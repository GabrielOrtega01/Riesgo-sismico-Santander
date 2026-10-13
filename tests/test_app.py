"""Pruebas de la interfaz con el motor de pruebas de Streamlit, sobre los datos procesados reales."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.services import data_access as da

APP = str(Path(__file__).resolve().parents[1] / "src" / "app.py")

pytestmark = pytest.mark.skipif(
    not (da.EVENTS_PATH.is_file() and da.MUNICIPALITIES_PATH.is_file()),
    reason="Faltan los datos procesados (ejecute preprocessing e integration).",
)


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    return at


def _metrics(at):
    return {m.label: m.value for m in at.metric}


def test_app_starts_without_errors_and_shows_scope_warning(app):
    assert not app.exception
    assert any("No predice" in w.value for w in app.warning)
    assert app.title[0].value == "Riesgo sísmico de Santander"


def test_zone_tab_lists_all_87_municipalities(app):
    zone = app.selectbox(key="zona")
    assert len(zone.options) == 87
    assert zone.value == "Bucaramanga"


def test_selecting_a_zone_updates_its_indicators(app):
    app.selectbox(key="zona").select("Los Santos").run()
    assert not app.exception
    m = _metrics(app)
    assert m["Eventos registrados"] == "103 545"        # cifra real del catálogo limpio
    assert m["Magnitud máxima"] == "6.4"


def test_classification_and_prioritization_are_pending_without_models(app):
    texts = [i.value for i in app.info]
    assert any("Aún no disponible" in t and "clasificador" in t.lower() for t in texts)
    assert any("Aún no disponible" in t and "agente" in t.lower() for t in texts)
    # no se muestran resultados inventados: ninguna probabilidad ni categoría aparece
    assert not any("Avanzado" in m for m in _metrics(app).values())


def test_magnitude_threshold_changes_counts(app):
    app.select_slider[0].set_value(3.0).run()
    assert not app.exception
    assert "Eventos M ≥ 3.0" in _metrics(app)
