"""Población municipal de Santander (proyecciones oficiales del DANE).

Fuente: dos libros Excel con proyecciones basadas en el Censo 2018, en formato largo
(departamento, municipio, año, área geográfica, población):
- 2005-2017 (hoja `NuevaMpal`)
- 2018-2042 (hoja `PobMunicipalxÁrea`)

La población es un indicador de **exposición**, no de amenaza ni de vulnerabilidad.

Uso desde la raíz del repositorio:
    python -m src.data.population
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

SANTANDER_DEPARTMENT_CODE = "68"
FIRST_YEAR, LAST_YEAR = 2005, 2026     # 2005 permite calcular variaciones desde 2006

SERIES = [
    ("DCD-area-proypoblacion-Mun-2005-2017_VP.xlsx", "NuevaMpal"),
    ("PPED-AreaMun-2018-2042_VP.xlsx", "PobMunicipalxÁrea"),
]
_AREA_MAP = {
    "cabecera municipal": "cabecera",
    "centros poblados y rural disperso": "rural",
    "total": "total",
}
_COLUMN_MAP = {
    "dp": "cod_dpto", "dpnom": "departamento", "mpio": "cod_mpio", "dpmp": "municipio",
    "año": "anio", "área geográfica": "area", "población": "poblacion", "total": "poblacion",
}


class PopulationError(ValueError):
    """El archivo del DANE no tiene el formato esperado o los datos son inconsistentes."""


def read_dane_sheet(path: str | Path, sheet_name: str) -> pd.DataFrame:
    """Lee una hoja de proyecciones en formato largo y devuelve solo Santander, normalizada."""
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, dtype=str)
    first_col = raw.iloc[:, 0].astype(str).str.strip().str.upper()
    header_rows = raw.index[first_col == "DP"]
    if len(header_rows) == 0:
        raise PopulationError(f"{Path(path).name}/{sheet_name}: no se encontró la fila de encabezado 'DP'")
    header = header_rows[0]

    df = raw.iloc[header + 1:].copy()
    df.columns = [str(c).strip().lower() for c in raw.iloc[header]]
    df = df.rename(columns=_COLUMN_MAP)
    needed = {"cod_dpto", "cod_mpio", "anio", "area", "poblacion"}
    if not needed.issubset(df.columns):
        raise PopulationError(f"{Path(path).name}: faltan columnas {sorted(needed - set(df.columns))}")

    df = df.dropna(subset=["cod_dpto", "cod_mpio", "anio", "area", "poblacion"])
    df["cod_dpto"] = df["cod_dpto"].str.strip().str.zfill(2)
    df = df[df["cod_dpto"] == SANTANDER_DEPARTMENT_CODE].copy()

    df["cod_mpio"] = df["cod_mpio"].str.strip().str.zfill(5)
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["poblacion"] = pd.to_numeric(df["poblacion"], errors="coerce")
    df["area"] = df["area"].str.strip().str.lower().map(_AREA_MAP)
    unknown = df["area"].isna() | df["anio"].isna() | df["poblacion"].isna()
    if unknown.any():
        raise PopulationError(f"{Path(path).name}: {int(unknown.sum())} filas con área, año o población ilegible")
    df["anio"] = df["anio"].astype(int)
    df["poblacion"] = df["poblacion"].astype(int)
    return df[["cod_mpio", "anio", "area", "poblacion"]]


def build_population_table(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Une las series y devuelve una fila por municipio y año (cabecera, rural y total)."""
    long = pd.concat(frames, ignore_index=True)
    long = long[(long["anio"] >= FIRST_YEAR) & (long["anio"] <= LAST_YEAR)]
    if long.duplicated(["cod_mpio", "anio", "area"]).any():
        raise PopulationError("Hay (municipio, año, área) repetidos entre las series")

    wide = long.pivot(index=["cod_mpio", "anio"], columns="area", values="poblacion").reset_index()
    wide.columns.name = None
    wide = wide.rename(columns={
        "total": "poblacion_total", "cabecera": "poblacion_cabecera", "rural": "poblacion_rural",
    })
    wide["pct_poblacion_cabecera"] = wide["poblacion_cabecera"] / wide["poblacion_total"] * 100
    wide["serie"] = np.where(wide["anio"] <= 2017, "2005-2017", "2018-2042")
    return wide.sort_values(["cod_mpio", "anio"]).reset_index(drop=True)


def validate_population(table: pd.DataFrame, expected_codes: set[str]) -> dict:
    """Comprobaciones de cobertura, coherencia aritmética y continuidad entre series."""
    codes = set(table["cod_mpio"])
    years = sorted(table["anio"].unique())
    expected_years = list(range(FIRST_YEAR, LAST_YEAR + 1))
    grid_complete = len(table) == len(codes) * len(expected_years)

    parts = table["poblacion_cabecera"] + table["poblacion_rural"]
    diff = (table["poblacion_total"] - parts).abs()

    pivot = table.pivot(index="cod_mpio", columns="anio", values="poblacion_total")
    jump = (pivot[2018] / pivot[2017] - 1) * 100 if {2017, 2018} <= set(pivot.columns) else None
    report = {
        "municipios": len(codes),
        "anios": [int(years[0]), int(years[-1])],
        "filas": int(len(table)),
        "rejilla_completa_municipio_x_anio": bool(grid_complete),
        "codigos_sin_pareja_en_divipola": sorted(codes - expected_codes),
        "codigos_de_divipola_sin_poblacion": sorted(expected_codes - codes),
        "nulos": int(table[["poblacion_total", "poblacion_cabecera", "poblacion_rural"]].isna().sum().sum()),
        "filas_total_distinto_de_cabecera_mas_rural": int((diff > 1).sum()),
        "diferencia_maxima_total_vs_suma": int(diff.max()),
    }
    if jump is not None:
        report["continuidad_2017_2018"] = {
            "variacion_total_santander_pct": round(float(
                (pivot[2018].sum() / pivot[2017].sum() - 1) * 100), 2),
            "variacion_por_municipio_pct": {
                "p5": round(float(jump.quantile(0.05)), 1),
                "mediana": round(float(jump.median()), 1),
                "p95": round(float(jump.quantile(0.95)), 1),
                "minimo": round(float(jump.min()), 1),
                "maximo": round(float(jump.max()), 1),
            },
            "municipios_con_salto_mayor_a_10_pct": int((jump.abs() > 10).sum()),
        }
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Procesa la población municipal del DANE.")
    parser.add_argument("--raw", default="data/raw")
    parser.add_argument("--divipola", default="data/raw/divipola_municipios_santander.csv")
    parser.add_argument("--out", default="data/processed")
    args = parser.parse_args(argv)

    frames = [read_dane_sheet(Path(args.raw) / f, sheet) for f, sheet in SERIES]
    table = build_population_table(frames)
    codes = set(pd.read_csv(args.divipola, dtype=str)["cod_mpio"].str.zfill(5))
    report = validate_population(table, codes)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "poblacion_municipal_anual.csv", index=False, float_format="%.4f")
    with open(out / "poblacion_reporte.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
