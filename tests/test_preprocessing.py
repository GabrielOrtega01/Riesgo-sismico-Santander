import json

import pandas as pd
import pytest

from src.data.loaders import load_clean_events
from src.data.preprocessing import (
    clean_catalog, normalize_key, repair_mojibake, run, split_place,
)


# ---- funciones de texto -------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("GirÃ³n", "Girón"),
    ("VÃ©lez", "Vélez"),
    ("El PeÃ±Ã³n", "El Peñón"),
    ("San Vicente de ChucurÃ\xad", "San Vicente de Chucurí"),
    ("Bolívar", "Bolívar"),          # ya correcto: no se toca
    ("Los Santos", "Los Santos"),
])
def test_repair_mojibake(raw, expected):
    assert repair_mojibake(raw) == expected


def test_repair_mojibake_ignores_non_text():
    assert repair_mojibake(None) is None


def test_normalize_key_removes_accents_case_and_extra_spaces():
    assert normalize_key("  Santa  Helena DEL Opón ") == "santa helena del opon"
    assert normalize_key("Bolívar") == normalize_key("Bolivar") == "bolivar"


def test_split_place():
    assert split_place("Los Santos - Santander, Colombia") == ("Los Santos", "Santander")
    assert split_place("texto libre sin patrón") == (None, None)
    assert split_place(None) == (None, None)


# ---- limpieza ---------------------------------------------------------------

def test_types_and_timezone(make_raw):
    clean, _ = clean_catalog(make_raw({}))
    assert str(clean["utc_time"].dt.tz) == "UTC"
    assert pd.api.types.is_float_dtype(clean["magnitude"])
    assert "local_time" not in clean.columns


def test_municipality_variants_are_unified(make_raw):
    raw = make_raw(
        {"place": "GirÃ³n - Santander, Colombia"},
        {"place": "Girón - Santander, Colombia"},
        {"place": "Giron - Santander, Colombia"},
        {"place": "El Carmen - Santander, Colombia"},
        {"place": "El Carmen De Chucurí - Santander, Colombia"},
        {"place": "Jordán Sube - Santander, Colombia"},
        {"place": "Jordán - Santander, Colombia"},
    )
    clean, report = clean_catalog(raw)
    assert set(clean["municipio_key"]) == {"giron", "el carmen de chucuri", "jordan"}
    # el nombre mostrado conserva las tildes
    assert clean.loc[clean["municipio_key"] == "giron", "municipio"].unique().tolist() == ["Girón"]
    assert report["formas_de_municipio_crudas"] == 7
    assert report["municipios_tras_normalizar"] == 3


def test_duplicates_by_id_and_by_event_are_removed_keeping_lowest_id(make_raw):
    raw = make_raw({}, {}, {})
    raw.loc[1, "id"] = raw.loc[0, "id"]                       # mismo id
    raw.loc[2, ["utc_time", "latitude", "longitude", "magnitude", "depth"]] = (
        raw.loc[0, ["utc_time", "latitude", "longitude", "magnitude", "depth"]].values
    )                                                          # mismo evento, otro id
    clean, report = clean_catalog(raw)
    assert len(clean) == 1
    assert clean["id"].tolist() == ["SYN000"]
    assert report["filas_descartadas_por_motivo"]["id_duplicado"] == 1
    assert report["ids_eventos_duplicados_eliminados"] == ["SYN002"]


def test_invalid_rows_are_discarded_and_counted(make_raw):
    raw = make_raw(
        {},
        {"latitude": "60.0"},                  # fuera de rango
        {"utc_time": "no-es-fecha"},           # fecha ilegible
        {"magnitude": "abc"},                  # número ilegible
        {"depth": "9999"},                     # profundidad imposible
    )
    clean, report = clean_catalog(raw)
    assert clean["id"].tolist() == ["SYN000"]
    reasons = report["filas_descartadas_por_motivo"]
    assert reasons["campos_obligatorios_vacios"] == 2   # fecha y magnitud ilegibles
    assert reasons["coordenadas_fuera_de_rango"] == 1
    assert reasons["profundidad_fuera_de_rango"] == 1
    assert report["errores_de_formato_convertidos_a_nulo"] == {"magnitude": 1, "utc_time": 1}
    assert report["filas_originales"] - report["filas_limpias"] == 4


def test_events_outside_santander_are_removed(make_raw):
    raw = make_raw({}, {"place": "Cúcuta - Norte de Santander, Colombia"})
    clean, report = clean_catalog(raw)
    assert len(clean) == 1
    assert report["filas_descartadas_por_motivo"]["fuera_de_santander"] == 1


def test_unparseable_place_is_kept_without_municipality(make_raw):
    clean, report = clean_catalog(make_raw({"place": "Zona marítima"}))
    assert len(clean) == 1
    assert pd.isna(clean.loc[0, "municipio"])
    assert report["filas_sin_municipio_interpretable"] == 1


def test_extreme_values_are_kept_and_flagged(make_raw):
    raw = make_raw(
        {"magnitude": "6.4"},
        {"depth": "-5"},
        {"depth_error": "1000"},
    )
    clean, report = clean_catalog(raw)
    assert len(clean) == 3
    assert clean["magnitude"].max() == 6.4
    assert clean["flag_profundidad_negativa"].tolist() == [False, True, False]
    assert clean["flag_error_profundidad_extremo"].tolist() == [False, False, True]
    assert report["marcas"] == {"flag_profundidad_negativa": 1,
                                "flag_error_profundidad_extremo": 1}


def test_missing_values_are_reported_not_imputed(make_raw):
    raw = make_raw({"magnitude_error": ""}, {"gap": ""}, {})
    clean, report = clean_catalog(raw)
    assert clean["magnitude_error"].isna().sum() == 1
    assert clean["gap"].isna().sum() == 1
    assert report["nulos_por_columna"] == {"magnitude_error": 1, "gap": 1}


def test_flags_are_plain_booleans_even_when_the_measure_is_missing(make_raw):
    # Regresión: un depth_error ausente producía NA en la marca y, al releer, True.
    clean, report = clean_catalog(make_raw({"depth_error": ""}, {"depth_error": "500"}))
    assert clean["flag_error_profundidad_extremo"].dtype == bool
    assert clean["flag_profundidad_negativa"].dtype == bool
    assert clean["flag_error_profundidad_extremo"].tolist() == [False, True]
    assert "flag_error_profundidad_extremo" not in report["nulos_por_columna"]
    assert clean["magnitude"].dtype == "float64"


def test_output_is_sorted_by_time(make_raw):
    raw = make_raw({}, {}, {}).iloc[::-1].reset_index(drop=True)
    clean, _ = clean_catalog(raw)
    assert clean["utc_time"].is_monotonic_increasing


def test_input_is_not_modified(make_raw):
    raw = make_raw({"place": "GirÃ³n - Santander, Colombia"})
    snapshot = raw.copy(deep=True)
    clean_catalog(raw)
    pd.testing.assert_frame_equal(raw, snapshot)


# ---- ejecución completa -----------------------------------------------------

def test_run_writes_deterministic_outputs_and_roundtrips(tmp_path, make_raw):
    raw = make_raw({}, {"place": "GirÃ³n - Santander, Colombia"}, {"depth": "-5"})
    raw_path = tmp_path / "raw.csv"
    raw.to_csv(raw_path, index=False)
    raw_bytes = raw_path.read_bytes()

    out1, out2 = tmp_path / "o1", tmp_path / "o2"
    report = run(raw_path, out1)
    run(raw_path, out2)

    assert raw_path.read_bytes() == raw_bytes                      # el original no cambia
    gz1 = (out1 / "eventos_santander_limpio.csv.gz").read_bytes()
    gz2 = (out2 / "eventos_santander_limpio.csv.gz").read_bytes()
    assert gz1 == gz2                                               # reproducible bit a bit

    saved = json.loads((out1 / "limpieza_reporte.json").read_text(encoding="utf-8"))
    assert saved["filas_limpias"] == report["filas_limpias"] == 3

    loaded = load_clean_events(out1 / "eventos_santander_limpio.csv.gz")
    assert len(loaded) == 3
    assert str(loaded["utc_time"].dt.tz) == "UTC"
    assert loaded["flag_profundidad_negativa"].dtype == bool
    assert "Girón" in set(loaded["municipio"])
