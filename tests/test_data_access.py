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


@pytest.fixture
def population():
    rows = []
    for code, base in (("68001", 1000), ("68002", 400), ("68003", 50)):
        for year in (2020, 2021, 2022):
            total = base + 10 * (year - 2020)
            rows.append({"cod_mpio": code, "anio": year, "poblacion_total": total,
                         "pct_poblacion_cabecera": 80.0})
    return pd.DataFrame(rows)


@pytest.fixture
def geo_municipalities(municipalities):
    return municipalities.assign(lat_cabecera=[7.0, 6.0, 8.0], lon_cabecera=[-73.0, -73.5, -72.8])


def test_add_population_merges_by_year_without_losing_rows(events, municipalities, population):
    y = da.yearly_indicators(events, min_magnitude=2.5)
    out = da.add_population(y, municipalities, population)
    assert len(out) == len(y)
    cell = out.set_index(["municipio_key", "anio"])
    assert cell.loc[("alfa", 2021), "poblacion_total"] == 1010
    # alfa 2020: 1 evento >= 2.5 (M 3,1) sobre 1000 habitantes
    assert cell.loc[("alfa", 2020), "eventos_por_100mil"] == pytest.approx(1 / 1000 * 100_000)
    assert "cod_mpio" not in out.columns


def test_zone_population_defaults_to_latest_year(population):
    last = da.zone_population(population, "68001")
    assert (last["anio"], last["poblacion_total"]) == (2022, 1020)
    year = da.zone_population(population, "68002", 2020)
    assert year["poblacion_total"] == 400
    assert da.zone_population(population, "99999")["poblacion_total"] is None


def test_rank_zones_orders_by_events_and_handles_ties(events, municipalities):
    r = da.rank_zones(events, municipalities, min_magnitude=2.5)
    assert r.iloc[0]["municipio_key"] == "alfa" and r.iloc[0]["puesto"] == 1   # alfa tiene 2
    by_key = r.set_index("municipio_key")["puesto"]
    assert by_key["beta"] == 2                       # beta tiene 1
    assert by_key["gamma"] == 3                      # gamma sin eventos
    assert r["eventos_umbral"].sum() == 3


def test_describe_zone_uses_only_real_figures(events, municipalities):
    info = da.zone_summary(events, municipalities.iloc[0], min_magnitude=2.5)
    text = da.describe_zone(info, rank=1, total_zones=3, min_magnitude=2.5)
    assert "Alfa" in text and "3" in text and "puesto **1 de 3**" in text
    assert "3.1" in text                              # magnitud máxima
    empty = da.zone_summary(events, municipalities.iloc[2], min_magnitude=2.5)
    assert "no hay sismos registrados" in da.describe_zone(empty, None, 3, 2.5)


def test_map_table_scales_and_highlights(events, geo_municipalities, population):
    t = da.map_table(events, geo_municipalities, population, "eventos_umbral", 2.5,
                     highlight_key="beta")
    assert len(t) == 3
    assert set(t.columns) >= {"lat", "lon", "size_m", "color", "valor", "nombre"}
    assert t.set_index("municipio_key").loc["alfa", "valor"] == 2
    row = t.set_index("municipio_key").loc["beta"]
    assert row["color"] == "#eb6834" and row["size_m"] == 14000
    assert t["color"].str.match(r"^#[0-9a-f]{6}$").all()
    with pytest.raises(ValueError, match="desconocido"):
        da.map_table(events, geo_municipalities, population, "otra_cosa", 2.5)


def test_map_table_uses_log_scale_for_counts_and_linear_for_hazard(events, geo_municipalities, population):
    counts = da.map_table(events, geo_municipalities, population, "eventos", 2.5).set_index("municipio_key")
    # alfa 3 eventos, beta 2, gamma 0: en escala log la distancia beta→gamma supera a la de alfa→beta
    gap_low = counts.loc["beta", "size_m"] - counts.loc["gamma", "size_m"]
    gap_high = counts.loc["alfa", "size_m"] - counts.loc["beta", "size_m"]
    assert gap_low > gap_high > 0

    hazard = da.map_table(events, geo_municipalities.assign(pga_tr475=[0.20, 0.25, 0.30]),
                          population, "pga_tr475", 2.5).set_index("municipio_key")
    # PGA 0,25 está a mitad de rango (0,20–0,30): norma 0,5 en escala lineal
    assert hazard.loc["beta", "size_m"] == pytest.approx(2500 + 9000 * 0.5 ** 0.5)


def test_map_table_population_uses_latest_year(events, geo_municipalities, population):
    t = da.map_table(events, geo_municipalities, population, "poblacion", 2.5)
    assert t.set_index("municipio_key").loc["alfa", "valor"] == 1020


def test_model_status_lists_expected_artifacts(tmp_path, monkeypatch):
    fake = tmp_path / "clasificador.joblib"
    fake.write_bytes(b"x")
    monkeypatch.setattr(da, "MODEL_ARTIFACTS", {"Clasificador (Básico / Medio / Avanzado)": fake})
    monkeypatch.setattr(da, "ROOT", tmp_path)
    status = da.model_status()
    assert status == [{"componente": "Clasificador (Básico / Medio / Avanzado)",
                       "archivo": "clasificador.joblib", "disponible": True}]
