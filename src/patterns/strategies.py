"""Strategy: estrategias intercambiables de priorización de zonas.

Resuelve: comparar al agente aprendido con estrategias de referencia sin cambiar el código de
evaluación. Cada estrategia recibe la tabla de zonas de un año y devuelve una puntuación
(mayor = más prioritaria). Usado en `src/reinforcement_learning/training.py` y en el servicio
`src/services/risk_analysis.py`.
"""
from __future__ import annotations

from typing import Protocol

import numpy as np
import pandas as pd


class PrioritizationStrategy(Protocol):
    name: str

    def scores(self, zones: pd.DataFrame) -> np.ndarray: ...


class PersistenceStrategy:
    """Prioriza las zonas con más sismos M ≥ 2,5 en el año actual."""
    name = "Persistencia (actividad del año)"

    def scores(self, zones: pd.DataFrame) -> np.ndarray:
        return zones["n_m25_año"].to_numpy(dtype=float) + 1e-6 * zones["n_m25_hist_prom"].fillna(0).to_numpy()


class HistoryStrategy:
    """Prioriza las zonas con mayor promedio histórico de sismos M ≥ 2,5."""
    name = "Historia (promedio anual previo)"

    def scores(self, zones: pd.DataFrame) -> np.ndarray:
        return zones["n_m25_hist_prom"].fillna(0).to_numpy(dtype=float)


class ClassifierOnlyStrategy:
    """Prioriza según la categoría esperada por el clasificador (sin agente)."""
    name = "Solo clasificador (categoría esperada)"

    def scores(self, zones: pd.DataFrame) -> np.ndarray:
        return (zones["p_Medio"] + 2 * zones["p_Alto"]).to_numpy(dtype=float)


class RandomStrategy:
    """Orden aleatorio (referencia mínima). Se evalúa en esperanza con muchas permutaciones."""
    name = "Aleatoria"

    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)

    def scores(self, zones: pd.DataFrame) -> np.ndarray:
        return self.rng.random(len(zones))


class AgentStrategy:
    """Prioriza con el valor aprendido por el agente de refuerzo (desempate: p(Alto))."""
    name = "Agente de refuerzo (Q-learning)"

    def __init__(self, agent, discretizer, budget: int):
        self.agent, self.disc, self.budget = agent, discretizer, budget

    def scores(self, zones: pd.DataFrame) -> np.ndarray:
        return self.agent.priority_scores(self.disc.zone_states(zones), self.budget)


def rank_order(scores: np.ndarray, tiebreak: np.ndarray | None = None) -> np.ndarray:
    """Índices ordenados de mayor a menor puntuación; los empates se resuelven con `tiebreak`."""
    tb = np.zeros_like(scores) if tiebreak is None else tiebreak
    return np.lexsort((-tb, -scores))
