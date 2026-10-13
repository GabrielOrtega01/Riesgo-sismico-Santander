"""Acceso a los datos procesados y cálculo de indicadores descriptivos para la aplicación.

Todo lo que muestra la aplicación sale de aquí (o de los modelos entrenados cuando existan).
Los indicadores son **descriptivos del catálogo histórico**: no son categorías de riesgo ni
predicciones.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.data.loaders import load_clean_events

ROOT = Path(__file__).resolve().parents[2]
EVENTS_PATH = ROOT / "data" / "processed" / "eventos_santander_limpio.csv.gz"
MUNICIPALITIES_PATH = ROOT / "data" / "processed" / "municipios_santander.csv"
MC_PATH = ROOT / "data" / "processed" / "mc_por_anio.csv"
SOURCES_DOC_PATH = ROOT / "docs" / "fuentes_datos.md"

DEFAULT_MIN_MAGNITUDE = 2.5     # completo en todos los años (ver docs/fuentes_datos.md)
SHALLOW_KM = 30.0

MODEL_ARTIFACTS = {
    "Clasificador (Básico / Medio / Avanzado)": ROOT / "models" / "clasificador.joblib",
    "Política aprendida del agente (RL)": ROOT / "models" / "politica_q.npz",
}

_LOWER_WORDS = {"De", "Del", "La", "Las", "Los", "El"}


def pretty_name(name: str) -> str:
    """'SAN VICENTE DE CHUCURÍ' -> 'San Vicente de Chucurí' (el primer 'El' se conserva)."""
    words = str(name).title().split()
    return " ".join(
        w.lower() if (i > 0 and w in _LOWER_WORDS) else w for i, w in enumerate(words)
    )


# ------------------------------------------------------------------------ carga

def load_events(path: str | Path = EVENTS_PATH) -> pd.DataFrame:
    return load_clean_events(path)


def load_municipalities(path: str | Path = MUNICIPALITIES_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"cod_mpio": str})
    df["nombre"] = df["municipio_oficial"].map(pretty_name)
    return df.sort_values("nombre").reset_index(drop=True)


def load_mc_table(path: str | Path = MC_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def read_sources_doc(path: str | Path = SOURCES_DOC_PATH) -> str:
    return Path(path).read_text(encoding="utf-8")


# ------------------------------------------------------------------ indicadores

def catalog_summary(events: pd.DataFrame) -> dict:
    """Cifras globales del catálogo cargado."""
    return {
        "eventos": int(len(events)),
        "municipios": int(events["municipio_key"].nunique()),
        "inicio": events["utc_time"].min(),
        "fin": events["utc_time"].max(),
        "magnitud_max": float(events["magnitude"].max()),
        "profundidad_mediana": float(events["depth"].median()),
        "pct_profundos_100km": float((events["depth"] >= 100).mean() * 100),
    }


def yearly_indicators(
    events: pd.DataFrame,
    min_magnitude: float = DEFAULT_MIN_MAGNITUDE,
    shallow_km: float = SHALLOW_KM,
) -> pd.DataFrame:
    """Indicadores por municipio y año, con rejilla completa (años sin eventos = 0)."""
    df = events.assign(
        anio=events["utc_time"].dt.year,
        sobre_umbral=events["magnitude"] >= min_magnitude,
        superficial=events["depth"] < shallow_km,
    )
    agg = df.groupby(["municipio_key", "anio"]).agg(
        n_eventos=("id", "size"),
        n_sobre_umbral=("sobre_umbral", "sum"),
        magnitud_max=("magnitude", "max"),
        magnitud_media=("magnitude", "mean"),
        profundidad_mediana=("depth", "median"),
        pct_superficial=("superficial", "mean"),
    )
    agg["pct_superficial"] *= 100

    years = range(int(df["anio"].min()), int(df["anio"].max()) + 1)
    grid = pd.MultiIndex.from_product(
        [sorted(df["municipio_key"].dropna().unique()), years], names=["municipio_key", "anio"]
    )
    out = agg.reindex(grid)
    out[["n_eventos", "n_sobre_umbral"]] = out[["n_eventos", "n_sobre_umbral"]].fillna(0).astype(int)
    return out.reset_index()


def zone_summary(
    events: pd.DataFrame,
    municipality: pd.Series,
    min_magnitude: float = DEFAULT_MIN_MAGNITUDE,
) -> dict:
    """Resumen descriptivo de un municipio (fila de `load_municipalities`)."""
    ev = events[events["municipio_key"] == municipality["municipio_key"]]
    base = {
        "cod_mpio": municipality["cod_mpio"],
        "nombre": municipality["nombre"],
        "eventos": int(len(ev)),
        "pct_del_catalogo": float(len(ev) / len(events) * 100) if len(events) else 0.0,
        "eventos_sobre_umbral": int((ev["magnitude"] >= min_magnitude).sum()),
        "pga_tr475": float(municipality["pga_tr475"]),
        "pga_tr2475": float(municipality["pga_tr2475"]),
        "intensidad_esperada": float(municipality["intensidad_esperada"]),
    }
    if ev.empty:
        return {**base, "magnitud_max": None, "fecha_magnitud_max": None,
                "profundidad_mediana": None, "pct_superficial": None}
    top = ev.loc[ev["magnitude"].idxmax()]
    return {
        **base,
        "magnitud_max": float(top["magnitude"]),
        "fecha_magnitud_max": top["utc_time"],
        "profundidad_mediana": float(ev["depth"].median()),
        "pct_superficial": float((ev["depth"] < SHALLOW_KM).mean() * 100),
    }


def depth_histogram(events: pd.DataFrame, municipio_key: str, bin_km: int = 10) -> pd.DataFrame:
    """Número de eventos por rango de profundidad (km) de un municipio."""
    depth = events.loc[events["municipio_key"] == municipio_key, "depth"].clip(lower=0)
    if depth.empty:
        return pd.DataFrame({"rango_km": [], "eventos": []})
    top = int(np.ceil(depth.max() / bin_km) * bin_km) or bin_km
    edges = np.arange(0, top + bin_km, bin_km)
    counts, _ = np.histogram(depth, bins=edges)
    labels = [f"{int(a):03d}-{int(b):03d}" for a, b in zip(edges[:-1], edges[1:])]
    return pd.DataFrame({"rango_km": labels, "eventos": counts})


def compare_zones(yearly: pd.DataFrame, keys: list[str], metric: str) -> pd.DataFrame:
    """Tabla año × municipio de una métrica, lista para graficar."""
    sub = yearly[yearly["municipio_key"].isin(keys)]
    return sub.pivot(index="anio", columns="municipio_key", values=metric).sort_index()


def model_status() -> list[dict]:
    """Estado de los artefactos entrenados que alimentan la clasificación y la priorización."""
    return [
        {"componente": name, "archivo": str(path.relative_to(ROOT)), "disponible": path.is_file()}
        for name, path in MODEL_ARTIFACTS.items()
    ]
