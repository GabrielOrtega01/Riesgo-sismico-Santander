"""Aplicación de demostración (Streamlit).

    streamlit run src/app.py

Muestra únicamente información calculada a partir de los datos procesados del proyecto. Las
secciones de clasificación y priorización permanecen "en desarrollo" hasta que existan los
modelos entrenados; no se muestran resultados escritos a mano.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:          # permite `import src...` al lanzar desde src/ (p. ej. en la nube)
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from src.services import data_access as da
from src.ui import content as C
from src.ui import theme as T

APP_NAME = "Seismox"
APP_TAGLINE = "Riesgo sísmico de Santander"

st.set_page_config(
    page_title=f"{APP_NAME} · {APP_TAGLINE}", page_icon="🌋", layout="wide",
    initial_sidebar_state="expanded",
)
T.inject_css()


def fmt(n) -> str:
    return f"{int(n):,}".replace(",", " ")


# ---- datos (con caché) ---------------------------------------------------------------------

@st.cache_data(show_spinner="Cargando catálogo…")
def get_events() -> pd.DataFrame:
    return da.load_events()


@st.cache_data
def get_municipalities() -> pd.DataFrame:
    return da.load_municipalities()


@st.cache_data
def get_population() -> pd.DataFrame:
    return da.load_population()


@st.cache_data
def get_yearly(min_magnitude: float) -> pd.DataFrame:
    return da.add_population(
        da.yearly_indicators(get_events(), min_magnitude=min_magnitude),
        get_municipalities(), get_population(),
    )


try:
    events = get_events()
    municipalities = get_municipalities()
    population = get_population()
except FileNotFoundError as exc:
    st.error(
        f"Faltan datos procesados: {exc}\n\n"
        "Genérelos con `python -m src.data.preprocessing`, `python -m src.data.integration` "
        "y `python -m src.data.population`."
    )
    st.stop()

summary = da.catalog_summary(events)
status = {s["componente"].split(" ")[0]: s["disponible"] for s in da.model_status()}


def go(page: str) -> None:
    st.session_state["nav"] = page


# ---- barra lateral (menú) -------------------------------------------------------------------
st.session_state.setdefault("nav", C.PAGE_HOME)
with st.sidebar:
    st.markdown(
        f'<div class="brand">🌋 {APP_NAME}</div>'
        f'<div class="brand-sub">{APP_TAGLINE} · actividad sísmica histórica</div>',
        unsafe_allow_html=True,
    )
    st.radio("Menú", C.PAGES, key="nav", label_visibility="collapsed")
    st.divider()
    with st.expander("⚙️ Opciones de visualización"):
        min_mag = st.select_slider(
            "Magnitud mínima para contar sismos",
            options=[2.0, 2.5, 3.0], value=da.DEFAULT_MIN_MAGNITUDE, key="min_mag",
            help="2,5 es la más segura para comparar años: el catálogo es completo desde 2006. "
                 "Con 2,0 los años 2006–2008 no son comparables.",
        )
    st.caption("Proyecto académico · UTS\n\nDatos: SGC y DANE\n\nNo es una evaluación oficial del riesgo.")

yearly = get_yearly(min_mag)
names = municipalities.set_index("municipio_key")["nombre"]
ranking = da.rank_zones(events, municipalities, min_mag)


def footer() -> None:
    st.markdown(
        '<p class="footnote">Análisis exploratorio de datos históricos. No predice terremotos y '
        "no es una evaluación oficial del riesgo de desastres.</p>",
        unsafe_allow_html=True,
    )


# ============================================================================ INICIO
def page_home() -> None:
    T.hero(
        f"{APP_NAME} · {APP_TAGLINE}",
        "Explora más de 20 años de actividad sísmica en los 87 municipios de Santander, "
        "con datos oficiales del Servicio Geológico Colombiano y del DANE.",
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Sismos registrados", fmt(summary["eventos"]))
    k2.metric("Municipios", summary["municipios"])
    k3.metric("Periodo", f"{summary['inicio']:%Y}–{summary['fin']:%Y}")
    k4.metric("Mayor magnitud", f"{summary['magnitud_max']:.1f}")

    st.markdown("### ¿De qué trata?")
    st.markdown(
        '<p class="lede">Santander registra miles de sismos cada año; casi todos son muy pequeños y '
        "ocurren a gran profundidad, por lo que las personas rara vez los sienten. Esta herramienta "
        "reúne datos oficiales para que puedas ver, municipio por municipio, <b>cómo ha sido su "
        "actividad sísmica</b>, <b>cuánta gente vive allí</b> y <b>qué amenaza estima el SGC</b>, y "
        "para organizar qué zonas conviene revisar primero.</p>",
        unsafe_allow_html=True,
    )

    st.markdown("### ¿Cómo funciona?")
    cls_ok, rl_ok = status.get("Clasificador", False), status.get("Política", False)
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        T.card("Datos oficiales", "<p>Reunimos el catálogo de sismos del SGC, su mapa de amenaza y "
               "la población del DANE, y los unimos por municipio.</p><p style='margin-top:.6rem'>"
               + T.badge("Disponible", "ok") + "</p>", number=1),
        unsafe_allow_html=True,
    )
    c2.markdown(
        T.card("Clasificación", "<p>Un modelo de aprendizaje automático asigna a cada municipio una "
               "categoría de actividad sísmica: <b>Básico, Medio o Avanzado</b>.</p>"
               "<p style='margin-top:.6rem'>"
               + T.badge("Disponible" if cls_ok else "En desarrollo", "ok" if cls_ok else "wip")
               + "</p>", number=2),
        unsafe_allow_html=True,
    )
    c3.markdown(
        T.card("Priorización", "<p>Un agente de aprendizaje por refuerzo propone en qué orden "
               "revisar las zonas, comparado con una estrategia sencilla de referencia.</p>"
               "<p style='margin-top:.6rem'>"
               + T.badge("Disponible" if rl_ok else "En desarrollo", "ok" if rl_ok else "wip")
               + "</p>", number=3),
        unsafe_allow_html=True,
    )

    st.markdown("### ¿Por dónde empezar?")
    b1, b2, b3 = st.columns(3)
    for col, page in zip((b1, b2, b3), (C.PAGE_ZONE, C.PAGE_MAP, C.PAGE_COMPARE)):
        with col:
            st.button(page, on_click=go, args=(page,), key=f"go_{page}")
            st.caption(C.PAGE_HINTS[page])

    st.markdown("### Lo que esta herramienta **no** es")
    st.info(
        "**No predice terremotos:** no dice cuándo, dónde ni de qué tamaño será el próximo.  \n"
        "**No es una evaluación oficial del riesgo:** es un análisis académico y exploratorio.  \n"
        "**No mide vulnerabilidad:** no sabe qué tan resistentes son las construcciones.  \n"
        "Más detalle en «Fuentes y límites» y en el «Glosario»."
    )
    footer()


# ============================================================================ ZONA
def page_zone() -> None:
    st.title("📍 Explorar una zona")
    st.markdown(
        '<p class="lede">Elige un municipio para ver su actividad sísmica, la amenaza oficial '
        "estimada por el SGC y su población.</p>", unsafe_allow_html=True,
    )
    default_idx = int(municipalities.index[municipalities["municipio_key"] == "bucaramanga"][0])
    choice = st.selectbox("Municipio", municipalities["nombre"], index=default_idx, key="zona")
    muni = municipalities[municipalities["nombre"] == choice].iloc[0]
    info = da.zone_summary(events, muni, min_magnitude=min_mag)
    pop = da.zone_population(population, muni["cod_mpio"])
    rank_row = ranking[ranking["municipio_key"] == muni["municipio_key"]].iloc[0]

    meta = f"Código DANE {info['cod_mpio']}"
    if pop["poblacion_total"] is not None:
        meta += f" · {fmt(pop['poblacion_total'])} habitantes ({pop['anio']}, proyección)"
    T.zone_header(info["nombre"], meta)
    st.markdown(
        da.describe_zone(info, int(rank_row["puesto"]), len(ranking), min_mag),
    )

    st.markdown("#### Actividad sísmica registrada")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric(f"Sismos M ≥ {min_mag:g}", fmt(info["eventos_sobre_umbral"]),
              help="Conteo con la magnitud mínima elegida en «Opciones de visualización».")
    a2.metric("Sismos totales", fmt(info["eventos"]),
              help=f"{info['pct_del_catalogo']:.1f} % de todo el catálogo de Santander.")
    a3.metric("Magnitud máxima", "—" if info["magnitud_max"] is None else f"{info['magnitud_max']:.1f}")
    a4.metric("Profundidad típica",
              "—" if info["profundidad_mediana"] is None else f"{info['profundidad_mediana']:.0f} km",
              help="Mediana de la profundidad de los sismos de este municipio.")

    st.markdown("#### Amenaza oficial y población")
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("PGA esperada", f"{info['pga_tr475']:.3f} g",
              help="Amenaza Sísmica 2020 del SGC, periodo de retorno de 475 años, en la cabecera.")
    b2.metric("Intensidad esperada", f"{info['intensidad_esperada']:.0f}",
              help="Grado de intensidad sísmica esperado según el SGC.")
    b3.metric("Habitantes", "—" if pop["poblacion_total"] is None else fmt(pop["poblacion_total"]),
              help="Proyección del DANE.")
    b4.metric("Superficiales",
              "—" if info["pct_superficial"] is None else f"{info['pct_superficial']:.1f} %",
              help="Porcentaje de sismos a menos de 30 km de profundidad.")

    one = yearly[yearly["municipio_key"] == muni["municipio_key"]].assign(
        anio=lambda d: d["anio"].astype(str)
    ).set_index("anio")
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.markdown(f"**Sismos por año** (magnitud ≥ {min_mag:g})")
        st.bar_chart(one["n_sobre_umbral"], color=T.SERIES)
        last = events["utc_time"].max()
        st.caption(f"{last.year} es un año parcial: llega hasta {last:%d/%m/%Y}.")
    with right, st.container(border=True):
        st.markdown("**¿A qué profundidad ocurren?** (sismos por rango de 10 km)")
        hist = da.depth_histogram(events, muni["municipio_key"])
        if hist.empty:
            st.info("Este municipio no tiene sismos registrados.")
        else:
            st.bar_chart(hist.set_index("rango_km")["eventos"], color=T.SERIES)
            st.caption("Rango en km, de «000-010» (cerca de la superficie) hacia abajo.")

    with st.container(border=True):
        st.markdown("**Ubicación**")
        pts = da.map_table(events, municipalities, population, "eventos_umbral", min_mag,
                           highlight_key=muni["municipio_key"])
        st.map(pts, latitude="lat", longitude="lon", size="size_m", color="color", zoom=7)
        st.caption("El municipio elegido aparece resaltado en naranja; el resto, en azul.")

    with st.expander("¿Cómo leer estos números?"):
        st.markdown(
            "- **Sismos y magnitud:** vienen del catálogo del SGC. Muchos sismos pequeños no "
            "implican más peligro.\n"
            "- **PGA e intensidad:** son estimaciones oficiales de *amenaza*, iguales todos los "
            "años; se miden en un punto del municipio.\n"
            "- **Habitantes:** miden *exposición* (cuánta gente hay), no vulnerabilidad.\n"
            "- Nada de esto es una categoría de riesgo ni una predicción."
        )
    footer()


# ============================================================================ MAPA
def page_map() -> None:
    st.title("🗺️ Mapa de Santander")
    st.markdown(
        '<p class="lede">Cada punto es la cabecera de un municipio. Cuanto más grande y más '
        "oscuro, mayor es el valor del indicador elegido.</p>", unsafe_allow_html=True,
    )
    label = st.selectbox("Indicador", list(da.MAP_METRICS), key="mapa_metrica")
    metric = da.MAP_METRICS[label]
    pts = da.map_table(events, municipalities, population, metric, min_mag)
    left, right = st.columns([3, 2])
    with left, st.container(border=True):
        st.map(pts, latitude="lat", longitude="lon", size="size_m", color="color", zoom=7)
    with right, st.container(border=True):
        st.markdown(f"**Los 10 municipios con mayor valor**  \n_{label}_")
        top = pts.nlargest(10, "valor")[["nombre", "valor"]].rename(
            columns={"nombre": "Municipio", "valor": "Valor"})
        st.dataframe(top, hide_index=True)
    if metric == "pga_tr475":
        st.caption("La amenaza oficial varía poco entre municipios: todo Santander tiene amenaza alta.")
    elif metric in da.LOG_SCALE_METRICS:
        st.caption(
            "Tamaño y color usan una escala logarítmica: así se distinguen los municipios con pocos "
            "sismos o pocos habitantes, aunque algunos concentren muchísimos más."
        )
    footer()


# ============================================================================ COMPARAR
def page_compare() -> None:
    st.title("⚖️ Comparar zonas")
    st.markdown(
        '<p class="lede">Selecciona hasta 6 municipios y un indicador para ver cómo se comparan '
        "año por año.</p>", unsafe_allow_html=True,
    )
    metrics = {
        f"Sismos por año (magnitud ≥ {min_mag:g})": "n_sobre_umbral",
        "Sismos por año (todos)": "n_eventos",
        "Magnitud máxima del año": "magnitud_max",
        "Profundidad típica (km)": "profundidad_mediana",
        "% de sismos superficiales": "pct_superficial",
        "Habitantes (proyección)": "poblacion_total",
        f"Sismos (M ≥ {min_mag:g}) por 100 000 habitantes": "eventos_por_100mil",
    }
    defaults = [n for n in ("Bucaramanga", "Los Santos", "Zapatoca") if n in set(municipalities["nombre"])]
    c1, c2 = st.columns([3, 2])
    picked = c1.multiselect("Municipios (hasta 6)", municipalities["nombre"], default=defaults,
                            max_selections=6, key="comparar")
    metric_label = c2.selectbox("Indicador", list(metrics), key="indicador")
    if not picked:
        st.info("Selecciona al menos un municipio para comparar.")
        footer()
        return

    keys = [municipalities.loc[municipalities["nombre"] == n, "municipio_key"].iloc[0] for n in picked]
    table = da.compare_zones(yearly, keys, metrics[metric_label])[keys].rename(columns=names)
    table.index = table.index.astype(str)
    with st.container(border=True):
        st.markdown(f"**{metric_label}**")
        st.line_chart(table, color=T.CATEGORICAL[: len(keys)])
        if metrics[metric_label] == "eventos_por_100mil":
            st.caption("Es una razón descriptiva entre sismos y habitantes; no es una medida de riesgo.")
    static = municipalities[municipalities["nombre"].isin(picked)][
        ["nombre", "cod_mpio", "n_eventos_catalogo", "pga_tr475", "intensidad_esperada"]
    ].rename(columns={
        "nombre": "Municipio", "cod_mpio": "Código DANE", "n_eventos_catalogo": "Sismos (total)",
        "pga_tr475": "PGA oficial (g)", "intensidad_esperada": "Intensidad esperada",
    })
    st.markdown("**Datos fijos de cada municipio**")
    st.dataframe(static, hide_index=True)
    footer()


# ============================================================================ CLASIFICACIÓN / PRIORIZACIÓN
def _artifact_notice(prefix: str, text: str) -> None:
    item = [s for s in da.model_status() if s["componente"].startswith(prefix)][0]
    if item["disponible"]:
        st.success(f"Modelo disponible (`{item['archivo']}`). La integración con esta pantalla está en curso.")
    else:
        st.info(
            f"**Aún no disponible.** {text}\n\nArchivo requerido: `{item['archivo']}`. "
            "Mientras no exista, esta pantalla no muestra resultados de ejemplo."
        )


def page_class() -> None:
    st.title("🧠 Clasificación")
    st.markdown(
        '<p class="lede">Aquí se mostrará, para cada municipio, su categoría de actividad sísmica '
        "—<b>Básico</b>, <b>Medio</b> o <b>Avanzado</b>— y qué tan seguro está el modelo.</p>",
        unsafe_allow_html=True,
    )
    _artifact_notice("Clasificador", "El clasificador supervisado aún no está entrenado.")
    c1, c2 = st.columns(2)
    c1.markdown(
        T.card("Cómo se construirá", "<ul><li>La categoría de un año se define con la actividad del "
               "<b>año siguiente</b>.</li><li>El modelo solo usa información hasta el año actual.</li>"
               "<li>Los umbrales se ajustan solo con años de entrenamiento.</li>"
               "<li>Se prueba con años que el modelo no vio.</li></ul>"),
        unsafe_allow_html=True,
    )
    c2.markdown(
        T.card("Cómo se evaluará", "<ul><li>Exactitud, precisión y recall por categoría.</li>"
               "<li>Matriz de confusión.</li><li>Comparación contra la estrategia «el año que viene "
               "será igual que este».</li><li>Si no la supera, se reportará tal cual.</li></ul>"),
        unsafe_allow_html=True,
    )
    st.caption("Las categorías son una clasificación exploratoria propia del proyecto, no categorías oficiales.")
    footer()


def page_prio() -> None:
    st.title("🎯 Priorización")
    st.markdown(
        '<p class="lede">Aquí se mostrará el orden en que un agente de aprendizaje por refuerzo '
        "propone revisar las zonas, y cómo se compara con una regla simple.</p>",
        unsafe_allow_html=True,
    )
    _artifact_notice("Política", "El agente de aprendizaje por refuerzo aún no está entrenado.")
    c1, c2 = st.columns(2)
    c1.markdown(
        T.card("Qué decide el agente", "<p>Dado un conjunto de zonas candidatas, elige cuál revisar "
               "primero. Aprende de miles de episodios simulados con datos históricos reales.</p>"),
        unsafe_allow_html=True,
    )
    c2.markdown(
        T.card("Cómo sabremos que aprendió", "<ul><li>Curva de recompensa a lo largo del "
               "entrenamiento.</li><li>Evaluación en años que no usó para aprender.</li>"
               "<li>Comparación con una estrategia de referencia sencilla.</li></ul>"),
        unsafe_allow_html=True,
    )
    st.caption("La priorización es exploratoria: ordena zonas para revisarlas, no estima daños ni predice sismos.")
    footer()


# ============================================================================ CALIDAD
def page_catalog() -> None:
    st.title("📊 Calidad de los datos")
    st.markdown(
        '<p class="lede">Antes de interpretar los números conviene saber qué tan comparables son '
        "los años entre sí.</p>", unsafe_allow_html=True,
    )
    mc = da.load_mc_table()
    a, b = st.columns(2)
    with a, st.container(border=True):
        st.markdown("**Sismos registrados por año (todo Santander)**")
        per_year = events.groupby(events["utc_time"].dt.year).size().rename("sismos")
        per_year.index = per_year.index.astype(str)
        st.bar_chart(per_year, color=T.SERIES)
        st.caption("El aumento no significa que haya más sismos: se detectan más eventos pequeños.")
    with b, st.container(border=True):
        st.markdown("**Magnitud mínima que el catálogo registra completa (Mc)**")
        st.line_chart(mc.assign(anio=mc["anio"].astype(str)).set_index("anio")["mc_maxc"], color=T.SERIES)
        st.caption("Por debajo de esa magnitud faltan eventos. Más bajo = mejor detección.")
    st.warning(
        "**El catálogo no es homogéneo.** Hacia 2018 cambian el tipo de magnitud dominante, el "
        "número de estaciones que registran cada evento y la proporción de sismos pequeños. Antes de "
        "2009 la detección es menor. Por eso se recomienda contar sismos de magnitud 2,5 o más."
    )
    with st.expander("Ver la tabla por año"):
        st.dataframe(
            mc.rename(columns={"anio": "Año", "n_eventos": "Sismos", "mc_maxc": "Mc",
                               "n_sobre_mc": "Sobre Mc", "valor_b": "Valor b"}).round(2),
            hide_index=True,
        )
    footer()


# ============================================================================ FUENTES
def page_sources() -> None:
    st.title("📚 Fuentes y límites")
    st.markdown(
        '<p class="lede">De dónde salen los datos y qué hay que tener en cuenta al usarlos.</p>',
        unsafe_allow_html=True,
    )
    cols = st.columns(len(C.SOURCES))
    for col, src in zip(cols, C.SOURCES):
        col.markdown(
            T.card(src["titulo"],
                   f"<p><b>{src['entidad']}</b></p><p style='margin-top:.4rem'>{src['aporta']}</p>"
                   f"<p style='margin-top:.4rem'><b>Cobertura:</b> {src['cobertura']}</p>"
                   f"<p style='margin-top:.4rem'><b>Límite:</b> {src['limite']}</p>"),
            unsafe_allow_html=True,
        )
    st.markdown("### Límites generales")
    for item in C.LIMITATIONS:
        st.markdown(f"- {item}")
    with st.expander("Documentación técnica completa de las fuentes"):
        st.markdown(da.read_sources_doc())
    footer()


# ============================================================================ GLOSARIO
def page_glossary() -> None:
    st.title("❓ Glosario")
    st.markdown(
        '<p class="lede">Los términos que aparecen en la aplicación, en lenguaje sencillo.</p>',
        unsafe_allow_html=True,
    )
    query = st.text_input("Buscar un término", key="glosario_busqueda", placeholder="Ej.: magnitud, PGA…")
    shown = [(t, d) for t, d in C.GLOSSARY
             if not query or query.lower() in t.lower() or query.lower() in d.lower()]
    if not shown:
        st.info("No hay términos que coincidan con la búsqueda.")
    for term, definition in shown:
        with st.expander(term):
            st.markdown(definition)
    footer()


# ---- enrutador -------------------------------------------------------------------------------
ROUTES = {
    C.PAGE_HOME: page_home, C.PAGE_ZONE: page_zone, C.PAGE_MAP: page_map,
    C.PAGE_COMPARE: page_compare, C.PAGE_CLASS: page_class, C.PAGE_PRIO: page_prio,
    C.PAGE_CATALOG: page_catalog, C.PAGE_SOURCES: page_sources, C.PAGE_GLOSSARY: page_glossary,
}
ROUTES[st.session_state["nav"]]()
