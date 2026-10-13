"""Aplicación de demostración (Streamlit).

    streamlit run src/app.py

Muestra únicamente información calculada a partir de los datos procesados del proyecto. Las
secciones de clasificación y priorización permanecen "pendientes" hasta que existan los modelos
entrenados; no se muestran resultados escritos a mano.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:          # permite `import src...` al lanzar desde src/ (p. ej. en la nube)
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from src.services import data_access as da

st.set_page_config(page_title="Riesgo sísmico de Santander", page_icon="🌋", layout="wide")


# ---- datos (con caché) ---------------------------------------------------------

@st.cache_data(show_spinner="Cargando catálogo…")
def get_events() -> pd.DataFrame:
    return da.load_events()


@st.cache_data
def get_municipalities() -> pd.DataFrame:
    return da.load_municipalities()


@st.cache_data
def get_yearly(min_magnitude: float) -> pd.DataFrame:
    return da.yearly_indicators(get_events(), min_magnitude=min_magnitude)


# ---- cabecera y aviso de alcance --------------------------------------------------

st.title("Riesgo sísmico de Santander")
st.caption("Análisis exploratorio de la actividad sísmica histórica · Proyecto académico (UTS)")
st.warning(
    "**Alcance.** Esta herramienta describe y clasifica la actividad sísmica **histórica**. "
    "**No predice** la fecha, el lugar ni la magnitud de futuros terremotos y **no es** una "
    "evaluación oficial del riesgo de desastres. Las categorías son una clasificación "
    "exploratoria propia del proyecto.",
    icon="⚠️",
)

try:
    events = get_events()
    municipalities = get_municipalities()
except FileNotFoundError as exc:
    st.error(
        f"Faltan datos procesados: {exc}\n\n"
        "Genérelos con `python -m src.data.preprocessing` y `python -m src.data.integration`."
    )
    st.stop()

with st.sidebar:
    st.header("Parámetros")
    min_mag = st.select_slider(
        "Magnitud mínima para contar eventos",
        options=[2.0, 2.5, 3.0],
        value=da.DEFAULT_MIN_MAGNITUDE,
        help="2,5 es completo en todos los años del catálogo; con 2,0 los años 2006–2008 "
             "no son comparables (ver pestaña «Catálogo»).",
    )
    st.markdown("---")
    summary = da.catalog_summary(events)
    st.metric("Eventos en el catálogo", f"{summary['eventos']:,}".replace(",", " "))
    st.caption(
        f"{summary['inicio']:%Y-%m-%d} → {summary['fin']:%Y-%m-%d} (UTC) · "
        f"{summary['municipios']} municipios"
    )

yearly = get_yearly(min_mag)
names = municipalities.set_index("municipio_key")["nombre"]

tab_zone, tab_compare, tab_class, tab_prio, tab_catalog, tab_sources = st.tabs(
    ["Zona", "Comparar zonas", "Clasificación", "Priorización", "Catálogo", "Fuentes y limitaciones"]
)

# ---- Zona -----------------------------------------------------------------------------------
with tab_zone:
    st.subheader("Indicadores de una zona (municipio)")
    default_idx = int(municipalities.index[municipalities["municipio_key"] == "bucaramanga"][0])
    choice = st.selectbox("Municipio", municipalities["nombre"], index=default_idx, key="zona")
    muni = municipalities[municipalities["nombre"] == choice].iloc[0]
    info = da.zone_summary(events, muni, min_magnitude=min_mag)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Eventos registrados", f"{info['eventos']:,}".replace(",", " "),
              help=f"{info['pct_del_catalogo']:.1f} % del catálogo de Santander")
    c2.metric(f"Eventos M ≥ {min_mag}", f"{info['eventos_sobre_umbral']:,}".replace(",", " "))
    c3.metric("Magnitud máxima", "—" if info["magnitud_max"] is None else f"{info['magnitud_max']:.1f}")
    c4.metric("Profundidad mediana (km)",
              "—" if info["profundidad_mediana"] is None else f"{info['profundidad_mediana']:.0f}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Eventos superficiales (< 30 km)",
              "—" if info["pct_superficial"] is None else f"{info['pct_superficial']:.1f} %")
    c6.metric("PGA oficial, Tr = 475 años (g)", f"{info['pga_tr475']:.3f}",
              help="Amenaza Sísmica 2020 del SGC, muestreada en la cabecera municipal.")
    c7.metric("PGA oficial, Tr = 2 475 años (g)", f"{info['pga_tr2475']:.3f}")
    c8.metric("Intensidad sísmica esperada", f"{info['intensidad_esperada']:.0f}")
    st.caption(f"Código DANE: {info['cod_mpio']}")

    one = yearly[yearly["municipio_key"] == muni["municipio_key"]].assign(
        anio=lambda d: d["anio"].astype(str)
    ).set_index("anio")
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Eventos por año** (M ≥ {min_mag})")
        st.bar_chart(one["n_sobre_umbral"])
        last = events["utc_time"].max()
        st.caption(f"El año {last.year} es parcial: llega hasta {last:%Y-%m-%d}.")
    with right:
        st.markdown("**Distribución por profundidad** (eventos por rango de 10 km)")
        hist = da.depth_histogram(events, muni["municipio_key"])
        if hist.empty:
            st.info("Sin eventos registrados.")
        else:
            st.bar_chart(hist.set_index("rango_km")["eventos"])
    st.caption(
        "Indicadores **descriptivos** del catálogo histórico; no equivalen a una categoría de riesgo."
    )

# ---- Comparar zonas -------------------------------------------------------------------------
with tab_compare:
    st.subheader("Comparar zonas")
    metrics = {
        f"Eventos por año (M ≥ {min_mag})": "n_sobre_umbral",
        "Eventos por año (todos)": "n_eventos",
        "Magnitud máxima anual": "magnitud_max",
        "Profundidad mediana anual (km)": "profundidad_mediana",
        "% de eventos superficiales": "pct_superficial",
    }
    defaults = [n for n in ("Bucaramanga", "Los Santos", "Zapatoca") if n in set(municipalities["nombre"])]
    picked = st.multiselect("Municipios (hasta 6)", municipalities["nombre"], default=defaults,
                            max_selections=6, key="comparar")
    metric_label = st.selectbox("Indicador", list(metrics), key="indicador")
    if not picked:
        st.info("Seleccione al menos un municipio.")
    else:
        keys = municipalities.loc[municipalities["nombre"].isin(picked), "municipio_key"].tolist()
        table = da.compare_zones(yearly, keys, metrics[metric_label]).rename(columns=names)
        table.index = table.index.astype(str)          # evita separador de miles en los años
        st.line_chart(table)
        static = municipalities[municipalities["nombre"].isin(picked)][
            ["nombre", "cod_mpio", "n_eventos_catalogo", "pga_tr475", "intensidad_esperada"]
        ].rename(columns={
            "nombre": "Municipio", "cod_mpio": "Código", "n_eventos_catalogo": "Eventos (total)",
            "pga_tr475": "PGA Tr=475 (g)", "intensidad_esperada": "Intensidad esperada",
        })
        st.dataframe(static, hide_index=True)

# ---- Clasificación / Priorización (dependen de modelos entrenados) ---------------------------
def _pending(title: str, component_prefix: str, text: str) -> None:
    st.subheader(title)
    status = [s for s in da.model_status() if s["componente"].startswith(component_prefix)][0]
    if status["disponible"]:
        st.success(f"Artefacto encontrado: `{status['archivo']}`.")
        st.info("La integración de esta sección con el flujo completo está en desarrollo.")
    else:
        st.info(
            f"**Aún no disponible.** {text}\n\n"
            f"Artefacto requerido: `{status['archivo']}` (no existe todavía). "
            "Esta sección no muestra datos de ejemplo."
        )


with tab_class:
    _pending(
        "Clasificación de la zona",
        "Clasificador",
        "El clasificador supervisado (Básico / Medio / Avanzado) aún no está entrenado.",
    )
    st.markdown(
        "**Metodología prevista:** la categoría de un municipio en el año *t* se define con la "
        "actividad sísmica del año *t*+1 y se estima con información hasta el año *t*; los "
        "umbrales se ajustan solo con años de entrenamiento y se compara siempre contra una "
        "línea base de persistencia."
    )

with tab_prio:
    _pending(
        "Priorización exploratoria",
        "Política",
        "El agente de aprendizaje por refuerzo aún no está entrenado.",
    )
    st.markdown(
        "**Qué mostrará:** el orden de zonas que propone la política aprendida y su comparación "
        "con una estrategia de referencia, junto con la explicación de los indicadores usados."
    )

# ---- Catálogo --------------------------------------------------------------------------------
with tab_catalog:
    st.subheader("Calidad y homogeneidad del catálogo")
    mc = da.load_mc_table()
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Eventos por año (todo Santander)**")
        per_year = events.groupby(events["utc_time"].dt.year).size().rename("eventos")
        st.bar_chart(per_year)
    with col_b:
        st.markdown("**Magnitud de completitud estimada por año (Mc)**")
        st.line_chart(mc.assign(anio=mc["anio"].astype(str)).set_index("anio")["mc_maxc"])
    st.info(
        "**El catálogo no es homogéneo.** Hacia 2018 cambian el tipo de magnitud dominante, el "
        "número de estaciones por evento (`nst`) y el valor *b*. Antes de 2009 la completitud es "
        "menor. Por eso se propone M ≥ 2,5 para comparar años."
    )
    st.dataframe(mc.round(2), hide_index=True)

# ---- Fuentes y limitaciones -----------------------------------------------------------------
with tab_sources:
    st.subheader("Fuentes de datos y limitaciones")
    st.markdown(da.read_sources_doc())
