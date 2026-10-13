"""Pruebas con eventos, municipios y población SINTÉTICOS (no son datos reales)."""
import numpy as np
import pandas as pd
import pytest

from src.data import features as F


@pytest.fixture
def municipalities():
    # alfa y beta están a ~11 km entre sí; gamma está lejos (>100 km); "los santos" es la referencia
    return pd.DataFrame({
        "cod_mpio": ["68001", "68002", "68003", "68004"],
        "municipio_key": ["alfa", "beta", "gamma", "los santos"],
        "municipio_oficial": ["ALFA", "BETA", "GAMMA", "LOS SANTOS"],
        "lat_cabecera": [7.00, 7.10, 8.50, 6.80],
        "lon_cabecera": [-73.00, -73.00, -73.00, -73.10],
        "pga_tr475": [0.20, 0.25, 0.30, 0.26],
        "sa10_tr475": [0.08, 0.10, 0.09, 0.10],
        "intensidad_esperada": [6.0, 7.0, 6.0, 6.0],
    })


@pytest.fixture
def population():
    rows = []
    for code, base in (("68001", 10_000), ("68002", 20_000), ("68003", 5_000), ("68004", 8_000)):
        for year in range(2005, 2012):
            total = base + 100 * (year - 2005)
            rows.append({"cod_mpio": code, "anio": year, "poblacion_total": total,
                         "pct_poblacion_cabecera": 60.0})
    return pd.DataFrame(rows)


def _events(rows):
    """rows: (municipio_key, 'YYYY-MM-DD', magnitud, profundidad)."""
    n = len(rows)
    return pd.DataFrame({
        "id": [f"S{i}" for i in range(n)],
        "municipio_key": [r[0] for r in rows],
        "utc_time": pd.to_datetime([r[1] for r in rows], utc=True),
        "magnitude": [r[2] for r in rows],
        "depth": [r[3] for r in rows],
        "nst": [10.0] * n, "gap": [120.0] * n, "rms": [0.4] * n,
        "latitude_error": [3.0] * n, "longitude_error": [4.0] * n, "depth_error": [5.0] * n,
    })


@pytest.fixture
def events():
    return _events([
        ("alfa", "2008-01-10", 2.6, 150), ("alfa", "2008-01-20", 3.2, 20),
        ("alfa", "2008-06-05", 1.8, 140),
        ("alfa", "2009-03-01", 2.7, 145),
        ("beta", "2008-02-02", 2.5, 100), ("beta", "2009-09-09", 4.1, 10),
        ("gamma", "2009-05-05", 2.9, 160),
        ("alfa", "2010-04-04", 2.5, 148), ("alfa", "2010-11-11", 2.8, 30),
    ])


def _panel(events, municipalities, population, **kw):
    return F.build_feature_panel(events, municipalities, population,
                                 first_year=2006, last_year=kw.pop("last_year", 2010), **kw)


# ---- estructura ------------------------------------------------------------------------

def test_panel_has_one_row_per_municipality_year_and_all_columns(events, municipalities, population):
    p = _panel(events, municipalities, population)
    assert len(p) == 4 * 5                                            # 4 municipios × 2006–2010
    assert not p.duplicated(["cod_mpio", "anio"]).any()
    assert set(F.FEATURE_NAMES) <= set(p.columns)
    assert list(p.columns) == F.ID_COLUMNS + F.FEATURE_NAMES + F.FLAG_COLUMNS


def test_dictionary_covers_every_feature_once_and_has_at_least_20():
    names = [f.name for f in F.FEATURES]
    assert len(names) == len(set(names)) >= 20
    for f in F.FEATURES:
        for field in ("description", "source", "origin", "kind", "formula", "unit", "missing",
                      "why", "limitation"):
            assert getattr(f, field).strip(), f"{f.name}: campo vacío {field}"
        assert f.origin in ("original", "derivada")


def test_render_dictionary_lists_all_variables():
    doc = F.render_dictionary()
    for name in F.FEATURE_NAMES:
        assert f"`{name}`" in doc
    assert "Sin fuga temporal" in doc
    assert "Variables evaluadas y descartadas" in doc


def test_discarded_variables_are_not_in_the_panel(events, municipalities, population):
    p = _panel(events, municipalities, population)
    assert "meses_activos_m25" not in p.columns
    assert "frac_anios_activos_hist" not in p.columns
    assert "meses_activos_m25" not in F.FEATURE_NAMES


def test_requirement_of_20_variables_holds_without_regime_proxies():
    independent = [f for f in F.FEATURES if not f.regime_proxy]
    assert len(F.FEATURES) >= 20
    assert len(independent) >= 20
    assert {f.name for f in F.FEATURES if f.regime_proxy} == {
        "nst_mediano_anio", "error_horizontal_mediano_anio", "error_profundidad_mediano_anio"}


# ---- valores --------------------------------------------------------------------------

def test_yearly_counts_and_magnitude_features(events, municipalities, population):
    p = _panel(events, municipalities, population).set_index(["municipio_key", "anio"])
    a08 = p.loc[("alfa", 2008)]
    assert a08["n_m25_anio"] == 2                                     # 2,6 y 3,2 (no la de 1,8)
    assert a08["magnitud_max_anio"] == 3.2
    assert a08["magnitud_media_m25_anio"] == pytest.approx(2.9)
    assert a08["pct_m30_sobre_m25"] == pytest.approx(50.0)
    assert a08["profundidad_mediana_anio"] == 140                     # 150, 20, 140
    assert a08["pct_superficial_anio"] == pytest.approx(100 / 3)

    empty = p.loc[("gamma", 2008)]
    assert empty["n_m25_anio"] == 0 and not empty["tiene_eventos_anio"]
    assert np.isnan(empty["magnitud_max_anio"]) and np.isnan(empty["profundidad_mediana_anio"])


def test_historical_features_use_only_previous_years(events, municipalities, population):
    p = _panel(events, municipalities, population).set_index(["municipio_key", "anio"])
    # alfa: n_m25 = 2006:0, 2007:0, 2008:2, 2009:1, 2010:2
    assert np.isnan(p.loc[("alfa", 2006), "n_m25_hist_prom"])         # sin historia
    assert p.loc[("alfa", 2009), "n_m25_hist_prom"] == pytest.approx((0 + 0 + 2) / 3)
    assert p.loc[("alfa", 2010), "n_m25_hist_prom"] == pytest.approx((0 + 0 + 2 + 1) / 4)
    assert p.loc[("alfa", 2009), "magnitud_max_hist"] == 3.2          # no incluye 2009
    assert p.loc[("alfa", 2009), "n_m25_cambio_1a"] == -1
    assert p.loc[("alfa", 2008), "anios_historia"] == 2


def test_neighbors_within_50km_only(events, municipalities, population):
    p = _panel(events, municipalities, population).set_index(["municipio_key", "anio"])
    assert p.loc[("alfa", 2009), "n_m25_vecinos_anio"] == 1           # beta: 4,1 en 2009
    assert p.loc[("beta", 2009), "n_m25_vecinos_anio"] == 1           # alfa: 2,7 en 2009
    assert p.loc[("gamma", 2009), "n_m25_vecinos_anio"] == 0          # lejos de todos
    assert p.loc[("alfa", 2008), "n_m25_vecinos_anio"] == 1           # beta: 2,5 en 2008


def test_static_and_population_features(events, municipalities, population):
    p = _panel(events, municipalities, population).set_index(["municipio_key", "anio"])
    ref = p.loc[("los santos", 2008)]
    assert ref["distancia_los_santos_km"] == pytest.approx(0.0)
    assert p.loc[("alfa", 2008), "distancia_los_santos_km"] > 20
    assert p.loc[("beta", 2008), "sa10_sobre_pga"] == pytest.approx(0.10 / 0.25)
    assert p.loc[("alfa", 2008), "poblacion_log10"] == pytest.approx(np.log10(10_300))
    assert p.loc[("alfa", 2008), "crecimiento_poblacion_pct"] == pytest.approx(100 * (10_300 / 10_200 - 1))
    assert p.loc[("alfa", 2008), "pct_poblacion_cabecera"] == 60.0


# ---- sin fuga de información --------------------------------------------------------------

def test_no_future_leakage(events, municipalities, population):
    """Cambiar o agregar eventos de años posteriores a t no altera las variables del año t."""
    base = _panel(events, municipalities, population)
    future = _events([
        ("alfa", "2010-07-07", 6.5, 5), ("beta", "2010-08-08", 5.9, 5),
        ("gamma", "2010-09-09", 5.5, 5), ("alfa", "2011-01-01", 6.0, 5),
    ])
    changed = _panel(pd.concat([events, future], ignore_index=True), municipalities, population)
    for year in (2006, 2007, 2008, 2009):                             # años anteriores al cambio
        a = base[base["anio"] == year].reset_index(drop=True)
        b = changed[changed["anio"] == year].reset_index(drop=True)
        pd.testing.assert_frame_equal(a, b, check_exact=True, obj=f"panel {year}")
    # y el año del cambio sí cambia, para asegurar que la prueba detecta diferencias
    assert not base[base["anio"] == 2010].reset_index(drop=True).equals(
        changed[changed["anio"] == 2010].reset_index(drop=True))


def test_events_after_last_year_are_ignored(events, municipalities, population):
    late = _events([("alfa", "2012-02-02", 6.0, 5)])
    a = _panel(events, municipalities, population, last_year=2010)
    b = _panel(pd.concat([events, late], ignore_index=True), municipalities, population, last_year=2010)
    pd.testing.assert_frame_equal(a, b, check_exact=True)


# ---- reporte -----------------------------------------------------------------------------

def test_panel_report_structure(events, municipalities, population):
    p = _panel(events, municipalities, population)
    rep = F.panel_report(p)
    assert rep["n_variables"] == len(F.FEATURE_NAMES)
    assert set(rep["porcentaje_faltante_por_variable"]) == set(F.FEATURE_NAMES)
    assert set(rep["correlacion_con_el_anio"]) == set(F.FEATURE_NAMES)
    assert rep["anios_utilizables"][0] >= 2006 + F.MIN_HISTORY_YEARS
