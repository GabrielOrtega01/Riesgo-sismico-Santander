"""Entorno de revisión de zonas.

Problema: cada año se presentan las zonas (municipios) una por una, en orden aleatorio, y el
agente decide si **priorizar** la zona (incluirla en la lista de revisión) o **saltarla**, con un
presupuesto limitado de K revisiones. La recompensa de priorizar es la utilidad realmente
observada de esa zona en el año siguiente (ver `reward.py`), menos el costo de revisión.

Estado (todo conocido al final del año t, sin información futura):
- categoría predicha por el clasificador para el año siguiente (Bajo/Medio/Alto)
- actividad reciente de la zona (3 niveles, año t)
- amenaza oficial (PGA, 3 niveles)
- exposición (población, 3 niveles)
- presupuesto restante (agrupado en 3 niveles) y mitad del episodio (2 niveles)
Acciones: 0 = saltar, 1 = priorizar.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.models.labels import CLASSES
from src.reinforcement_learning.reward import REVIEW_COST

N_ZONE_STATES = 3 * 3 * 3 * 3        # categoría × actividad × amenaza × exposición
N_QUARTERS = 4
SKIP, REVIEW = 0, 1


@dataclass
class Discretizer:
    """Cortes en 3 niveles ajustados con los años de entrenamiento."""
    activity_edges: tuple[float, float]
    hazard_edges: tuple[float, float]
    exposure_edges: tuple[float, float]

    @classmethod
    def fit(cls, train: pd.DataFrame) -> "Discretizer":
        def edges(s, qs):
            e = np.quantile(s.dropna(), qs)
            return float(e[0]), float(max(e[1], e[0] + 1e-9))
        return cls(
            activity_edges=edges(train["n_m25_año"], [0.55, 0.88]),
            hazard_edges=edges(train["pga_tr475"], [1 / 3, 2 / 3]),
            exposure_edges=edges(train["poblacion_log10"], [1 / 3, 2 / 3]),
        )

    def zone_states(self, df: pd.DataFrame) -> np.ndarray:
        cat = df["prediccion"].map({c: i for i, c in enumerate(CLASSES)}).to_numpy()
        act = np.digitize(df["n_m25_año"].fillna(0), [self.activity_edges[0] + 1e-9, self.activity_edges[1] + 1e-9])
        haz = np.digitize(df["pga_tr475"], self.hazard_edges)
        exp = np.digitize(df["poblacion_log10"], self.exposure_edges)
        return (((cat * 3 + act) * 3 + haz) * 3 + exp).astype(int)

    def to_dict(self) -> dict:
        return {"activity_edges": list(self.activity_edges), "hazard_edges": list(self.hazard_edges),
                "exposure_edges": list(self.exposure_edges)}

    @classmethod
    def from_dict(cls, d: dict) -> "Discretizer":
        return cls(tuple(d["activity_edges"]), tuple(d["hazard_edges"]), tuple(d["exposure_edges"]))


N_BUDGET_BUCKETS = 3     # 0 = sin presupuesto, 1 = quedan 1–3, 2 = quedan 4 o más
N_TIME_BUCKETS = 2       # primera / segunda mitad del episodio


def budget_bucket(left: int) -> int:
    return 0 if left <= 0 else (1 if left <= 3 else 2)


def n_states(budget: int) -> int:
    """Tamaño del espacio de estados (el presupuesto y el tiempo se agrupan para aprender rápido)."""
    return N_ZONE_STATES * N_BUDGET_BUCKETS * N_TIME_BUCKETS


def encode(zone_state: int, budget_left: int, quarter: int, budget: int) -> int:
    half = 1 if quarter >= N_QUARTERS // 2 else 0
    return (int(zone_state) * N_BUDGET_BUCKETS + budget_bucket(budget_left)) * N_TIME_BUCKETS + half


class ReviewEnv:
    """Un episodio = un año; las zonas llegan en orden aleatorio."""

    def __init__(self, zone_states: dict[int, np.ndarray], utilities: dict[int, np.ndarray],
                 budget: int = 10, cost: float = REVIEW_COST):
        self.zone_states, self.utilities = zone_states, utilities
        self.budget, self.cost = budget, cost
        self.n_states = n_states(budget)

    @property
    def years(self) -> list[int]:
        return sorted(self.zone_states)

    def reset(self, year: int, rng: np.random.Generator) -> int:
        self.year = year
        self.n = len(self.zone_states[year])
        self.order = rng.permutation(self.n)
        self.i, self.left = 0, self.budget
        self.captured = 0.0
        return self._obs()

    def _obs(self) -> int:
        zone = self.order[self.i]
        quarter = min(N_QUARTERS - 1, (N_QUARTERS * self.i) // self.n)
        return encode(self.zone_states[self.year][zone], self.left, quarter, self.budget)

    def valid_actions(self) -> list[int]:
        return [SKIP] if self.left == 0 else [SKIP, REVIEW]

    def step(self, action: int) -> tuple[int | None, float, bool]:
        reward = 0.0
        if action == REVIEW and self.left > 0:
            u = float(self.utilities[self.year][self.order[self.i]])
            reward = u - self.cost
            self.captured += u
            self.left -= 1
        self.i += 1
        done = self.i >= self.n
        return (None if done else self._obs()), reward, done
