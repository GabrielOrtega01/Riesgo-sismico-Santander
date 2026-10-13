"""Lectura de archivos de entrada.

El cargador no transforma el contenido: devuelve todo como texto para que la limpieza
(`preprocessing.py`) sea la única etapa que interpreta y corrige los datos.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

SGC_COLUMNS = [
    "id", "status", "rms", "agency", "gap", "place", "local_time", "utc_time",
    "magnitude", "magnitude_error", "nst", "mag_type", "latitude", "latitude_error",
    "longitude", "longitude_error", "depth", "depth_error",
]


class SchemaError(ValueError):
    """El archivo no tiene las columnas esperadas del catálogo."""


def load_sgc_catalog(path: str | Path) -> pd.DataFrame:
    """Lee el catálogo del SGC (CSV, CSV comprimido o Excel) sin transformarlo.

    Todas las columnas se devuelven como texto; las celdas vacías quedan como NaN y los
    textos literales como "NA" se conservan (no se interpretan como nulos).
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    suffixes = "".join(path.suffixes).lower()
    if suffixes.endswith((".xlsx", ".xlsm")):
        df = pd.read_excel(path, dtype=str, keep_default_na=False, na_values=[""])
    elif suffixes.endswith((".csv", ".csv.gz")):
        df = pd.read_csv(
            path, dtype=str, keep_default_na=False, na_values=[""], encoding="utf-8-sig"
        )
    else:
        raise ValueError(f"Formato no soportado: {path.name} (use .csv, .csv.gz o .xlsx)")

    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in SGC_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaError(f"Faltan columnas en {path.name}: {missing}")
    return df


def load_clean_events(path: str | Path) -> pd.DataFrame:
    """Lee los eventos ya limpios (salida de `preprocessing.run`) con sus tipos restaurados."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"No existe {path}. Genérelo con: python -m src.data.preprocessing"
        )
    df = pd.read_csv(path, keep_default_na=False, na_values=[""])
    df["utc_time"] = pd.to_datetime(df["utc_time"], utc=True)
    for col in ("flag_profundidad_negativa", "flag_error_profundidad_extremo"):
        df[col] = df[col].astype(bool)
    return df
