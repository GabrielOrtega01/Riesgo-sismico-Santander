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

def data_signature() -> tuple:
    """Huella de los archivos de datos y modelos (nombre, fecha y tamaño).

    Se pasa a las funciones con caché: si un despliegue cambia un archivo, la huella cambia y la
    caché se invalida sola (sin ella, una tabla vieja podría sobrevivir en memoria al redespliegue).
    """
    paths = [da.EVENTS_PATH, da.MUNICIPALITIES_PATH, da.POPULATION_PATH, da.MC_PATH,
             da.ROOT / "data" / "processed" / "panel_municipio_anio.csv",
             da.ROOT / "data" / "processed" / "predicciones_clasificador.csv",
             da.ROOT / "models" / "clasificador.joblib", da.ROOT / "models" / "politica_q.npz"]
    sig = []
    for p in paths:
        stat = p.stat() if p.exists() else None
        sig.append((p.name, stat.st_mtime_ns if stat else 0, stat.st_size if stat else 0))
    return tuple(sig)


SIG = data_signature()


@st.cache_data(show_spinner="Cargando catálogo…")
def get_events(sig: tuple) -> pd.DataFrame:
    return da.load_events()


@st.cache_data
def get_municipalities(sig: tuple) -> pd.DataFrame:
    return da.load_municipalities()


@st.cache_data
def get_population(sig: tuple) -> pd.DataFrame:
    return da.load_population()


@st.cache_data
def get_yearly(min_magnitude: float, sig: tuple) -> pd.DataFrame:
    return da.add_population(
        da.yearly_indicators(get_events(sig), min_magnitude=min_magnitude),
        get_municipalities(sig), get_population(sig),
    )


@st.cache_resource(show_spinner="Cargando modelos…")
def get_service(sig: tuple):
    from src.services.risk_analysis import RiskAnalysisService
    try:
        return RiskAnalysisService()
    except (FileNotFoundError, OSError):
        return None


try:
    events = get_events(SIG)
    municipalities = get_municipalities(SIG)
    population = get_population(SIG)
except FileNotFoundError as exc:
    st.error(
        f"Faltan datos procesados: {exc}\n\n"
        "Genérelos con `python -m src.data.preprocessing`, `python -m src.data.integration` "
        "y `python -m src.data.population`."
    )
    st.stop()

service = get_service(SIG)
summary = da.catalog_summary(events)
status = {s["componente"].split(" ")[0]: s["disponible"] for s in da.model_status()}


def go(page: str) -> None:
    st.session_state["nav"] = page


# ---- barra lateral (menú) -------------------------------------------------------------------
# Enlaces directos a una sección: ?pagina=zona | mapa | comparar | grupos | clasificacion | priorizacion …
PAGE_KEYS = {
    "inicio": C.PAGE_HOME, "zona": C.PAGE_ZONE, "mapa": C.PAGE_MAP, "comparar": C.PAGE_COMPARE,
    "grupos": C.PAGE_GROUPS, "clasificacion": C.PAGE_CLASS, "priorizacion": C.PAGE_PRIO,
    "calidad": C.PAGE_CATALOG, "fuentes": C.PAGE_SOURCES, "glosario": C.PAGE_GLOSSARY,
}
if "nav" not in st.session_state:
    st.session_state["nav"] = PAGE_KEYS.get(str(st.query_params.get("pagina", "")).lower(), C.PAGE_HOME)
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
            options=C.MAG_OPTIONS, value=da.DEFAULT_MIN_MAGNITUDE, key="min_mag",
            help="2,5 es la más segura para comparar años. Con 2,0 los años 2006–2008 no son "
                 "comparables. El mayor sismo del catálogo es de magnitud 6,4: con umbrales mayores "
                 "solo se cuentan los eventos más fuertes (pocos o ninguno).",
        )
    st.caption("Proyecto académico · UTS\n\nDatos: SGC y DANE\n\nNo es una evaluación oficial del riesgo.")

yearly = get_yearly(min_mag, SIG)
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
               "categoría de actividad sísmica para el año siguiente: <b>Bajo, Medio o Alto</b>.</p>"
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
    st.markdown("### Equipo")
    people = "".join(f"<li>{name}</li>" for name in C.TEAM)
    st.markdown(
        T.card("Hackathon CIAI UTSmart 2026 · Universitaria Tecnológica de Santander",
               f"<ul>{people}</ul><p style='margin-top:.5rem'>Datos oficiales: Servicio Geológico "
               "Colombiano y DANE · Nivel Avanzado: clasificación, grupos territoriales y "
               "priorización con aprendizaje por refuerzo.</p>"),
        unsafe_allow_html=True,
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
        meta += f" · {fmt(pop['poblacion_total'])} habitantes ({pop['año']}, proyección)"
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
        año=lambda d: d["año"].astype(str)
    ).set_index("año").rename_axis("Año")
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.markdown(f"**Sismos por año** (magnitud ≥ {min_mag:g})")
        st.bar_chart(one["n_sobre_umbral"].rename("Sismos"), color=T.SERIES)
        last = events["utc_time"].max()
        st.caption(f"{last.year} es un año parcial: llega hasta {last:%d/%m/%Y}.")
    with right, st.container(border=True):
        st.markdown("**¿A qué profundidad ocurren?** (sismos por rango de 10 km)")
        hist = da.depth_histogram(events, muni["municipio_key"])
        if hist.empty:
            st.info("Este municipio no tiene sismos registrados.")
        else:
            st.bar_chart(hist.rename(columns={"rango_km": "Rango (km)", "eventos": "Sismos"})
                         .set_index("Rango (km)")["Sismos"], color=T.SERIES)
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
    c1, c2 = st.columns([3, 2])
    label = c1.selectbox("Indicador", list(da.MAP_METRICS), key="mapa_metrica")
    order = c2.radio("Mostrar en la lista", ["Mayor valor", "Menor valor"], horizontal=True,
                     key="mapa_orden")
    metric = da.MAP_METRICS[label]
    lowest = order == "Menor valor"
    pts = da.map_table(events, municipalities, population, metric, min_mag)
    left, right = st.columns([3, 2])
    with left, st.container(border=True):
        st.map(pts, latitude="lat", longitude="lon", size="size_m", color="color", zoom=7)
    with right, st.container(border=True):
        st.markdown(f"**Los 10 municipios con {'menor' if lowest else 'mayor'} valor**  \n_{label}_")
        top = da.extreme_zones(pts, 10, lowest=lowest).rename(
            columns={"nombre": "Municipio", "valor": "Valor"})
        st.dataframe(top, hide_index=True)
        if lowest:
            st.caption("Menos sismos registrados no significa menos amenaza: la amenaza oficial "
                       "sigue siendo alta en todo Santander.")
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
    table.index.name = "Año"
    table.columns.name = None
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


# ============================================================================ GRUPOS (no supervisado)
def page_groups() -> None:
    st.title("🧩 Grupos territoriales")
    st.markdown(
        '<p class="lede">Sin usar etiquetas, un algoritmo de agrupamiento (K-means) reúne los '
        "municipios que se parecen en actividad sísmica, amenaza y exposición. Sirve para "
        "interpretar el territorio, no para clasificar riesgo.</p>", unsafe_allow_html=True,
    )
    if service is None:
        st.info("Aún no hay resultados de agrupamiento. Ejecute `python -m src.models.clustering`.")
        return
    gm, profiles, groups = service.group_metrics(), service.group_profiles(), service.groups
    k = gm["k"]
    a, b, c = st.columns(3)
    a.metric("Grupos encontrados", k, help="k elegido con el mejor índice de silueta entre 3 y 6.")
    b.metric("Variables usadas", gm["n_variables"],
             help="Promedio 2009–2025 de las variables del panel que no dependen del año.")
    c.metric("Índice de silueta", f"{gm['silhouette']:.2f}",
             help="De −1 a 1. Valores bajos (< 0,25) indican grupos poco separados.")
    st.caption(
        "El índice de silueta es bajo: los grupos son una **simplificación útil**, no fronteras "
        "nítidas. Un municipio (Los Santos) forma su propio grupo por concentrar la sismicidad."
    )

    merged = groups.merge(municipalities[["cod_mpio", "lat_cabecera", "lon_cabecera"]], on="cod_mpio")
    merged["color"] = merged["grupo"].map(lambda g: T.CATEGORICAL[(int(g) - 1) % len(T.CATEGORICAL)])
    merged["size_m"] = 9000
    left, right = st.columns([3, 2])
    with left, st.container(border=True):
        st.markdown("**Mapa por grupo** (cada color es un grupo)")
        st.map(merged.rename(columns={"lat_cabecera": "lat", "lon_cabecera": "lon"}),
               latitude="lat", longitude="lon", size="size_m", color="color", zoom=7)
        leg = " · ".join(
            f'<span style="color:{T.CATEGORICAL[(g - 1) % 6]}">■</span> Grupo {g} ({gm["tamanos"][str(g)]})'
            for g in range(1, k + 1))
        st.markdown(f'<p class="footnote">{leg}</p>', unsafe_allow_html=True)
    with right, st.container(border=True):
        st.markdown("**Cómo son los grupos** (promedio 2009–2025)")
        view = profiles[["n_m25_año", "magnitud_max_hist", "pct_superficial_año", "pga_tr475",
                         "poblacion_log10"]].rename(columns={
            "n_m25_año": "Sismos M≥2,5/año", "magnitud_max_hist": "Magnitud máx.",
            "pct_superficial_año": "% superficiales", "pga_tr475": "PGA (g)",
            "poblacion_log10": "log10 población"})
        view.index.name = "Grupo"
        st.dataframe(view.round(2))
    pick = st.selectbox("Ver los municipios de un grupo", list(range(1, k + 1)), key="grupo_sel",
                        format_func=lambda g: f"Grupo {g} ({gm['tamanos'][str(g)]} municipios)")
    members = groups[groups["grupo"] == pick].merge(
        municipalities[["cod_mpio", "nombre", "n_eventos_catalogo"]], on="cod_mpio")
    st.dataframe(members[["nombre", "cod_mpio", "n_eventos_catalogo"]].rename(
        columns={"nombre": "Municipio", "cod_mpio": "Código DANE", "n_eventos_catalogo": "Sismos (total)"}
    ).sort_values("Municipio"), hide_index=True)
    footer()


# ============================================================================ CLASIFICACIÓN
def page_class() -> None:
    st.title("🧠 Clasificación de actividad sísmica")
    st.markdown(
        '<p class="lede">Un modelo supervisado asigna a cada municipio una categoría de actividad '
        "para el <b>año siguiente</b> — <b>Bajo</b>, <b>Medio</b> o <b>Alto</b> — con la "
        "probabilidad de cada una.</p>", unsafe_allow_html=True,
    )
    if service is None:
        st.info("Aún no hay modelo entrenado. Ejecute `python -m src.models.classifier`.")
        return
    cm = service.classifier_metrics()
    st.info(
        "**Qué es y qué no es:** clasifica la *actividad sísmica histórica esperada* de cada "
        "municipio (cuántos sismos M ≥ 2,5 y qué tan fuerte el mayor). **No predice terremotos "
        "concretos** ni es una evaluación oficial del riesgo."
    )

    years = service.years
    year = st.selectbox("Año con información disponible (la categoría es para el año siguiente)",
                        years, index=len(years) - 1, key="clase_año")
    table = service.classify(year)
    counts = table["categoria"].value_counts().reindex(["Bajo", "Medio", "Alto"], fill_value=0)
    c1, c2, c3 = st.columns(3)
    c1.metric("Municipios en categoría Alto", int(counts["Alto"]))
    c2.metric("Medio", int(counts["Medio"]))
    c3.metric("Bajo", int(counts["Bajo"]))
    with st.container(border=True):
        st.markdown(f"**Categoría esperada en {year + 1} para cada municipio** (con datos hasta {year})")
        show = table.assign(zona=table["zona"].map(da.pretty_name))[
            ["zona", "categoria", "p_Alto", "p_Medio", "p_Bajo"]]
        st.dataframe(
            show.rename(columns={"zona": "Municipio", "categoria": "Categoría", "p_Alto": "P(Alto)",
                                 "p_Medio": "P(Medio)", "p_Bajo": "P(Bajo)"}),
            hide_index=True, column_config={
                "P(Alto)": st.column_config.ProgressColumn(format="%.2f", min_value=0.0, max_value=1.0),
                "P(Medio)": st.column_config.ProgressColumn(format="%.2f", min_value=0.0, max_value=1.0),
                "P(Bajo)": st.column_config.ProgressColumn(format="%.2f", min_value=0.0, max_value=1.0)})

    st.markdown("### ¿Qué tan bien funciona?")
    test, base = cm["prueba"], cm["linea_base"]["prueba"]
    m1, m2, m3 = st.columns(3)
    m1.metric("Exactitud en prueba", f"{test['exactitud']:.1%}",
              delta=f"{(test['exactitud'] - base['persistencia']['exactitud']) * 100:+.1f} pts vs. persistencia")
    m2.metric("F1 macro en prueba", f"{test['f1_macro']:.3f}",
              delta=f"{test['f1_macro'] - base['persistencia']['f1_macro']:+.3f} vs. persistencia")
    m3.metric("Municipios-año evaluados", test["n"])
    st.caption(
        f"Evaluado con años que el modelo nunca vio (2023–2024). Línea base «persistencia»: suponer "
        f"que el año siguiente será igual que este (exactitud {base['persistencia']['exactitud']:.1%}). "
        "La mejora es **modesta**: la actividad sísmica de un municipio es muy persistente."
    )
    a, b = st.columns(2)
    with a, st.container(border=True):
        st.markdown("**Matriz de confusión (prueba)**  \nFilas = real; columnas = predicho")
        mat = pd.DataFrame(test["matriz_confusion"], index=[f"Real {c}" for c in test["orden_clases"]],
                           columns=[f"Pred. {c}" for c in test["orden_clases"]])
        st.dataframe(mat)
        per = pd.DataFrame(test["por_clase"]).T.rename(
            columns={"precision": "Precisión", "recall": "Recall", "f1": "F1", "soporte": "Casos"})
        st.dataframe(per)
    with b, st.container(border=True):
        st.markdown("**Variables que más pesan**")
        imp = pd.Series(cm["importancias"])
        imp.index = [C.variable_label(n) for n in imp.index]
        imp = imp.sort_values()
        st.bar_chart(imp, horizontal=True, color=T.SERIES)
    with st.expander("Cómo se definen las categorías y cómo se validó"):
        th = cm["umbrales"]
        st.markdown(
            f"- **Actividad del año siguiente:** conteo de sismos M ≥ 2,5. **Bajo** si es "
            f"≤ {th['count_low']:.0f}; **Medio** si es ≤ {th['count_high']:.0f}; **Alto** si es mayor. "
            f"Si el mayor sismo del año es ≥ {th['strong_magnitude']:.1f}, la categoría sube un nivel.\n"
            "- **Umbrales ajustados solo con años de entrenamiento** (2009–2020) y luego congelados.\n"
            "- **División temporal:** entrenamiento ≤ 2020; validación 2021–2022; prueba 2023–2024. "
            "Nunca aleatoria.\n"
            f"- **Modelo elegido:** {cm['modelo_elegido']['modelo']} con variables "
            f"«{cm['modelo_elegido']['variables']}» ({cm['modelo_elegido']['criterio']}).\n"
            "- Comparado contra regresión logística y contra las líneas base (persistencia y clase "
            "mayoritaria)."
        )
    footer()


# ============================================================================ PRIORIZACIÓN
def page_prio() -> None:
    st.title("🎯 Priorización de zonas")
    st.markdown(
        '<p class="lede">Un agente de aprendizaje por refuerzo ordena las zonas según cuáles '
        "conviene revisar primero, combinando la categoría esperada, la actividad reciente, la "
        "amenaza oficial y la población.</p>", unsafe_allow_html=True,
    )
    if service is None:
        st.info("Aún no hay agente entrenado. Ejecute `python -m src.reinforcement_learning.training`.")
        return
    ar = service.agent_results()
    years = service.years
    c1, c2 = st.columns([2, 1])
    year = c1.selectbox("Año con información disponible", years, index=len(years) - 1, key="prio_año")
    k = c2.slider("Zonas a priorizar (K)", 3, 20, service.budget, key="prio_k",
                  help="El agente se entrenó con K = 10; otros valores solo cambian el corte de la lista.")
    ranking = service.prioritize(year, k=k)
    top = ranking.head(k).assign(municipio=lambda d: d["municipio"].map(da.pretty_name))
    with st.container(border=True):
        st.markdown(f"**Las {k} zonas que el agente propone revisar primero** (información hasta {year})")
        st.dataframe(
            top[["prioridad", "municipio", "prediccion", "p_Alto", "n_m25_año", "pga_tr475", "grupo"]]
            .rename(columns={"prioridad": "Puesto", "municipio": "Municipio", "prediccion": "Categoría esperada",
                             "p_Alto": "P(Alto)", "n_m25_año": f"Sismos M≥2,5 en {year}",
                             "pga_tr475": "PGA (g)", "grupo": "Grupo"}),
            hide_index=True)
    st.caption(
        "El puntaje del agente es el valor aprendido de priorizar una zona en su estado (categoría, "
        "actividad, amenaza, exposición). Los empates se resuelven con P(Alto) del clasificador."
    )

    st.markdown("### ¿Aprendió? ¿Es mejor que una regla sencilla?")
    ev = ar["evaluacion"]["validacion_y_prueba"]
    names = ["Agente de refuerzo (Q-learning)", "Persistencia (actividad del año)",
             "Solo clasificador (categoría esperada)", "Historia (promedio anual previo)", "Aleatoria"]
    comp = pd.DataFrame({
        "Estrategia": names,
        "Utilidad capturada": [ev[n]["utilidad_media"] for n in names],
        "Cobertura de sismos": [ev[n].get("cobertura_eventos_media") for n in names],
    })
    cc1, cc2 = st.columns([3, 2])
    with cc1, st.container(border=True):
        st.markdown(f"**Comparación en años no vistos (2021–2024), con K = {ar['configuracion']['presupuesto_K']}**")
        st.bar_chart(comp.set_index("Estrategia")["Utilidad capturada"], horizontal=True, color=T.SERIES)
        st.caption(
            f"Cota superior (conociendo el futuro): {ev['Óptimo (conoce el futuro; cota superior)']['utilidad_media']:.3f}. "
            "Utilidad = parte de la actividad y de la exposición del año siguiente que queda en las zonas elegidas."
        )
    with cc2, st.container(border=True):
        online = ar["evaluacion_en_linea"]["prueba"]
        st.markdown("**Protocolo secuencial (prueba)**")
        st.dataframe(pd.DataFrame({"Política": list(online), "Utilidad": list(online.values())}),
                     hide_index=True)
    st.warning(
        "**Lectura honesta:** el agente supera con claridad a la selección aleatoria y a las reglas "
        "fijas simples en el protocolo secuencial, y queda **a la par** de las mejores estrategias de "
        "referencia en el ranking, **sin superar de forma consistente** a la persistencia. Con solo 4 "
        "años de evaluación, esas diferencias no son concluyentes."
    )

    curve = pd.DataFrame(ar["curva_de_aprendizaje"])
    with st.container(border=True):
        st.markdown("**Curva de aprendizaje** (recompensa media por episodio durante el entrenamiento)")
        st.line_chart(
            curve.rename(columns={"episodio": "Episodio", "recompensa_media": "Recompensa media"})
            .set_index("Episodio")["Recompensa media"], color=T.SERIES)
        st.caption(
            f"Parte de {curve['recompensa_media'].iloc[0]:.2f} (alta exploración) y llega a "
            f"{curve['recompensa_media'].iloc[-1]:.2f}. Un agente sin entrenar obtiene 0 en el "
            "protocolo secuencial."
        )
    with st.expander("Cómo funciona el agente: estados, acciones y recompensa"):
        cfg = ar["configuracion"]
        st.markdown(
            "- **Problema:** cada año las zonas se presentan una a una y el agente decide "
            "*priorizar* o *saltar*, con un presupuesto de K revisiones.\n"
            "- **Estado:** categoría esperada (Bajo/Medio/Alto) × actividad del año (3 niveles) × "
            "amenaza (3 niveles) × exposición (3 niveles) × presupuesto restante × mitad del episodio.\n"
            "- **Acciones:** saltar o priorizar la zona presentada.\n"
            "- **Recompensa:** al priorizar, la utilidad real de la zona en el año siguiente "
            "(mitad parte de los sismos, mitad parte de la exposición afectada) menos un costo de "
            f"revisión de {cfg['costo_revision']}.\n"
            f"- **Algoritmo:** Q-learning tabular, {cfg['episodios']:,} episodios, α = {cfg['alpha']}, "
            f"γ = {cfg['gamma']}, ε decreciente. Entrenado con {cfg['años_entrenamiento'][0]}–"
            f"{cfg['años_entrenamiento'][1]}; validación {cfg['años_validacion']}; prueba "
            f"{cfg['años_prueba']}.\n"
            "- **Sesgos:** la actividad está muy concentrada (Los Santos); la recompensa no mide "
            "vulnerabilidad de las construcciones."
        )
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
        per_year = events.groupby(events["utc_time"].dt.year).size().rename("Sismos")
        per_year.index = per_year.index.astype(str)
        per_year.index.name = "Año"
        st.bar_chart(per_year, color=T.SERIES)
        st.caption("El aumento no significa que haya más sismos: se detectan más eventos pequeños.")
    with b, st.container(border=True):
        st.markdown("**Magnitud mínima que el catálogo registra completa (Mc)**")
        st.line_chart(
            mc.assign(año=mc["año"].astype(str)).rename(columns={"año": "Año", "mc_maxc": "Mc"})
            .set_index("Año")["Mc"], color=T.SERIES)
        st.caption("Por debajo de esa magnitud faltan eventos. Más bajo = mejor detección.")
    st.warning(
        "**El catálogo no es homogéneo.** Hacia 2018 cambian el tipo de magnitud dominante, el "
        "número de estaciones que registran cada evento y la proporción de sismos pequeños. Antes de "
        "2009 la detección es menor. Por eso se recomienda contar sismos de magnitud 2,5 o más."
    )
    with st.expander("Ver la tabla por año"):
        st.dataframe(
            mc.rename(columns={"año": "Año", "n_eventos": "Sismos", "mc_maxc": "Mc",
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
    C.PAGE_COMPARE: page_compare, C.PAGE_GROUPS: page_groups, C.PAGE_CLASS: page_class, C.PAGE_PRIO: page_prio,
    C.PAGE_CATALOG: page_catalog, C.PAGE_SOURCES: page_sources, C.PAGE_GLOSSARY: page_glossary,
}
ROUTES[st.session_state["nav"]]()
