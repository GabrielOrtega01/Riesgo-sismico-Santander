"""Función de recompensa de la priorización.

Utilidad de revisar una zona = qué parte de la actividad sísmica del año siguiente y de la
exposición afectada se «captura» al incluirla en la lista de revisión:

    utilidad_i = 0,5 · e_i / Σ_j e_j  +  0,5 · (e_i · p_i) / Σ_j (e_j · p_j)

con e_i = sismos M ≥ 2,5 del año t+1 en la zona i y p_i = población de la zona en el año t.
Recompensa neta = utilidad − COSTO_REVISION (cada revisión consume recursos).

Supuestos y sesgos:
- Mide utilidad de priorizar según actividad **observada** (no es una predicción de daños).
- Pondera la exposición con la población total: no considera vulnerabilidad de las construcciones.
- Una zona con muchos sismos pero pocos habitantes vale menos que una con ambas cosas.
- La actividad está muy concentrada (Los Santos): la recompensa lo refleja y puede dominar.
"""
from __future__ import annotations

import numpy as np

REVIEW_COST = 0.01
W_ACTIVITY, W_EXPOSURE = 0.5, 0.5


def zone_utilities(next_counts, population) -> np.ndarray:
    """Utilidad (suma 1 sobre las zonas del año; 0 si no hubo actividad)."""
    e = np.nan_to_num(np.asarray(next_counts, dtype=float), nan=0.0)
    p = np.asarray(population, dtype=float)
    act = e / e.sum() if e.sum() > 0 else np.zeros_like(e)
    w = e * p
    exp = w / w.sum() if w.sum() > 0 else np.zeros_like(e)
    return W_ACTIVITY * act + W_EXPOSURE * exp


def net_reward(utility: float, cost: float = REVIEW_COST) -> float:
    return float(utility - cost)
