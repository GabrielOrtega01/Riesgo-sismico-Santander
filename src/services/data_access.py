"""Acceso a los datos procesados y cálculo de indicadores descriptivos para la aplicación.

Todo lo que muestra la aplicación sale de aquí (o de los modelos entrenados cuando existan).
Los indicadores son **descriptivos del catálogo histórico**: no son categorías de riesgo ni
predicciones.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.data.loaders import load_clean_events

ROOT = Path(__file__).resolve().parents[2]
EVENTS_PATH = ROOT / "data" / "processed" / "eventos_santander_limpio.csv.gz"
MUNICIPALITIES_PATH = ROOT / "data" / "processed" / "municipios_santander.csv"
MC_PATH = ROOT / "data" / "processed" / "mc_por_anio.csv"
POPULATION_PATH = ROOT / "data" / "processed" / "poblacion_municipal_anual.csv"
SOURCES_DOC_PATH = ROOT / "docs" / "fuentes_datos.md"

DEFAULT_MIN_MAGNITUDE = 2.5     # completo en todos los años (ver docs/fuentes_datos.md)
SHALLOW_KM = 30.0

MODEL_ARTIFACTS = {
    "Clasificador (Bajo / Medio / Alto)": ROOT / "models" / "clasificador.joblib",
    "Política aprendida del agente (RL)": ROOT / "models" / "politica_q.npz",
}

_LOWER_WORDS = {"De", "Del", "La", "Las", "Los", "El"}


def pretty_name(name: str) -> str:
    """'SAN VICENTE DE CHUCURÍ' -> 'San Vicente de Chucurí' (el primer 'El' se conserva)."""
    words = str(name).title().split()
    return " ".join(
        w.lower() if (i > 0 and w in _LOWER_WORDS) else w for i, w in enumerate(words)
    )


# ------------------------------------------------------------------------ carga

def load_events(path: str | Path = EVENTS_PATH) -> pd.DataFrame:
    return load_clean_events(path)


def load_municipalities(path: str | Path = MUNICIPALITIES_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"cod_mpio": str})
    df["nombre"] = df["municipio_oficial"].map(pretty_name)
    return df.sort_values("nombre").reset_index(drop=True)


def load_mc_table(path: str | Path = MC_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def load_population(path: str | Path = POPULATION_PATH) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"cod_mpio": str})


def read_sources_doc(path: str | Path = SOURCES_DOC_PATH) -> str:
    return Path(path).read_text(encoding="utf-8")


# ------------------------------------------------------------------ indicadores

def catalog_summary(events: pd.DataFrame) -> dict:
    """Cifras globales del catálogo cargado."""
    return {
        "eventos": int(len(events)),
        "municipios": int(events["municipio_key"].nunique()),
        "inicio": events["utc_time"].min(),
        "fin": events["utc_time"].max(),
        "magnitud_max": float(events["magnitude"].max()),
        "profundidad_mediana": float(events["depth"].median()),
        "pct_profundos_100km": float((events["depth"] >= 100).mean() * 100),
    }


def yearly_indicators(
    events: pd.DataFrame,
    min_magnitude: float = DEFAULT_MIN_MAGNITUDE,
    shallow_km: float = SHALLOW_KM,
) -> pd.DataFrame:
    """Indicadores por municipio y año, con rejilla completa (años sin eventos = 0)."""
    df = events.assign(
        año=events["utc_time"].dt.year,
        sobre_umbral=events["magnitude"] >= min_magnitude,
        superficial=events["depth"] < shallow_km,
    )
    agg = df.groupby(["municipio_key", "año"]).agg(
        n_eventos=("id", "size"),
        n_sobre_umbral=("sobre_umbral", "sum"),
        magnitud_max=("magnitude", "max"),
        magnitud_media=("magnitude", "mean"),
        profundidad_mediana=("depth", "median"),
        pct_superficial=("superficial", "mean"),
    )
    agg["pct_superficial"] *= 100

    years = range(int(df["año"].min()), int(df["año"].max()) + 1)
    grid = pd.MultiIndex.from_product(
        [sorted(df["municipio_key"].dropna().unique()), years], names=["municipio_key", "año"]
    )
    out = agg.reindex(grid)
    out[["n_eventos", "n_sobre_umbral"]] = out[["n_eventos", "n_sobre_umbral"]].fillna(0).astype(int)
    return out.reset_index()


def zone_summary(
    events: pd.DataFrame,
    municipality: pd.Series,
    min_magnitude: float = DEFAULT_MIN_MAGNITUDE,
) -> dict:
    """Resumen descriptivo de un municipio (fila de `load_municipalities`)."""
    ev = events[events["municipio_key"] == municipality["municipio_key"]]
    base = {
        "cod_mpio": municipality["cod_mpio"],
        "nombre": municipality["nombre"],
        "eventos": int(len(ev)),
        "pct_del_catalogo": float(len(ev) / len(events) * 100) if len(events) else 0.0,
        "eventos_sobre_umbral": int((ev["magnitude"] >= min_magnitude).sum()),
        "pga_tr475": float(municipality["pga_tr475"]),
        "pga_tr2475": float(municipality["pga_tr2475"]),
        "intensidad_esperada": float(municipality["intensidad_esperada"]),
    }
    if ev.empty:
        return {**base, "magnitud_max": None, "fecha_magnitud_max": None,
                "profundidad_mediana": None, "pct_superficial": None}
    top = ev.loc[ev["magnitude"].idxmax()]
    return {
        **base,
        "magnitud_max": float(top["magnitude"]),
        "fecha_magnitud_max": top["utc_time"],
        "profundidad_mediana": float(ev["depth"].median()),
        "pct_superficial": float((ev["depth"] < SHALLOW_KM).mean() * 100),
    }


def depth_histogram(events: pd.DataFrame, municipio_key: str, bin_km: int = 10) -> pd.DataFrame:
    """Número de eventos por rango de profundidad (km) de un municipio."""
    depth = events.loc[events["municipio_key"] == municipio_key, "depth"].clip(lower=0)
    if depth.empty:
        return pd.DataFrame({"rango_km": [], "eventos": []})
    top = int(np.ceil(depth.max() / bin_km) * bin_km) or bin_km
    edges = np.arange(0, top + bin_km, bin_km)
    counts, _ = np.histogram(depth, bins=edges)
    labels = [f"{int(a):03d}-{int(b):03d}" for a, b in zip(edges[:-1], edges[1:])]
    return pd.DataFrame({"rango_km": labels, "eventos": counts})


def compare_zones(yearly: pd.DataFrame, keys: list[str], metric: str) -> pd.DataFrame:
    """Tabla año × municipio de una métrica, lista para graficar."""
    sub = yearly[yearly["municipio_key"].isin(keys)]
    return sub.pivot(index="año", columns="municipio_key", values=metric).sort_index()


def add_population(
    yearly: pd.DataFrame,
    municipalities: pd.DataFrame,
    population: pd.DataFrame,
    min_magnitude_label: str = "n_sobre_umbral",
) -> pd.DataFrame:
    """Añade población anual y eventos por 100 000 habitantes a la tabla municipio × año."""
    code = municipalities.set_index("municipio_key")["cod_mpio"]
    out = yearly.assign(cod_mpio=yearly["municipio_key"].map(code))
    pop = population[["cod_mpio", "año", "poblacion_total"]]
    out = out.merge(pop, on=["cod_mpio", "año"], how="left", validate="many_to_one")
    out["eventos_por_100mil"] = out[min_magnitude_label] / out["poblacion_total"] * 100_000
    return out.drop(columns="cod_mpio")


def zone_population(population: pd.DataFrame, cod_mpio: str, year: int | None = None) -> dict:
    """Población total y % en cabecera de un municipio (último año disponible por defecto)."""
    rows = population[population["cod_mpio"] == cod_mpio]
    if rows.empty:
        return {"año": None, "poblacion_total": None, "pct_cabecera": None}
    row = rows.loc[rows["año"].idxmax()] if year is None else rows[rows["año"] == year].iloc[0]
    return {
        "año": int(row["año"]),
        "poblacion_total": int(row["poblacion_total"]),
        "pct_cabecera": float(row["pct_poblacion_cabecera"]),
    }


def rank_zones(events: pd.DataFrame, municipalities: pd.DataFrame, min_magnitude: float) -> pd.DataFrame:
    """Posición de cada municipio por número de eventos M ≥ umbral (1 = más eventos)."""
    counts = (
        events.assign(_u=events["magnitude"] >= min_magnitude)
        .groupby("municipio_key")["_u"].sum().astype(int).rename("eventos_umbral")
    )
    out = municipalities[["municipio_key", "nombre"]].merge(
        counts, on="municipio_key", how="left"
    ).fillna({"eventos_umbral": 0})
    out["eventos_umbral"] = out["eventos_umbral"].astype(int)
    out["puesto"] = out["eventos_umbral"].rank(method="min", ascending=False).astype(int)
    return out.sort_values(["puesto", "nombre"]).reset_index(drop=True)


def _spaced(n: int | float) -> str:
    return f"{int(n):,}".replace(",", " ")


def describe_zone(info: dict, rank: int | None, total_zones: int, min_magnitude: float) -> str:
    """Resumen en lenguaje natural, construido solo con las cifras de la zona."""
    name = info["nombre"]
    if info["eventos"] == 0:
        return f"En el catálogo no hay sismos registrados para **{name}**."
    text = (
        f"En **{name}** el catálogo registra **{_spaced(info['eventos'])}** sismos entre 2006 y 2026; "
        f"**{_spaced(info['eventos_sobre_umbral'])}** tienen magnitud de {min_magnitude:g} o más."
    )
    if rank is not None and info["eventos_sobre_umbral"] > 0:
        text += f" Es el puesto **{rank} de {total_zones}** municipios por número de esos eventos."
    depth = info["profundidad_mediana"]
    if depth is not None:
        kind = "muy profundos" if depth >= 100 else "poco profundos" if depth < 30 else "de profundidad intermedia"
        text += f" La mayoría son {kind}: la profundidad típica es de unos {depth:.0f} km."
    if info["magnitud_max"] is not None:
        text += f" El más fuerte registrado fue de magnitud {info['magnitud_max']:.1f}."
    return text


MAP_METRICS = {
    "Sismos (magnitud mínima elegida)": "eventos_umbral",
    "Sismos totales del catálogo": "eventos",
    "Amenaza oficial (PGA, Tr = 475 años)": "pga_tr475",
    "Población proyectada": "poblacion",
}
LOG_SCALE_METRICS = {"eventos_umbral", "eventos", "poblacion"}
_MAP_LOW, _MAP_HIGH = "#cde2fb", "#0d366b"     # azul secuencial, claro → oscuro
_MAP_HIGHLIGHT = "#eb6834"


def _lerp(low: str, high: str, t: float) -> str:
    t = min(max(float(t), 0.0), 1.0)
    a = [int(low[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(high[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def map_table(
    events: pd.DataFrame,
    municipalities: pd.DataFrame,
    population: pd.DataFrame,
    metric: str,
    min_magnitude: float,
    highlight_key: str | None = None,
) -> pd.DataFrame:
    """Un punto por municipio (cabecera) con tamaño y color según el indicador elegido."""
    if metric not in MAP_METRICS.values():
        raise ValueError(f"Indicador desconocido: {metric}")
    counts = (
        events.assign(_u=events["magnitude"] >= min_magnitude)
        .groupby("municipio_key").agg(eventos=("id", "size"), eventos_umbral=("_u", "sum"))
    )
    base = municipalities.merge(counts, left_on="municipio_key", right_index=True, how="left")
    base[["eventos", "eventos_umbral"]] = base[["eventos", "eventos_umbral"]].fillna(0)
    last = population.loc[population["año"] == population["año"].max(), ["cod_mpio", "poblacion_total"]]
    base = base.merge(last.rename(columns={"poblacion_total": "poblacion"}), on="cod_mpio", how="left")

    value = base[metric].astype(float)
    # Los conteos y la población están muy concentrados (un municipio concentra > 50 % de los
    # sismos): se dibujan en escala logarítmica para que el resto siga siendo distinguible.
    scaled = np.log1p(value) if metric in LOG_SCALE_METRICS else value
    span = scaled.max() - scaled.min()
    norm = (scaled - scaled.min()) / span if span > 0 else pd.Series(0.5, index=value.index)
    out = pd.DataFrame({
        "nombre": base["nombre"],
        "municipio_key": base["municipio_key"],
        "lat": base["lat_cabecera"],
        "lon": base["lon_cabecera"],
        "valor": value,
        "size_m": 2500 + 9000 * np.sqrt(norm),
        "color": [_lerp(_MAP_LOW, _MAP_HIGH, t) for t in norm],
    })
    if highlight_key is not None:
        mask = out["municipio_key"] == highlight_key
        out.loc[mask, "color"] = _MAP_HIGHLIGHT
        out.loc[mask, "size_m"] = 14000
    return out


def model_status() -> list[dict]:
    """Estado de los artefactos entrenados que alimentan la clasificación y la priorización."""
    return [
        {"componente": name, "archivo": path.relative_to(ROOT).as_posix(), "disponible": path.is_file()}
        for name, path in MODEL_ARTIFACTS.items()
    ]
