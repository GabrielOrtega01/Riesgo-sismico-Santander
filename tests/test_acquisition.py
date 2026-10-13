"""Pruebas sin red: el servicio remoto se sustituye por respuestas simuladas (sintéticas)."""
import pandas as pd
import pytest

from src.data import acquisition as acq


def _fake_divipola_rows():
    return [
        {"cod_mpio": "68001", "nom_mpio": "A", "tipo_municipio": "Municipio",
         "longitud": "-73,1", "latitud": "7,1"},
        {"cod_mpio": "68002", "nom_mpio": "B", "tipo_municipio": "Municipio",
         "longitud": "-73,2", "latitud": "6,9"},
    ]


def test_fetch_divipola_returns_expected_columns_as_text():
    df = acq.fetch_divipola(get_json=lambda url: _fake_divipola_rows())
    assert list(df.columns) == acq.DIVIPOLA_COLUMNS
    assert df.loc[0, "longitud"] == "-73,1"          # sin convertir


def test_fetch_divipola_detects_schema_change():
    with pytest.raises(ValueError, match="faltan"):
        acq.fetch_divipola(get_json=lambda url: [{"cod_mpio": "1"}])


def _identify_response(value="0.25"):
    return {"results": [
        {"layerId": 9, "attributes": {"Classify.Pixel Value": value}},
        {"layerId": 21, "attributes": {"Classify.Pixel Value": "6"}},
        {"layerId": 999, "attributes": {"Classify.Pixel Value": "1"}},   # capa ajena: se ignora
    ]}


def test_identify_point_parses_values_and_ignores_unknown_layers():
    vals = acq.identify_point(-73.1, 7.1, get_json=lambda url: _identify_response())
    assert vals["pga_tr475"] == pytest.approx(0.25)
    assert vals["intensidad_esperada"] == 6.0
    assert vals["pga_tr31"] is None                  # capa sin resultado


def test_identify_point_nodata_becomes_none():
    vals = acq.identify_point(-73.1, 7.1, get_json=lambda url: _identify_response("NoData"))
    assert vals["pga_tr475"] is None


def test_identify_point_raises_on_service_error():
    with pytest.raises(RuntimeError, match="error"):
        acq.identify_point(-73.1, 7.1, get_json=lambda url: {"error": {"code": 500}})


def test_sample_hazard_builds_one_row_per_municipality_with_provenance():
    div = pd.DataFrame(_fake_divipola_rows())
    full = {name: 0.1 for name in acq.HAZARD_LAYERS.values()}
    out = acq.sample_hazard(div, identify=lambda lon, lat: dict(full), pause_s=0)
    assert out["cod_mpio"].tolist() == ["68001", "68002"]
    assert out.loc[0, "lon_usada"] == pytest.approx(-73.1)
    assert out["fecha_consulta_utc"].str.endswith("Z").all()


def test_sample_hazard_fails_instead_of_writing_partial_data():
    div = pd.DataFrame(_fake_divipola_rows())
    partial = {name: 0.1 for name in acq.HAZARD_LAYERS.values()}
    partial["pga_tr475"] = None
    with pytest.raises(RuntimeError, match="pga_tr475"):
        acq.sample_hazard(div, identify=lambda lon, lat: dict(partial), pause_s=0)


def test_main_refuses_to_overwrite_raw_files(tmp_path):
    (tmp_path / acq.DIVIPOLA_FILE).write_text("x")
    with pytest.raises(SystemExit, match="no se sobrescriben"):
        acq.main(["--out", str(tmp_path)])
    assert (tmp_path / acq.DIVIPOLA_FILE).read_text() == "x"
