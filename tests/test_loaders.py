import pandas as pd
import pytest

from src.data.loaders import SchemaError, load_clean_events, load_sgc_catalog


def _write_csv(path, df, encoding="utf-8"):
    df.to_csv(path, index=False, encoding=encoding)
    return path


def test_load_csv_returns_everything_as_text(tmp_path, make_raw):
    raw = make_raw({}, {"magnitude": "3.1"})
    path = _write_csv(tmp_path / "cat.csv", raw)
    loaded = load_sgc_catalog(path)
    assert len(loaded) == 2
    assert loaded["magnitude"].tolist() == ["2.0", "3.1"]
    assert all(isinstance(v, str) for v in loaded["latitude"])


def test_empty_cells_become_null_but_literal_NA_is_kept(tmp_path, make_raw):
    raw = make_raw({"magnitude_error": "", "place": "NA - Santander, Colombia"})
    loaded = load_sgc_catalog(_write_csv(tmp_path / "cat.csv", raw))
    assert pd.isna(loaded.loc[0, "magnitude_error"])
    assert loaded.loc[0, "place"] == "NA - Santander, Colombia"


def test_utf8_bom_is_handled(tmp_path, make_raw):
    raw = make_raw({})
    path = _write_csv(tmp_path / "bom.csv", raw, encoding="utf-8-sig")
    assert "id" in load_sgc_catalog(path).columns


def test_excel_is_supported(tmp_path, make_raw):
    raw = make_raw({}, {"magnitude": "4.5"})
    path = tmp_path / "cat.xlsx"
    raw.to_excel(path, index=False)
    loaded = load_sgc_catalog(path)
    assert len(loaded) == 2
    assert loaded["id"].tolist() == ["SYN000", "SYN001"]


def test_missing_columns_raise_schema_error(tmp_path, make_raw):
    raw = make_raw({}).drop(columns=["depth"])
    with pytest.raises(SchemaError, match="depth"):
        load_sgc_catalog(_write_csv(tmp_path / "bad.csv", raw))


def test_missing_file_and_unsupported_format(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_sgc_catalog(tmp_path / "no_existe.csv")
    other = tmp_path / "datos.txt"
    other.write_text("x")
    with pytest.raises(ValueError, match="no soportado"):
        load_sgc_catalog(other)


def test_load_clean_events_requires_existing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="preprocessing"):
        load_clean_events(tmp_path / "no_existe.csv.gz")
