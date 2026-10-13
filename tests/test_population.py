"""Pruebas con libros Excel SINTÉTICOS que imitan el formato del DANE (no son cifras reales)."""
import pandas as pd
import pytest

from src.data import population as pop


def _write_workbook(path, sheet, rows, header, junk_rows=3):
    """Escribe una hoja con filas de texto previas, el encabezado y las filas de datos."""
    lines = [["PROYECCIONES (texto previo)"] + [None] * (len(header) - 1)] * junk_rows
    lines += [header] + rows
    pd.DataFrame(lines).to_excel(path, sheet_name=sheet, header=False, index=False)


HEADER_A = ["DP", "DPNOM", "DPMP", "MPIO", "AÑO", "ÁREA GEOGRÁFICA", "Población"]   # serie 2005-2017
HEADER_B = ["DP", "DPNOM", "MPIO", "DPMP", "AÑO", "ÁREA GEOGRÁFICA", "TOTAL"]       # serie 2018-


def _rows_a(code, name, year, cab, rur, dpto=("68", "Santander")):
    return [
        [dpto[0], dpto[1], name, code, str(year), "Cabecera Municipal", str(cab)],
        [dpto[0], dpto[1], name, code, str(year), "Centros Poblados y Rural Disperso", str(rur)],
        [dpto[0], dpto[1], name, code, str(year), "Total", str(cab + rur)],
    ]


def _rows_b(code, name, year, cab, rur, dpto=("68", "Santander")):
    return [
        [dpto[0], dpto[1], code, name, str(year), "Cabecera Municipal", str(cab)],
        [dpto[0], dpto[1], code, name, str(year), "Centros Poblados y Rural Disperso", str(rur)],
        [dpto[0], dpto[1], code, name, str(year), "Total", str(cab + rur)],
    ]


@pytest.fixture
def workbooks(tmp_path):
    a, b = tmp_path / "a.xlsx", tmp_path / "b.xlsx"
    rows_a = (_rows_a("68001", "Alfa", 2017, 900, 100) + _rows_a("68002", "Beta", 2017, 400, 600)
              + _rows_a("05001", "Medellín", 2017, 5000, 50, dpto=("05", "Antioquia")))
    rows_b = (_rows_b("68001", "Alfa", 2018, 950, 105) + _rows_b("68002", "Beta", 2018, 410, 590)
              + _rows_b("05001", "Medellín", 2018, 5100, 50, dpto=("05", "Antioquia")))
    _write_workbook(a, "NuevaMpal", rows_a, HEADER_A, junk_rows=5)
    _write_workbook(b, "PobMunicipalxÁrea", rows_b, HEADER_B, junk_rows=2)
    return a, b


def test_read_sheet_finds_header_filters_santander_and_normalizes(workbooks):
    a, _ = workbooks
    df = pop.read_dane_sheet(a, "NuevaMpal")
    assert set(df["cod_mpio"]) == {"68001", "68002"}                # sin Antioquia
    assert set(df["area"]) == {"cabecera", "rural", "total"}
    row = df[(df["cod_mpio"] == "68001") & (df["area"] == "total")].iloc[0]
    assert row["poblacion"] == 1000 and row["año"] == 2017


def test_both_column_layouts_give_the_same_schema(workbooks):
    a, b = workbooks
    da_ = pop.read_dane_sheet(a, "NuevaMpal")
    db_ = pop.read_dane_sheet(b, "PobMunicipalxÁrea")
    assert list(da_.columns) == list(db_.columns) == ["cod_mpio", "año", "area", "poblacion"]
    assert set(db_["cod_mpio"]) == {"68001", "68002"}


def test_build_table_is_wide_one_row_per_municipality_year(workbooks, monkeypatch):
    a, b = workbooks
    monkeypatch.setattr(pop, "FIRST_YEAR", 2017)
    monkeypatch.setattr(pop, "LAST_YEAR", 2018)
    table = pop.build_population_table([
        pop.read_dane_sheet(a, "NuevaMpal"), pop.read_dane_sheet(b, "PobMunicipalxÁrea"),
    ])
    assert len(table) == 4
    r = table[(table["cod_mpio"] == "68002") & (table["año"] == 2018)].iloc[0]
    assert (r["poblacion_total"], r["poblacion_cabecera"], r["poblacion_rural"]) == (1000, 410, 590)
    assert r["pct_poblacion_cabecera"] == pytest.approx(41.0)
    assert r["serie"] == "2018-2042"


def test_validate_reports_coverage_and_series_jump(workbooks, monkeypatch):
    a, b = workbooks
    monkeypatch.setattr(pop, "FIRST_YEAR", 2017)
    monkeypatch.setattr(pop, "LAST_YEAR", 2018)
    table = pop.build_population_table([
        pop.read_dane_sheet(a, "NuevaMpal"), pop.read_dane_sheet(b, "PobMunicipalxÁrea"),
    ])
    rep = pop.validate_population(table, {"68001", "68002", "68003"})
    assert rep["municipios"] == 2
    assert rep["rejilla_completa_municipio_x_año"] is True
    assert rep["codigos_de_divipola_sin_poblacion"] == ["68003"]
    assert rep["codigos_sin_pareja_en_divipola"] == []
    assert rep["filas_total_distinto_de_cabecera_mas_rural"] == 0
    assert rep["continuidad_2017_2018"]["variacion_total_santander_pct"] == pytest.approx(
        (1055 + 1000) / (1000 + 1000) * 100 - 100, abs=0.01)


def test_duplicate_series_overlap_is_rejected(workbooks):
    a, _ = workbooks
    frame = pop.read_dane_sheet(a, "NuevaMpal")
    with pytest.raises(pop.PopulationError, match="repetidos"):
        pop.build_population_table([frame, frame])


def test_missing_header_raises(tmp_path):
    path = tmp_path / "x.xlsx"
    pd.DataFrame([["sin", "encabezado"], ["1", "2"]]).to_excel(path, sheet_name="Hoja", header=False, index=False)
    with pytest.raises(pop.PopulationError, match="encabezado"):
        pop.read_dane_sheet(path, "Hoja")


def test_unreadable_values_raise(tmp_path):
    path = tmp_path / "x.xlsx"
    rows = [["68", "Santander", "Alfa", "68001", "2017", "Total", "mil"]]
    _write_workbook(path, "NuevaMpal", rows, HEADER_A)
    with pytest.raises(pop.PopulationError, match="ilegible"):
        pop.read_dane_sheet(path, "NuevaMpal")
