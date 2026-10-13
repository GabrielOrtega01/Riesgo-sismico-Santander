"""Limpieza reproducible del catálogo sísmico del SGC.

Principios:
- Los datos originales (`data/raw/`) nunca se modifican; la salida va a `data/processed/`.
- Los eventos con valores extremos pero válidos se **conservan** (se marcan, no se eliminan).
- Solo se descartan filas imposibles de interpretar o físicamente inválidas, y cada descarte
  queda contado en el reporte de limpieza.
- No se imputan valores faltantes aquí: esa decisión pertenece a la construcción de variables.

Uso desde la raíz del repositorio:
    python -m src.data.preprocessing
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

from src.data.loaders import load_sgc_catalog

NUMERIC_COLUMNS = [
    "rms", "gap", "magnitude", "magnitude_error", "nst",
    "latitude", "latitude_error", "longitude", "longitude_error", "depth", "depth_error",
]
REQUIRED_COLUMNS = ["id", "utc_time", "latitude", "longitude", "magnitude", "depth", "place"]

# Cajas deliberadamente amplias: solo detectan errores de formato o de signo, no definen Santander.
LAT_RANGE = (-5.0, 14.0)
LON_RANGE = (-82.0, -66.0)
MAGNITUDE_RANGE = (-3.0, 10.0)
DEPTH_RANGE_KM = (-10.0, 700.0)
DEPTH_ERROR_EXTREME_KM = 100.0

# Alias de nombre verificados en el catálogo (clave normalizada -> clave normalizada canónica).
# Hipótesis pendiente de confirmar con el código DIVIPOLA del DANE (ver docs/fuentes_datos.md).
MUNICIPALITY_ALIASES = {
    "el carmen": "el carmen de chucuri",
    "jordan sube": "jordan",
}
TARGET_DEPARTMENT_KEY = "santander"

OUTPUT_COLUMNS = [
    "id", "utc_time", "latitude", "longitude", "depth", "magnitude", "mag_type",
    "magnitude_error", "latitude_error", "longitude_error", "depth_error",
    "rms", "gap", "nst", "status", "agency", "place",
    "municipio", "municipio_key", "departamento",
    "flag_profundidad_negativa", "flag_error_profundidad_extremo",
]

_PLACE_RE = re.compile(r"^(?P<municipio>.+?)\s+-\s+(?P<departamento>.+?),\s*Colombia\s*$")


# --------------------------------------------------------------------------- texto

def repair_mojibake(text):
    """Revierte UTF-8 leído como cp1252/latin-1 ('GirÃ³n' -> 'Girón'). Si no aplica, devuelve igual."""
    if not isinstance(text, str):
        return text
    for encoding in ("cp1252", "latin-1"):
        try:
            return text.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return text


def normalize_key(text):
    """Clave de comparación: sin tildes, minúsculas y espacios simples."""
    if not isinstance(text, str):
        return text
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.casefold().split())


def split_place(place):
    """'Los Santos - Santander, Colombia' -> ('Los Santos', 'Santander'). Sin patrón: (None, None)."""
    if not isinstance(place, str):
        return None, None
    match = _PLACE_RE.match(place.strip())
    if match is None:
        return None, None
    return match.group("municipio").strip(), match.group("departamento").strip()


def _display_names(names: pd.Series, keys: pd.Series) -> dict[str, str]:
    """Nombre a mostrar por clave: la forma con más caracteres no ASCII; desempata por frecuencia."""
    table = pd.DataFrame({"name": names, "key": keys}).dropna()
    result: dict[str, str] = {}
    for key, group in table.groupby("key"):
        counts = group["name"].value_counts()
        result[key] = sorted(
            counts.index,
            key=lambda n: (-sum(ord(c) > 127 for c in n), -int(counts[n]), n),
        )[0]
    return result


# ------------------------------------------------------------------------- limpieza

def _outlier_summary(df: pd.DataFrame, columns: list[str]) -> dict:
    """Valores atípicos por regla de Tukey (1,5·IQR). Solo descriptivo: no se elimina nada."""
    summary = {}
    for col in columns:
        values = df[col].dropna()
        if values.empty:
            continue
        q1, q3 = values.quantile([0.25, 0.75])
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        summary[col] = {
            "q1": float(q1), "q3": float(q3),
            "limite_inferior": float(low), "limite_superior": float(high),
            "n_atipicos": int(((values < low) | (values > high)).sum()),
            "minimo": float(values.min()), "maximo": float(values.max()),
        }
    return summary


def clean_catalog(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Limpia el catálogo crudo (todo texto) y devuelve (datos limpios, reporte)."""
    report: dict = {"filas_originales": int(len(raw))}
    df = raw.copy()

    # 1. Espacios y tipos
    for col in df.columns:
        df[col] = df[col].astype("string").str.strip()

    raw_time_present = df["utc_time"].notna()
    df["utc_time"] = pd.to_datetime(df["utc_time"], errors="coerce", utc=True)
    time_errors = int((raw_time_present & df["utc_time"].isna()).sum())

    format_errors: dict[str, int] = {}
    for col in NUMERIC_COLUMNS:
        present_before = int(df[col].notna().sum())
        # float64 estándar (NaN), no tipos anulables: así las comparaciones nunca producen NA
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
        lost = present_before - int(df[col].notna().sum())
        if lost:
            format_errors[col] = lost
    if time_errors:
        format_errors["utc_time"] = time_errors
    report["errores_de_formato_convertidos_a_nulo"] = format_errors

    # 2. Validez: se descartan solo filas sin campos esenciales o físicamente imposibles
    invalid = pd.Series(False, index=df.index)
    discarded: dict[str, int] = {}

    def discard(mask: pd.Series, reason: str) -> None:
        nonlocal invalid
        new = mask.fillna(True) & ~invalid
        discarded[reason] = int(new.sum())
        invalid = invalid | new

    discard(df[REQUIRED_COLUMNS].isna().any(axis=1), "campos_obligatorios_vacios")
    discard(~(df["latitude"].between(*LAT_RANGE) & df["longitude"].between(*LON_RANGE)),
            "coordenadas_fuera_de_rango")
    discard(~df["magnitude"].between(*MAGNITUDE_RANGE), "magnitud_fuera_de_rango")
    discard(~df["depth"].between(*DEPTH_RANGE_KM), "profundidad_fuera_de_rango")
    report["ids_descartados_por_invalidez"] = df.loc[invalid, "id"].astype(str).tolist()
    df = df.loc[~invalid].copy()

    # 3. Duplicados (primero por id y luego por evento físico idéntico; se conserva el menor id)
    df = df.sort_values(["utc_time", "id"], kind="stable")
    dup_id = df["id"].duplicated(keep="first")
    discarded["id_duplicado"] = int(dup_id.sum())
    df = df.loc[~dup_id]

    event_key = ["utc_time", "latitude", "longitude", "magnitude", "depth"]
    dup_event = df.duplicated(event_key, keep="first")
    discarded["evento_duplicado_mismo_instante_posicion_magnitud_profundidad"] = int(dup_event.sum())
    report["ids_eventos_duplicados_eliminados"] = df.loc[dup_event, "id"].astype(str).tolist()
    df = df.loc[~dup_event].copy()

    # 4. Ubicación administrativa a partir de `place`
    parsed = df["place"].map(split_place)
    municipio_raw = parsed.map(lambda t: t[0])
    departamento_raw = parsed.map(lambda t: t[1])
    municipio_fixed = municipio_raw.map(repair_mojibake)
    departamento_fixed = departamento_raw.map(repair_mojibake)

    dept_key = departamento_fixed.map(normalize_key)
    outside = dept_key.notna() & (dept_key != TARGET_DEPARTMENT_KEY)
    discarded["fuera_de_santander"] = int(outside.sum())
    keep = ~outside
    df = df.loc[keep].copy()
    municipio_raw = municipio_raw.loc[keep]
    municipio_fixed = municipio_fixed.loc[keep]
    departamento_fixed = departamento_fixed.loc[keep]

    keys = municipio_fixed.map(normalize_key).map(lambda k: MUNICIPALITY_ALIASES.get(k, k))
    names = _display_names(municipio_fixed, keys)
    df["municipio_key"] = keys
    df["municipio"] = keys.map(names)
    df["departamento"] = departamento_fixed
    report["filas_sin_municipio_interpretable"] = int(df["municipio_key"].isna().sum())

    variants = (
        pd.DataFrame({"key": keys, "raw": municipio_raw}).dropna()
        .groupby("key")["raw"].agg(lambda s: sorted(set(s)))
    )
    report["municipios_variantes_por_clave"] = {k: v for k, v in variants.items()}
    report["formas_de_municipio_crudas"] = int(municipio_raw.nunique())
    report["municipios_tras_normalizar"] = int(keys.nunique())

    # 5. Marcas sobre valores extremos (se conservan)
    df["flag_profundidad_negativa"] = df["depth"] < 0
    df["flag_error_profundidad_extremo"] = df["depth_error"] > DEPTH_ERROR_EXTREME_KM

    # 6. Salida
    df = df.sort_values(["utc_time", "id"], kind="stable").reset_index(drop=True)
    df = df[OUTPUT_COLUMNS]

    report["filas_descartadas_por_motivo"] = discarded
    report["filas_limpias"] = int(len(df))
    report["periodo_utc"] = [df["utc_time"].min().isoformat(), df["utc_time"].max().isoformat()]
    report["nulos_por_columna"] = {c: int(n) for c, n in df.isna().sum().items() if n}
    report["marcas"] = {
        "flag_profundidad_negativa": int(df["flag_profundidad_negativa"].sum()),
        "flag_error_profundidad_extremo": int(df["flag_error_profundidad_extremo"].sum()),
    }
    report["atipicos_conservados"] = _outlier_summary(
        df, ["magnitude", "depth", "rms", "gap", "nst",
             "magnitude_error", "latitude_error", "longitude_error", "depth_error"]
    )
    report["columnas_descartadas"] = {
        "local_time": "etiquetada +00:00 pero equivale a UTC-5; se usa utc_time",
    }
    return df, report


# ---------------------------------------------------------------------- ejecución

def run(raw_path: str | Path, out_dir: str | Path) -> dict:
    """Carga, limpia y guarda los datos procesados y el reporte. Devuelve el reporte."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = load_sgc_catalog(raw_path)
    clean, report = clean_catalog(raw)
    report["archivo_origen"] = Path(raw_path).name

    clean.to_csv(
        out_dir / "eventos_santander_limpio.csv.gz",
        index=False,
        compression={"method": "gzip", "mtime": 0},  # salida determinista
    )
    with open(out_dir / "limpieza_reporte.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, default=float)
        fh.write("\n")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Limpia el catálogo sísmico del SGC.")
    parser.add_argument(
        "--raw", default="data/raw/sgc_catalogo_santander_20060101_20261013.csv",
        help="Ruta del catálogo original.",
    )
    parser.add_argument("--out", default="data/processed", help="Carpeta de salida.")
    args = parser.parse_args(argv)

    report = run(args.raw, args.out)
    print(f"Filas originales: {report['filas_originales']}")
    print(f"Filas limpias:    {report['filas_limpias']}")
    print(f"Descartes:        {report['filas_descartadas_por_motivo']}")
    print(f"Municipios:       {report['formas_de_municipio_crudas']} formas -> "
          f"{report['municipios_tras_normalizar']} tras normalizar")


if __name__ == "__main__":
    main()
