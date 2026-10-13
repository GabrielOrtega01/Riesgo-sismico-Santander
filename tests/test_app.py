"""Pruebas de la interfaz con el motor de pruebas de Streamlit, sobre los datos procesados reales."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.services import data_access as da
from src.ui import content as C

APP = str(Path(__file__).resolve().parents[1] / "src" / "app.py")

pytestmark = pytest.mark.skipif(
    not (da.EVENTS_PATH.is_file() and da.MUNICIPALITIES_PATH.is_file() and da.POPULATION_PATH.is_file()),
    reason="Faltan los datos procesados (ejecute preprocessing, integration y population).",
)


def _fresh() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    return at


@pytest.fixture(scope="module")
def home():
    return _fresh()


def _metrics(at):
    return {m.label: m.value for m in at.metric}


def _goto(at, page):
    at.radio(key="nav").set_value(page).run()
    assert not at.exception
    return at


def test_home_explains_the_project_and_shows_real_figures(home):
    assert not home.exception
    assert home.radio(key="nav").value == C.PAGE_HOME
    m = _metrics(home)
    assert m["Sismos registrados"] == "184 722"
    assert m["Municipios"] == "87"
    text = " ".join(md.value for md in home.markdown)
    assert "¿De qué trata?" in text and "¿Cómo funciona?" in text
    assert "Seismox" in text and "Seismox" in " ".join(md.value for md in home.sidebar.markdown)
    assert any("No predice terremotos" in i.value for i in home.info)


def test_menu_lists_all_pages(home):
    assert list(home.radio(key="nav").options) == C.PAGES


def test_every_page_renders_without_errors():
    at = _fresh()
    for page in C.PAGES:
        _goto(at, page)


def test_home_buttons_navigate():
    at = _fresh()
    at.button(key=f"go_{C.PAGE_ZONE}").click().run()
    assert at.radio(key="nav").value == C.PAGE_ZONE
    assert at.selectbox(key="zona").value == "Bucaramanga"


def test_zone_page_lists_87_municipalities_and_updates():
    at = _goto(_fresh(), C.PAGE_ZONE)
    zone = at.selectbox(key="zona")
    assert len(zone.options) == 87
    zone.select("Los Santos").run()
    assert not at.exception
    m = _metrics(at)
    assert m["Sismos totales"] == "103 545"          # cifra real del catálogo limpio
    assert m["Magnitud máxima"] == "6.4"
    assert "Habitantes" in m and m["Habitantes"] != "—"


def test_classification_and_prioritization_are_pending_without_models():
    at = _fresh()
    _goto(at, C.PAGE_CLASS)
    assert any("Aún no disponible" in i.value for i in at.info)
    assert not any(k for k in _metrics(at))           # ningún número inventado
    _goto(at, C.PAGE_PRIO)
    assert any("Aún no disponible" in i.value for i in at.info)
    assert not any(k for k in _metrics(at))


def test_magnitude_threshold_changes_zone_labels():
    at = _fresh()
    at.select_slider(key="min_mag").set_value(3.0).run()
    _goto(at, C.PAGE_ZONE)
    assert "Sismos M ≥ 3" in _metrics(at)


def test_map_page_offers_all_indicators():
    at = _goto(_fresh(), C.PAGE_MAP)
    assert list(at.selectbox(key="mapa_metrica").options) == list(da.MAP_METRICS)
    at.selectbox(key="mapa_metrica").select("Población proyectada").run()
    assert not at.exception


def test_compare_page_default_and_population_indicator():
    at = _goto(_fresh(), C.PAGE_COMPARE)
    assert at.multiselect(key="comparar").value == ["Bucaramanga", "Los Santos", "Zapatoca"]
    options = list(at.selectbox(key="indicador").options)
    assert "Habitantes (proyección)" in options
    at.selectbox(key="indicador").select("Habitantes (proyección)").run()
    assert not at.exception


def test_glossary_search_filters_terms():
    at = _goto(_fresh(), C.PAGE_GLOSSARY)
    labels = lambda: [e.label for e in at.expander if "Opciones" not in e.label]
    assert len(labels()) == len(C.GLOSSARY)
    at.text_input(key="glosario_busqueda").set_value("PGA").run()
    assert 1 <= len(labels()) < len(C.GLOSSARY)
    at.text_input(key="glosario_busqueda").set_value("zzzz-no-existe").run()
    assert labels() == []
