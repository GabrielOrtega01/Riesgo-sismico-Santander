"""Pruebas con tablas SINTÉTICAS (no son datos reales)."""
import numpy as np
import pandas as pd
import pytest

from src.data.integration import (
    HAZARD_COLUMNS, IntegrationError, attach_municipality, build_municipality_table,
    geographic_consistency, haversine_km, integrate, load_divipola, load_hazard, parse_decimal,
)


def _divipola(rows=None):
    rows = rows or [
        ("68001", "Alfa", 7.0, -73.0),
        ("68002", "Beta", 6.0, -73.0),
        ("68003", "Gamma", 8.0, -73.0),
    ]
    return pd.DataFrame({
        "cod_mpio": [r[0] for r in rows],
        "municipio_oficial": [r[1].upper() for r in rows],
        "lat_cabecera": [r[2] for r in rows],
        "lon_cabecera": [r[3] for r in rows],
        "municipio_key": [r[1].lower() for r in rows],
    })


def _hazard(codes=("68001", "68002", "68003")):
    df = pd.DataFrame({"cod_mpio": list(codes)})
    for i, col in enumerate(HAZARD_COLUMNS):
        df[col] = 0.1 + 0.01 * i
    return df


def _events(keys, lats=None, lons=None):
    n = len(keys)
    return pd.DataFrame({
        "municipio_key": keys,
        "latitude": lats if lats is not None else [7.0] * n,
        "longitude": lons if lons is not None else [-73.0] * n,
        "magnitude": [2.0] * n,
    })


def test_parse_decimal_handles_comma_and_blanks():
    assert parse_decimal("-73,132562") == pytest.approx(-73.132562)
    assert parse_decimal("7.11647") == pytest.approx(7.11647)
    assert np.isnan(parse_decimal(""))
    assert np.isnan(parse_decimal(None))


def test_load_divipola_parses_and_normalizes(tmp_path):
    path = tmp_path / "div.csv"
    path.write_text(
        'cod_mpio,nom_mpio,tipo_municipio,longitud,latitud\n'
        '68001,BUCARAMANGA,Municipio,"-73,132562","7,11647"\n'
        '68615,RIONEGRO,Municipio,"-73,1","7,2"\n'
        '5001,SIN CERO,Municipio,"-75,5","6,2"\n', encoding="utf-8")
    div = load_divipola(path)
    assert div.loc[0, "lon_cabecera"] == pytest.approx(-73.132562)
    assert div.loc[0, "municipio_key"] == "bucaramanga"
    assert div.loc[2, "cod_mpio"] == "05001"          # se completa a 5 dígitos


def test_load_divipola_rejects_duplicates(tmp_path):
    path = tmp_path / "div.csv"
    path.write_text(
        'cod_mpio,nom_mpio,tipo_municipio,longitud,latitud\n'
        '68001,A,Municipio,"-73,1","7,1"\n68001,B,Municipio,"-73,2","7,2"\n', encoding="utf-8")
    with pytest.raises(IntegrationError, match="cod_mpio"):
        load_divipola(path)


def test_load_hazard_requires_columns(tmp_path):
    path = tmp_path / "haz.csv"
    _hazard().drop(columns=["pga_tr475"]).to_csv(path, index=False)
    with pytest.raises(IntegrationError, match="pga_tr475"):
        load_hazard(path)


def test_build_table_is_one_to_one_and_rejects_mismatch():
    table = build_municipality_table(_divipola(), _hazard())
    assert len(table) == 3
    assert table["pga_tr475"].notna().all()
    with pytest.raises(IntegrationError, match="sin pareja"):
        build_municipality_table(_divipola(), _hazard(codes=("68001", "68002", "99999")))


def test_build_table_rejects_missing_hazard_values():
    haz = _hazard()
    haz.loc[1, "pga_tr475"] = np.nan
    with pytest.raises(IntegrationError, match="sin valor de amenaza"):
        build_municipality_table(_divipola(), haz)


def test_attach_keeps_row_count_and_adds_code():
    muni = build_municipality_table(_divipola(), _hazard())
    ev = _events(["alfa", "alfa", "beta", "gamma", "alfa"])
    out = attach_municipality(ev, muni)
    assert len(out) == len(ev)
    assert out["cod_mpio"].tolist() == ["68001", "68001", "68002", "68003", "68001"]
    assert out["pga_tr475"].notna().all()


def test_attach_fails_for_unknown_municipality():
    muni = build_municipality_table(_divipola(), _hazard())
    with pytest.raises(IntegrationError, match="desconocido"):
        attach_municipality(_events(["alfa", "desconocido"]), muni)


def test_haversine_one_degree_of_latitude():
    assert haversine_km(7.0, -73.0, 8.0, -73.0) == pytest.approx(111.19, abs=0.1)
    assert haversine_km(7.0, -73.0, 7.0, -73.0) == pytest.approx(0.0)


def test_geographic_consistency_detects_nearest_and_far_events():
    muni = build_municipality_table(_divipola(), _hazard())
    ev = _events(
        ["alfa", "beta", "alfa"],
        lats=[7.0, 6.0, 6.0],          # el 3.º está sobre la cabecera de Beta pero etiquetado Alfa
        lons=[-73.0, -73.0, -73.0],
    )
    res = geographic_consistency(ev, muni)
    assert res["eventos_evaluados"] == 3
    assert res["porcentaje_municipio_es_la_cabecera_mas_cercana"] == pytest.approx(66.67, abs=0.01)
    assert res["distancia_a_cabecera_propia_km"]["maximo"] == pytest.approx(111.2, abs=0.2)


def test_integrate_reports_zero_event_municipalities():
    ev = _events(["alfa", "alfa", "beta"])
    muni, report = integrate(ev, _divipola(), _hazard())
    assert report["municipios"] == 3
    assert report["eventos_con_municipio_oficial"] == 3
    assert report["municipios_sin_eventos"] == 1          # gamma
    assert muni.set_index("municipio_key").loc["alfa", "n_eventos_catalogo"] == 2
