"""Integración de fuentes oficiales por municipio.

Fuentes:
- Catálogo sísmico del SGC (eventos limpios, con `municipio_key`).
- DIVIPOLA del DANE: código oficial, nombre y coordenadas de la cabecera de los 87 municipios.
- Amenaza Sísmica 2020 del SGC: valor de los ráster de PGA/Sa/intensidad en esas cabeceras.

Clave de integración: el nombre de municipio normalizado (`municipio_key`) para unir el catálogo
con DIVIPOLA, y el código `cod_mpio` para unir DIVIPOLA con la amenaza. Todas las uniones se
validan (uno a uno o muchos a uno) para no duplicar ni perder eventos.

Uso desde la raíz del repositorio:
    python -m src.data.integration
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.loaders import load_clean_events
from src.data.preprocessing import normalize_key

HAZARD_COLUMNS = [
    "pga_tr31", "pga_tr225", "pga_tr475", "pga_tr975", "pga_tr2475",
    "sa02_tr475", "sa10_tr475", "intensidad_esperada",
]
EARTH_RADIUS_KM = 6371.0088


class IntegrationError(ValueError):
    """Las fuentes no son compatibles o la unión produciría duplicados o pérdidas."""


def parse_decimal(text) -> float:
    """Convierte '-73,132562' (coma decimal, como entrega el DANE) o '-73.13' en float."""
    if isinstance(text, (int, float, np.floating)):
        return float(text)
    if not isinstance(text, str) or not text.strip():
        return float("nan")
    return float(text.strip().replace(",", "."))


# -------------------------------------------------------------------------- carga

def load_divipola(path: str | Path) -> pd.DataFrame:
    """Lee DIVIPOLA (original) y devuelve una fila por municipio con coordenadas numéricas."""
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    needed = {"cod_mpio", "nom_mpio", "longitud", "latitud"}
    if not needed.issubset(raw.columns):
        raise IntegrationError(f"DIVIPOLA sin columnas {sorted(needed - set(raw.columns))}")
    out = pd.DataFrame({
        "cod_mpio": raw["cod_mpio"].str.strip().str.zfill(5),
        "municipio_oficial": raw["nom_mpio"].str.strip(),
        "lon_cabecera": raw["longitud"].map(parse_decimal),
        "lat_cabecera": raw["latitud"].map(parse_decimal),
    })
    out["municipio_key"] = out["municipio_oficial"].map(normalize_key)
    for col in ("cod_mpio", "municipio_key"):
        if out[col].duplicated().any():
            raise IntegrationError(f"DIVIPOLA tiene valores repetidos en {col}")
    if out[["lon_cabecera", "lat_cabecera"]].isna().any().any():
        raise IntegrationError("DIVIPOLA tiene coordenadas vacías")
    return out


def load_hazard(path: str | Path) -> pd.DataFrame:
    """Lee el muestreo de amenaza (una fila por municipio)."""
    df = pd.read_csv(path, dtype={"cod_mpio": str})
    df["cod_mpio"] = df["cod_mpio"].str.zfill(5)
    missing = [c for c in ["cod_mpio", *HAZARD_COLUMNS] if c not in df.columns]
    if missing:
        raise IntegrationError(f"Amenaza sin columnas {missing}")
    if df["cod_mpio"].duplicated().any():
        raise IntegrationError("Amenaza tiene códigos de municipio repetidos")
    return df


# ------------------------------------------------------------------- integración

def build_municipality_table(divipola: pd.DataFrame, hazard: pd.DataFrame) -> pd.DataFrame:
    """Une DIVIPOLA con amenaza (uno a uno por `cod_mpio`). Falla si no coinciden exactamente."""
    only_div = set(divipola["cod_mpio"]) - set(hazard["cod_mpio"])
    only_haz = set(hazard["cod_mpio"]) - set(divipola["cod_mpio"])
    if only_div or only_haz:
        raise IntegrationError(
            f"Códigos sin pareja. Solo DIVIPOLA: {sorted(only_div)}; solo amenaza: {sorted(only_haz)}"
        )
    cols = ["cod_mpio", *HAZARD_COLUMNS]
    table = divipola.merge(hazard[cols], on="cod_mpio", how="left", validate="one_to_one")
    if table[HAZARD_COLUMNS].isna().any().any():
        raise IntegrationError("Hay municipios sin valor de amenaza")
    return table.sort_values("cod_mpio").reset_index(drop=True)


def attach_municipality(events: pd.DataFrame, municipalities: pd.DataFrame) -> pd.DataFrame:
    """Añade código y atributos oficiales a cada evento (muchos a uno por `municipio_key`).

    Falla si algún evento no encuentra municipio: nunca se pierden ni se duplican filas.
    """
    out = events.merge(municipalities, on="municipio_key", how="left", validate="many_to_one")
    if len(out) != len(events):
        raise IntegrationError("La unión cambió el número de eventos")
    if out["cod_mpio"].isna().any():
        bad = sorted(out.loc[out["cod_mpio"].isna(), "municipio_key"].dropna().unique())
        raise IntegrationError(f"Eventos sin municipio oficial: {bad[:10]}")
    return out


def haversine_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Distancia en km entre puntos (admite arreglos con broadcasting)."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi, dlmb = p2 - p1, np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def geographic_consistency(events: pd.DataFrame, municipalities: pd.DataFrame) -> dict:
    """¿El municipio de `place` es la cabecera más cercana al epicentro?

    Responde si `place` es el municipio que contiene el epicentro o solo una referencia, y
    cuantifica la distancia entre el epicentro y la cabecera de su municipio.
    """
    muni = municipalities.reset_index(drop=True)
    lat_m = muni["lat_cabecera"].to_numpy()[None, :]
    lon_m = muni["lon_cabecera"].to_numpy()[None, :]
    lat_e = events["latitude"].to_numpy()[:, None]
    lon_e = events["longitude"].to_numpy()[:, None]
    dist = haversine_km(lat_e, lon_e, lat_m, lon_m)                  # (n_eventos, n_municipios)

    nearest = dist.argmin(axis=1)
    index_of = pd.Series(muni.index.to_numpy(), index=muni["municipio_key"])
    own = events["municipio_key"].map(index_of).to_numpy()
    d_own = dist[np.arange(len(events)), own]
    return {
        "eventos_evaluados": int(len(events)),
        "porcentaje_municipio_es_la_cabecera_mas_cercana": round(float((nearest == own).mean() * 100), 2),
        "distancia_a_cabecera_propia_km": {
            "mediana": round(float(np.median(d_own)), 1),
            "p90": round(float(np.quantile(d_own, 0.90)), 1),
            "maximo": round(float(d_own.max()), 1),
        },
    }


def integrate(events: pd.DataFrame, divipola: pd.DataFrame, hazard: pd.DataFrame):
    """Ejecuta la integración completa. Devuelve (tabla de municipios, reporte)."""
    municipalities = build_municipality_table(divipola, hazard)
    enriched = attach_municipality(events, municipalities)   # valida; no se guarda aparte

    counts = enriched.groupby("cod_mpio").size()
    municipalities["n_eventos_catalogo"] = (
        municipalities["cod_mpio"].map(counts).fillna(0).astype(int)
    )
    report = {
        "municipios": int(len(municipalities)),
        "eventos": int(len(events)),
        "eventos_con_municipio_oficial": int(enriched["cod_mpio"].notna().sum()),
        "municipios_sin_eventos": int((municipalities["n_eventos_catalogo"] == 0).sum()),
        "municipios_con_menos_de_30_eventos": int((municipalities["n_eventos_catalogo"] < 30).sum()),
        "compatibilidad_geografica": geographic_consistency(events, municipalities),
        "compatibilidad_temporal": (
            "La amenaza es un mapa estático de 2020 (sin dimensión temporal); el catálogo cubre "
            "2006-2026. No hay variación temporal de amenaza dentro del análisis."
        ),
        "compatibilidad_metodologica": (
            "Amenaza muestreada en la cabecera municipal (punto DIVIPOLA), no el promedio del área."
        ),
        "rango_amenaza": {
            c: [round(float(municipalities[c].min()), 4), round(float(municipalities[c].max()), 4)]
            for c in HAZARD_COLUMNS
        },
    }
    return municipalities, report


# -------------------------------------------------------------------- ejecución

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Integra catálogo, DIVIPOLA y amenaza sísmica.")
    parser.add_argument("--events", default="data/processed/eventos_santander_limpio.csv.gz")
    parser.add_argument("--divipola", default="data/raw/divipola_municipios_santander.csv")
    parser.add_argument("--hazard", default="data/raw/sgc_amenaza_2020_cabeceras.csv")
    parser.add_argument("--out", default="data/processed")
    args = parser.parse_args(argv)

    events = load_clean_events(args.events)
    municipalities, report = integrate(
        events, load_divipola(args.divipola), load_hazard(args.hazard)
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    municipalities.to_csv(out / "municipios_santander.csv", index=False, float_format="%.6f")
    with open(out / "integracion_reporte.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
