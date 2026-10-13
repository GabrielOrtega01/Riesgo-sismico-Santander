"""Etiquetas de actividad sísmica (Bajo / Medio / Alto) para el año siguiente.

Metodología (clasificación exploratoria propia del proyecto, no una categoría oficial):
- La etiqueta de la fila (municipio, año t) describe la actividad del año **t+1**.
- Actividad = conteo de sismos M ≥ 2,5 del año t+1, con un **ajuste por intensidad**: si el
  sismo más fuerte del año t+1 es excepcional, la categoría sube un nivel.
- Los umbrales se ajustan **solo con los años de entrenamiento** (cuantiles del conteo y de la
  magnitud máxima) y luego se congelan para validación y prueba.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

CLASSES = ["Bajo", "Medio", "Alto"]
_ORDER = {c: i for i, c in enumerate(CLASSES)}

Q_LOW, Q_HIGH, Q_STRONG = 0.60, 0.87, 0.95


@dataclass(frozen=True)
class ActivityThresholds:
    count_low: float        # conteo <= count_low  -> Bajo
    count_high: float       # conteo <= count_high -> Medio; mayor -> Alto
    strong_magnitude: float # magnitud máxima >= esto -> sube un nivel

    def as_dict(self) -> dict:
        return asdict(self)


def fit_thresholds(counts, max_magnitudes, q_low=Q_LOW, q_high=Q_HIGH, q_strong=Q_STRONG) -> ActivityThresholds:
    """Ajusta los umbrales con datos de entrenamiento (nunca con validación ni prueba)."""
    c = np.asarray(counts, dtype=float)
    c = c[np.isfinite(c)]
    m = np.asarray(max_magnitudes, dtype=float)
    m = m[np.isfinite(m)]
    if c.size == 0 or m.size == 0:
        raise ValueError("No hay datos para ajustar los umbrales")
    low = float(np.quantile(c, q_low))
    high = max(float(np.quantile(c, q_high)), low + 1.0)   # evita clases vacías por empates
    return ActivityThresholds(low, high, float(np.quantile(m, q_strong)))


def classify_activity(counts, max_magnitudes, th: ActivityThresholds) -> np.ndarray:
    """Categoría de actividad a partir del conteo y la magnitud máxima de un año."""
    c = np.asarray(counts, dtype=float)
    m = np.asarray(max_magnitudes, dtype=float)
    level = np.where(c <= th.count_low, 0, np.where(c <= th.count_high, 1, 2))
    strong = np.nan_to_num(m, nan=-np.inf) >= th.strong_magnitude
    level = np.minimum(level + strong.astype(int), 2)
    return np.array(CLASSES, dtype=object)[level]


def add_targets(panel: pd.DataFrame, th: ActivityThresholds) -> pd.DataFrame:
    """Agrega `actividad_actual` (año t) y `etiqueta` (año t+1) al panel.

    La etiqueta queda vacía cuando el año t+1 no existe en el panel (último año).
    """
    out = panel.sort_values(["cod_mpio", "anio"]).copy()
    grp = out.groupby("cod_mpio", sort=False)
    out["conteo_siguiente"] = grp["n_m25_anio"].shift(-1)
    out["magnitud_max_siguiente"] = grp["magnitud_max_anio"].shift(-1)
    out["actividad_actual"] = classify_activity(out["n_m25_anio"], out["magnitud_max_anio"], th)
    nxt = classify_activity(out["conteo_siguiente"], out["magnitud_max_siguiente"], th)
    out["etiqueta"] = np.where(out["conteo_siguiente"].isna(), None, nxt)
    return out.reset_index(drop=True)


def class_index(labels) -> np.ndarray:
    return np.array([_ORDER[x] for x in labels])
