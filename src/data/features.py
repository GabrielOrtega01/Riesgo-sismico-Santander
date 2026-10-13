"""Panel municipio × año con las variables del proyecto y su diccionario.

Cada fila describe un municipio al **final** de un año `t` usando solo información disponible
hasta `t` (sin fuga hacia el futuro). Las variables históricas usan los años estrictamente
anteriores. El año 2026 queda fuera del panel: es parcial y sus conteos no son comparables.

Aquí NO se construye la etiqueta (categoría Básico/Medio/Avanzado): eso es un paso posterior que
mira al año t+1. Aquí tampoco se imputan faltantes: la imputación se ajusta solo con datos de
entrenamiento, en el flujo de modelado.

La lista `FEATURES` es la fuente única del diccionario de variables: el documento
`docs/diccionario_variables.md` se genera desde ella.

    python -m src.data.features
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.integration import haversine_km
from src.data.loaders import load_clean_events

FIRST_YEAR = 2006
LAST_FULL_YEAR = 2025
MIN_MAGNITUDE = 2.5
STRONG_MAGNITUDE = 3.0
SHALLOW_KM = 30.0
NEIGHBOR_KM = 50.0
NEST_REFERENCE_KEY = "los santos"
MIN_HISTORY_YEARS = 3            # filas con menos años de historia no se usan para modelar

ID_COLUMNS = ["cod_mpio", "municipio_key", "municipio", "anio", "anios_historia"]
FLAG_COLUMNS = ["tiene_eventos_anio", "tiene_eventos_m25_anio"]


@dataclass(frozen=True)
class Feature:
    name: str
    group: str
    description: str
    source: str
    origin: str            # "original" | "derivada"
    kind: str
    formula: str
    unit: str
    missing: str
    why: str
    limitation: str
    agent_state_candidate: bool = False
    regime_proxy: bool = False        # |ρ| > 0,5 con el año: puede codificar el cambio de red de 2018


CAT = "Catálogo SGC"
HAZ = "Amenaza SGC 2020"
POP = "Población DANE"
DIV = "DIVIPOLA DANE"

FEATURES: list[Feature] = [
    # ---- frecuencia y persistencia -------------------------------------------------------
    Feature("n_m25_anio", "Frecuencia", "Sismos de magnitud ≥ 2,5 en el municipio durante el año t.",
            CAT, "derivada", "conteo", "count(magnitude ≥ 2,5, año = t)", "sismos/año",
            "Sin faltantes: 0 si no hubo eventos.",
            "Nivel de actividad del año. El umbral 2,5 es completo en todos los años del catálogo (Mc).",
            "Conteos bajos por municipio: muchos años con 0.", True),
    Feature("n_m25_hist_prom", "Frecuencia", "Promedio anual de sismos M ≥ 2,5 en los años anteriores a t.",
            CAT, "derivada", "numérica continua", "mean(n_m25_anio de los años < t)", "sismos/año",
            "NaN en el primer año (sin historia).",
            "Nivel base de largo plazo: separa un año excepcional de un municipio habitualmente activo.",
            "Mezcla el régimen de red anterior y posterior a 2018.", True),
    Feature("n_m25_cambio_1a", "Frecuencia", "Cambio del conteo M ≥ 2,5 respecto al año anterior.",
            CAT, "derivada", "numérica discreta", "n_m25_anio(t) − n_m25_anio(t−1)", "sismos/año",
            "NaN en el primer año.",
            "Tendencia reciente de la actividad, distinta de su nivel.",
            "Ruidosa cuando los conteos son pequeños."),
    Feature("n_m25_vecinos_anio", "Frecuencia espacial",
            "Sismos M ≥ 2,5 del año t en otros municipios cuya cabecera está a ≤ 50 km.",
            CAT + " + " + DIV, "derivada", "conteo", "Σ n_m25_anio(vecino), distancia entre cabeceras ≤ 50 km",
            "sismos/año", "Sin faltantes: 0 si no hay vecinos activos.",
            "Contexto regional: la actividad cercana no queda capturada por el propio municipio.",
            "Usa la cabecera como punto del municipio; la etiqueta `place` es una referencia, "
            "no un polígono."),
    # ---- magnitud --------------------------------------------------------------------
    Feature("magnitud_max_anio", "Magnitud", "Mayor magnitud registrada en el municipio durante el año t.",
            CAT, "derivada", "numérica continua", "max(magnitude, año = t)", "magnitud",
            "NaN si no hubo eventos ese año.",
            "Severidad del evento más fuerte; el máximo es robusto a la incompletitud del catálogo.",
            "Mezcla tipos de magnitud (ML, MLr, MW) sin homogenizar."),
    Feature("magnitud_media_m25_anio", "Magnitud", "Magnitud media de los sismos M ≥ 2,5 del año t.",
            CAT, "derivada", "numérica continua", "mean(magnitude | magnitude ≥ 2,5, año = t)", "magnitud",
            "NaN si no hubo eventos M ≥ 2,5.",
            "Forma típica de la distribución, distinta de su extremo.",
            "Pocos eventos → media inestable."),
    Feature("magnitud_max_hist", "Magnitud", "Mayor magnitud registrada en el municipio antes del año t.",
            CAT, "derivada", "numérica continua", "max(magnitude, años < t)", "magnitud",
            "NaN en el primer año o si no hubo eventos.",
            "Techo conocido de la actividad del municipio.",
            "Depende del periodo observado (20 años)."),
    Feature("pct_m30_sobre_m25", "Magnitud", "Porcentaje de los sismos M ≥ 2,5 del año que tienen M ≥ 3,0.",
            CAT, "derivada", "porcentaje", "100 · n(M ≥ 3,0) / n(M ≥ 2,5)", "%",
            "NaN si no hubo eventos M ≥ 2,5.",
            "Proporción de eventos relativamente fuertes (cola de la distribución).",
            "Inestable con pocos eventos."),
    # ---- profundidad -----------------------------------------------------------------
    Feature("profundidad_mediana_anio", "Profundidad", "Profundidad mediana de los sismos del año t.",
            CAT, "derivada", "numérica continua", "median(depth, año = t)", "km",
            "NaN si no hubo eventos.",
            "Separa la sismicidad profunda (nido de Bucaramanga) de la superficial.",
            "La profundidad tiene error (puede ser grande en eventos con pocas estaciones)."),
    Feature("pct_superficial_anio", "Profundidad", "Porcentaje de sismos del año con profundidad < 30 km.",
            CAT, "derivada", "porcentaje", "100 · n(depth < 30) / n(total)", "%",
            "NaN si no hubo eventos.",
            "Los eventos superficiales son los que más importan para las construcciones.",
            "El umbral de 30 km es una convención del proyecto.", True),
    Feature("profundidad_iqr_anio", "Profundidad", "Rango intercuartílico de la profundidad de los sismos del año.",
            CAT, "derivada", "numérica continua", "Q3(depth) − Q1(depth), año = t", "km",
            "NaN si no hubo eventos.",
            "Dispersión: detecta mezcla de poblaciones profundas y superficiales.",
            "Requiere varios eventos para ser estable."),
    # ---- calidad de la localización ------------------------------------------------------
    Feature("nst_mediano_anio", "Calidad de localización", "Mediana del número de estaciones/fases por evento.",
            CAT, "original", "conteo", "median(nst, año = t)", "estaciones",
            "NaN si no hubo eventos.",
            "Indicador de cobertura de la red en la zona; condiciona qué tan completo es el catálogo allí.",
            "Cambia de régimen hacia 2018 (ρ = 0,72 con el año): puede actuar como indicador de año. "
            "Se evalúa con y sin ella.", regime_proxy=True),
    Feature("gap_mediano_anio", "Calidad de localización", "Mediana del hueco azimutal (gap) de las localizaciones.",
            CAT, "original", "numérica continua", "median(gap, año = t)", "grados",
            "NaN si no hubo eventos.",
            "Un hueco grande indica estaciones mal distribuidas alrededor del epicentro.",
            "Un solo valor de gap por evento; no se ha validado frente a la geometría real de la red."),
    Feature("error_horizontal_mediano_anio", "Calidad de localización",
            "Mediana del error horizontal de la localización.", CAT, "derivada", "numérica continua",
            "median(√(latitude_error² + longitude_error²), año = t)", "km (supuesto)",
            "NaN si no hubo eventos o faltan ambos errores.",
            "Incertidumbre de la ubicación: afecta a qué municipio se asigna el evento.",
            "La unidad (km) se asume y no está verificada en la documentación del catálogo. "
            "Sigue al año (ρ = 0,73): se evalúa con y sin ella.", regime_proxy=True),
    Feature("rms_mediano_anio", "Calidad de localización", "Mediana del residuo (RMS) del ajuste de localización.",
            CAT, "original", "numérica continua", "median(rms, año = t)", "s",
            "NaN si no hubo eventos.",
            "Calidad del ajuste del modelo de velocidades a las llegadas observadas.",
            "Correlaciona con el número de estaciones."),
    Feature("error_profundidad_mediano_anio", "Calidad de localización",
            "Mediana del error de profundidad reportado.", CAT, "original", "numérica continua",
            "median(depth_error, año = t)", "km (supuesto)",
            "NaN si no hubo eventos o falta el error (263 casos en el catálogo).",
            "Confiabilidad de la profundidad usada en las variables de profundidad.",
            "Unidad asumida; valores extremos (hasta 1 000). Sigue al año (ρ = −0,65): se evalúa "
            "con y sin ella.", regime_proxy=True),
    # ---- amenaza oficial (estática) ---------------------------------------------------
    Feature("pga_tr475", "Amenaza oficial", "Aceleración máxima del suelo esperada (PGA) para Tr = 475 años.",
            HAZ, "original", "numérica continua", "valor del ráster en la cabecera municipal", "g",
            "Sin faltantes (87 de 87 municipios).",
            "Estimación oficial de la amenaza por municipio.",
            "Mapa estático de 2020, no independiente de los eventos usados; un punto por municipio; "
            "rango estrecho (0,20–0,28 g).", True),
    Feature("intensidad_esperada", "Amenaza oficial", "Intensidad sísmica esperada según el SGC.",
            HAZ, "original", "ordinal (6, 7)", "valor del ráster en la cabecera municipal", "grado",
            "Sin faltantes.",
            "Medida oficial de efectos esperados, en una escala distinta de la aceleración.",
            "Solo toma dos valores; correlaciona con el PGA."),
    Feature("sa10_sobre_pga", "Amenaza oficial",
            "Cociente entre la aceleración espectral a 1,0 s y el PGA (Tr = 475 años).",
            HAZ, "derivada", "numérica continua", "sa10_tr475 / pga_tr475", "adimensional",
            "Sin faltantes.",
            "Forma del espectro: aporta información sobre el contenido de periodos largos.",
            "Muy poca variación entre municipios."),
    # ---- geografía --------------------------------------------------------------------
    Feature("distancia_los_santos_km", "Geografía",
            "Distancia desde la cabecera del municipio a la de Los Santos.",
            DIV, "derivada", "numérica continua", "haversine(cabecera, cabecera de Los Santos)", "km",
            "Sin faltantes.",
            "Posición relativa a la zona donde se concentra la sismicidad profunda de la región.",
            "Usa un municipio como referencia del nido sísmico; es una aproximación geográfica."),
    # ---- exposición --------------------------------------------------------------------
    Feature("poblacion_log10", "Exposición", "Logaritmo decimal de la población total proyectada del año t.",
            POP, "derivada", "numérica continua", "log10(poblacion_total)", "log10(hab.)",
            "Sin faltantes (2005–2026).",
            "Exposición: cuánta gente habita el municipio. El logaritmo estabiliza la asimetría.",
            "Son proyecciones; mide exposición, no vulnerabilidad."),
    Feature("pct_poblacion_cabecera", "Exposición", "Porcentaje de la población que vive en la cabecera.",
            POP, "original", "porcentaje", "100 · poblacion_cabecera / poblacion_total", "%",
            "Sin faltantes.",
            "Grado de concentración urbana de la exposición.",
            "Cambia lentamente; casi constante por municipio."),
    Feature("crecimiento_poblacion_pct", "Exposición", "Variación porcentual de la población respecto al año anterior.",
            POP, "derivada", "numérica continua", "100 · (pob(t) / pob(t−1) − 1)", "%",
            "Sin faltantes (la serie incluye 2005).",
            "Dinámica de la exposición.",
            "Efecto del empalme de series 2017/2018 (verificado como pequeño)."),
]

FEATURE_NAMES = [f.name for f in FEATURES]

# Variables evaluadas y descartadas, con la evidencia que motivó el descarte.
CORRELATION_DROP_THRESHOLD = 0.90
DISCARDED = [
    ("meses_activos_m25", "Redundante con `n_m25_anio` (ρ de Spearman = 0,998): en la mayoría de los "
     "municipios-año con eventos, cada sismo cae en un mes distinto.", "medida en el panel"),
    ("frac_anios_activos_hist", "Redundante con `n_m25_hist_prom` (ρ = 0,953): ambas miden qué tan "
     "habitualmente es activo el municipio.", "medida en el panel"),
    ("n_total_anio (todos los sismos del año)", "Su conteo depende de la red de detección (pasa de "
     "≈2 400 a ≈16 000 eventos/año), no solo de la sismicidad; se usa M ≥ 2,5 en su lugar.",
     "documentada en fuentes_datos.md"),
    ("energia_anual (suma de energía liberada)", "Casi determinada por la magnitud máxima del año; "
     "no aporta una dimensión nueva con los conteos tan bajos por municipio.", "criterio a priori, no medida"),
    ("valor_b_anual", "Inestable con los pocos eventos por municipio y año.", "criterio a priori, no medida"),
    ("latitud / longitud de la cabecera", "Quedan resumidas por `distancia_los_santos_km`; las "
     "coordenadas crudas facilitarían identificar municipios y sobreajustar.", "criterio a priori"),
]


# ------------------------------------------------------------------------ construcción

def _yearly_aggregates(ev: pd.DataFrame, min_magnitude: float) -> pd.DataFrame:
    ev = ev.assign(
        anio=ev["utc_time"].dt.year,
        err_h=np.hypot(ev["latitude_error"], ev["longitude_error"]),
        superficial=ev["depth"] < SHALLOW_KM,
    )
    g = ev.groupby(["municipio_key", "anio"])
    allagg = g.agg(
        n_total=("id", "size"),
        magnitud_max_anio=("magnitude", "max"),
        profundidad_mediana_anio=("depth", "median"),
        pct_superficial_anio=("superficial", "mean"),
        nst_mediano_anio=("nst", "median"),
        gap_mediano_anio=("gap", "median"),
        rms_mediano_anio=("rms", "median"),
        error_horizontal_mediano_anio=("err_h", "median"),
        error_profundidad_mediano_anio=("depth_error", "median"),
    )
    allagg["pct_superficial_anio"] *= 100
    q = g["depth"].quantile([0.25, 0.75]).unstack()
    allagg["profundidad_iqr_anio"] = q[0.75] - q[0.25]

    m25 = ev[ev["magnitude"] >= min_magnitude]
    g25 = m25.groupby(["municipio_key", "anio"])
    a25 = g25.agg(
        n_m25_anio=("id", "size"),
        magnitud_media_m25_anio=("magnitude", "mean"),
    )
    strong = ev[ev["magnitude"] >= STRONG_MAGNITUDE].groupby(["municipio_key", "anio"]).size().rename("n_m30")
    return allagg.join(a25, how="outer").join(strong, how="outer")


def build_feature_panel(
    events: pd.DataFrame,
    municipalities: pd.DataFrame,
    population: pd.DataFrame,
    first_year: int = FIRST_YEAR,
    last_year: int = LAST_FULL_YEAR,
    min_magnitude: float = MIN_MAGNITUDE,
) -> pd.DataFrame:
    """Panel (municipio × año) con todas las variables de `FEATURES`.

    Cada fila usa solo eventos con año ≤ t; los eventos posteriores a `last_year` se ignoran.
    """
    ev = events[events["utc_time"].dt.year <= last_year]
    years = list(range(first_year, last_year + 1))
    muni = municipalities.sort_values("municipio_key").reset_index(drop=True)
    keys = muni["municipio_key"].tolist()

    agg = _yearly_aggregates(ev, min_magnitude)
    grid = pd.MultiIndex.from_product([keys, years], names=["municipio_key", "anio"])
    panel = agg.reindex(grid).reset_index()
    for col in ("n_total", "n_m25_anio", "n_m30"):
        panel[col] = panel[col].fillna(0).astype(int)

    panel["tiene_eventos_anio"] = panel["n_total"] > 0
    panel["tiene_eventos_m25_anio"] = panel["n_m25_anio"] > 0
    panel["pct_m30_sobre_m25"] = np.where(
        panel["n_m25_anio"] > 0, 100 * panel["n_m30"] / panel["n_m25_anio"].replace(0, np.nan), np.nan
    )

    # ---- históricas: solo años estrictamente anteriores ----
    panel = panel.sort_values(["municipio_key", "anio"]).reset_index(drop=True)
    grp = panel.groupby("municipio_key", sort=False)
    panel["n_m25_hist_prom"] = grp["n_m25_anio"].transform(lambda s: s.expanding().mean().shift(1))
    panel["magnitud_max_hist"] = grp["magnitud_max_anio"].transform(lambda s: s.expanding().max().shift(1))
    panel["n_m25_cambio_1a"] = grp["n_m25_anio"].diff()
    panel["anios_historia"] = panel["anio"] - first_year

    # ---- vecinos a ≤ 50 km (misma año) ----
    lat, lon = muni["lat_cabecera"].to_numpy(), muni["lon_cabecera"].to_numpy()
    dist = haversine_km(lat[:, None], lon[:, None], lat[None, :], lon[None, :])
    weights = ((dist <= NEIGHBOR_KM) & ~np.eye(len(muni), dtype=bool)).astype(float)
    wide = panel.pivot(index="anio", columns="municipio_key", values="n_m25_anio")[keys]
    neighbors = pd.DataFrame(wide.to_numpy() @ weights.T, index=wide.index, columns=keys)
    panel["n_m25_vecinos_anio"] = [
        neighbors.at[a, k] for a, k in zip(panel["anio"], panel["municipio_key"])
    ]
    panel["n_m25_vecinos_anio"] = panel["n_m25_vecinos_anio"].astype(int)

    # ---- estáticas por municipio ----
    static = muni.set_index("municipio_key")
    ref = muni[muni["municipio_key"] == NEST_REFERENCE_KEY]
    if ref.empty:
        raise ValueError(f"No está el municipio de referencia: {NEST_REFERENCE_KEY}")
    ref_lat, ref_lon = float(ref["lat_cabecera"].iloc[0]), float(ref["lon_cabecera"].iloc[0])
    static = static.assign(
        sa10_sobre_pga=static["sa10_tr475"] / static["pga_tr475"],
        distancia_los_santos_km=haversine_km(
            static["lat_cabecera"], static["lon_cabecera"], ref_lat, ref_lon
        ),
    )
    for col in ("pga_tr475", "intensidad_esperada", "sa10_sobre_pga", "distancia_los_santos_km"):
        panel[col] = panel["municipio_key"].map(static[col])
    panel["cod_mpio"] = panel["municipio_key"].map(static["cod_mpio"])
    panel["municipio"] = panel["municipio_key"].map(static["municipio_oficial"])

    # ---- población (con 2005 para el crecimiento) ----
    pop = population.sort_values(["cod_mpio", "anio"]).copy()
    pop["poblacion_log10"] = np.log10(pop["poblacion_total"])
    pop["crecimiento_poblacion_pct"] = pop.groupby("cod_mpio")["poblacion_total"].pct_change() * 100
    panel = panel.merge(
        pop[["cod_mpio", "anio", "poblacion_log10", "pct_poblacion_cabecera", "crecimiento_poblacion_pct"]],
        on=["cod_mpio", "anio"], how="left", validate="one_to_one",
    )

    return panel[ID_COLUMNS + FEATURE_NAMES + FLAG_COLUMNS].sort_values(
        ["cod_mpio", "anio"]
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------- reporte

def panel_report(panel: pd.DataFrame, correlation_threshold: float = 0.85) -> dict:
    """Faltantes, redundancia (Spearman) y dependencia del año de cada variable."""
    usable = panel[panel["anios_historia"] >= MIN_HISTORY_YEARS]
    X = usable[FEATURE_NAMES]
    corr = X.corr(method="spearman")

    pairs = []
    for i, a in enumerate(FEATURE_NAMES):
        for b in FEATURE_NAMES[i + 1:]:
            r = corr.loc[a, b]
            if pd.notna(r) and abs(r) >= correlation_threshold:
                pairs.append({"a": a, "b": b, "spearman": round(float(r), 3)})
    pairs.sort(key=lambda p: -abs(p["spearman"]))

    year_corr = {
        f: round(float(usable[f].corr(usable["anio"], method="spearman")), 3) for f in FEATURE_NAMES
    }
    return {
        "filas_panel": int(len(panel)),
        "municipios": int(panel["cod_mpio"].nunique()),
        "anios": [int(panel["anio"].min()), int(panel["anio"].max())],
        "filas_utilizables_para_modelar": int(len(usable)),
        "anios_utilizables": [int(usable["anio"].min()), int(usable["anio"].max())],
        "n_variables": len(FEATURE_NAMES),
        "porcentaje_faltante_por_variable": {
            f: round(float(X[f].isna().mean() * 100), 1) for f in FEATURE_NAMES
        },
        "pares_con_correlacion_alta": pairs,
        "umbral_correlacion": correlation_threshold,
        "correlacion_con_el_anio": year_corr,
        "variables_dependientes_del_anio_abs_gt_0_5": sorted(
            f for f, r in year_corr.items() if pd.notna(r) and abs(r) > 0.5
        ),
    }


def render_dictionary(report: dict | None = None) -> str:
    """Documento Markdown del diccionario, generado desde `FEATURES`."""
    miss = (report or {}).get("porcentaje_faltante_por_variable", {})
    rho = (report or {}).get("correlacion_con_el_anio", {})
    groups: dict[str, list[Feature]] = {}
    for f in FEATURES:
        groups.setdefault(f.group, []).append(f)

    lines = [
        "# Diccionario de variables",
        "",
        "> Generado automáticamente desde `src/data/features.py` (`python -m src.data.features`). "
        "No editar a mano: modificar la lista `FEATURES` y regenerar.",
        "",
        "## Resumen",
        "",
        f"- **{len(FEATURES)} variables de entrada** candidatas para el clasificador, en "
        f"{len(groups)} grupos.",
        f"- Originales del catálogo o de las fuentes: {sum(f.origin == 'original' for f in FEATURES)}; "
        f"derivadas: {sum(f.origin == 'derivada' for f in FEATURES)}.",
        f"- Candidatas a **estado del agente** de refuerzo: "
        f"{sum(f.agent_state_candidate for f in FEATURES)} (propuesta; se confirma al diseñar el "
        "entorno).",
        "- **Unidad de análisis:** municipio × año. Años del panel: "
        f"{FIRST_YEAR}–{LAST_FULL_YEAR}; 2026 queda fuera por ser parcial.",
        f"- **Umbral de magnitud** de los conteos: M ≥ {MIN_MAGNITUDE:g} (completo en todos los años).",
        "- **Sin fuga temporal:** cada variable de la fila del año *t* usa solo eventos con año ≤ *t*; "
        "las históricas usan años < *t*. La prueba `test_no_future_leakage` lo verifica.",
        "- **Etiqueta:** no forma parte de este panel; se construye aparte con el año *t*+1.",
        "- **Faltantes:** no se imputan aquí. La imputación se ajusta solo con datos de entrenamiento.",
        "",
    ]
    if report:
        lines += [
            f"Filas del panel: {report['filas_panel']} ({report['municipios']} municipios × "
            f"{report['anios'][1] - report['anios'][0] + 1} años). Utilizables para modelar (≥ "
            f"{MIN_HISTORY_YEARS} años de historia): {report['filas_utilizables_para_modelar']} "
            f"({report['anios_utilizables'][0]}–{report['anios_utilizables'][1]}).",
            "",
        ]

    for group, feats in groups.items():
        lines += [f"## {group}", ""]
        lines += ["| Variable | Descripción | Fuente | Tipo | Fórmula | Unidad | % faltante | ρ con el año |",
                  "|---|---|---|---|---|---|---|---|"]
        for f in feats:
            m = f"{miss[f.name]:.1f}" if f.name in miss else "—"
            r = f"{rho[f.name]:+.2f}" if f.name in rho and pd.notna(rho[f.name]) else "—"
            marks = (" ★" if f.agent_state_candidate else "") + (" ⚠" if f.regime_proxy else "")
            lines.append(
                f"| `{f.name}`{marks} | {f.description} | {f.source} | {f.origin}, {f.kind} | "
                f"{f.formula} | {f.unit} | {m} | {r} |"
            )
        lines += ["", "| Variable | Tratamiento de faltantes | Justificación | Limitaciones |", "|---|---|---|---|"]
        for f in feats:
            lines.append(f"| `{f.name}` | {f.missing} | {f.why} | {f.limitation} |")
        lines.append("")

    lines += ["★ = candidata a estado del agente de refuerzo. ⚠ = indicador de régimen "
              "(sigue al año; se evalúa con y sin ella).", ""]

    n_proxy = sum(f.regime_proxy for f in FEATURES)
    lines += [
        "## Cuántas variables independientes hay",
        "",
        f"- Variables de entrada del panel: **{len(FEATURES)}**.",
        f"- Sin las {n_proxy} que pueden codificar el año (⚠): **{len(FEATURES) - n_proxy}**. "
        "El mínimo exigido (20) se cumple con y sin ellas.",
        "- Regla aplicada: se descartó una variable de cada par con |ρ de Spearman| ≥ "
        f"{CORRELATION_DROP_THRESHOLD:.2f}. Los pares entre 0,85 y 0,90 se conservan y se vigilan.",
        "",
    ]
    if report and report.get("pares_con_correlacion_alta"):
        lines += ["Pares con |ρ| ≥ 0,85 entre las variables **finales** (se conservan):", "",
                  "| Variable A | Variable B | ρ de Spearman |", "|---|---|---|"]
        for p in report["pares_con_correlacion_alta"]:
            lines.append(f"| `{p['a']}` | `{p['b']}` | {p['spearman']:+.3f} |")
        lines.append("")
    elif report:
        lines += ["Ningún par de las variables finales supera |ρ| ≥ 0,85.", ""]

    lines += ["## Variables evaluadas y descartadas", "",
              "| Variable | Motivo | Evidencia |", "|---|---|---|"]
    for name, reason, evidence in DISCARDED:
        lines.append(f"| `{name}` | {reason} | {evidence} |")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- ejecución

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Construye el panel de variables municipio × año.")
    parser.add_argument("--events", default="data/processed/eventos_santander_limpio.csv.gz")
    parser.add_argument("--municipalities", default="data/processed/municipios_santander.csv")
    parser.add_argument("--population", default="data/processed/poblacion_municipal_anual.csv")
    parser.add_argument("--out", default="data/processed")
    parser.add_argument("--doc", default="docs/diccionario_variables.md")
    args = parser.parse_args(argv)

    events = load_clean_events(args.events)
    municipalities = pd.read_csv(args.municipalities, dtype={"cod_mpio": str})
    population = pd.read_csv(args.population, dtype={"cod_mpio": str})

    panel = build_feature_panel(events, municipalities, population)
    report = panel_report(panel)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    panel.to_csv(out / "panel_municipio_anio.csv", index=False, float_format="%.6g")
    with open(out / "panel_variables_reporte.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    Path(args.doc).write_text(render_dictionary(report), encoding="utf-8")

    print(f"Panel: {len(panel)} filas × {len(FEATURE_NAMES)} variables → {out / 'panel_municipio_anio.csv'}")
    print(f"Diccionario → {args.doc}")
    print(json.dumps({k: report[k] for k in (
        "filas_utilizables_para_modelar", "pares_con_correlacion_alta",
        "variables_dependientes_del_anio_abs_gt_0_5")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
