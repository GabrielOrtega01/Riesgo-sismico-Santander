"""Pruebas con eventos SINTÉTICOS (no son datos reales)."""
import numpy as np
import pandas as pd
import pytest

from src.services import data_access as da


@pytest.fixture
def events():
    rows = [
        # municipio_key, fecha, magnitud, profundidad
        ("alfa", "2020-03-01", 2.0, 150), ("alfa", "2020-06-01", 3.1, 10),
        ("alfa", "2022-01-01", 2.6, 145), ("beta", "2021-05-01", 2.7, 20),
        ("beta", "2021-09-01", 1.5, 160),
    ]
    return pd.DataFrame({
        "id": [f"S{i}" for i in range(len(rows))],
        "municipio_key": [r[0] for r in rows],
        "utc_time": pd.to_datetime([r[1] for r in rows], utc=True),
        "magnitude": [r[2] for r in rows],
        "depth": [r[3] for r in rows],
    })


@pytest.fixture
def municipalities():
    return pd.DataFrame({
        "cod_mpio": ["68001", "68002", "68003"],
        "municipio_key": ["alfa", "beta", "gamma"],
        "municipio_oficial": ["ALFA", "BETA", "GAMMA"],
        "nombre": ["Alfa", "Beta", "Gamma"],
        "pga_tr475": [0.25, 0.22, 0.24], "pga_tr2475": [0.45, 0.4, 0.42],
        "intensidad_esperada": [6.0, 7.0, 6.0],
    })


def test_pretty_name_keeps_articles_lowercase():
    assert da.pretty_name("SAN VICENTE DE CHUCURÍ") == "San Vicente de Chucurí"
    assert da.pretty_name("EL CARMEN DE CHUCURÍ") == "El Carmen de Chucurí"
    assert da.pretty_name("LOS SANTOS") == "Los Santos"


def test_catalog_summary(events):
    s = da.catalog_summary(events)
    assert s["eventos"] == 5 and s["municipios"] == 2
    assert s["magnitud_max"] == 3.1
    assert s["pct_profundos_100km"] == pytest.approx(60.0)


def test_yearly_indicators_builds_complete_grid_with_zeros(events):
    y = da.yearly_indicators(events, min_magnitude=2.5)
    assert len(y) == 2 * 3                                  # 2 municipios × 2020..2022
    cell = y.set_index(["municipio_key", "anio"])
    assert cell.loc[("alfa", 2020), "n_eventos"] == 2
    assert cell.loc[("alfa", 2020), "n_sobre_umbral"] == 1   # solo la de M 3,1
    assert cell.loc[("beta", 2020), "n_eventos"] == 0       # año sin eventos = 0
    assert np.isnan(cell.loc[("beta", 2020), "magnitud_max"])
    assert cell.loc[("alfa", 2020), "pct_superficial"] == pytest.approx(50.0)
    assert cell["n_eventos"].sum() == len(events)           # no se pierde ni duplica nada


def test_zone_summary_with_and_without_events(events, municipalities):
    a = da.zone_summary(events, municipalities.iloc[0], min_magnitude=2.5)
    assert a["eventos"] == 3 and a["eventos_sobre_umbral"] == 2
    assert a["magnitud_max"] == 3.1
    assert a["pct_del_catalogo"] == pytest.approx(60.0)

    g = da.zone_summary(events, municipalities.iloc[2], min_magnitude=2.5)   # gamma: sin eventos
    assert g["eventos"] == 0
    assert g["magnitud_max"] is None and g["profundidad_mediana"] is None


def test_depth_histogram_counts_all_events(events):
    h = da.depth_histogram(events, "alfa", bin_km=10)
    assert h["eventos"].sum() == 3
    assert h.iloc[0]["rango_km"] == "000-010"
    assert da.depth_histogram(events, "gamma").empty


def test_compare_zones_pivots_by_year(events):
    y = da.yearly_indicators(events, min_magnitude=2.5)
    table = da.compare_zones(y, ["alfa", "beta"], "n_eventos")
    assert list(table.index) == [2020, 2021, 2022]
    assert table.loc[2021, "beta"] == 2


def test_model_status_lists_expected_artifacts(tmp_path, monkeypatch):
    fake = tmp_path / "clasificador.joblib"
    fake.write_bytes(b"x")
    monkeypatch.setattr(da, "MODEL_ARTIFACTS", {"Clasificador (Básico / Medio / Avanzado)": fake})
    monkeypatch.setattr(da, "ROOT", tmp_path)
    status = da.model_status()
    assert status == [{"componente": "Clasificador (Básico / Medio / Avanzado)",
                       "archivo": "clasificador.joblib", "disponible": True}]
