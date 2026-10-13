"""Agente de aprendizaje por refuerzo: Q-learning tabular con política ε-voraz."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.reinforcement_learning.environment import (
    N_ZONE_STATES, REVIEW, SKIP, Discretizer, ReviewEnv, encode,
)


class QLearningAgent:
    def __init__(self, n_states: int, n_actions: int = 2, alpha: float = 0.1, gamma: float = 1.0,
                 eps_start: float = 0.5, eps_end: float = 0.02, eps_decay: float = 0.9995,
                 seed: int = 0):
        self.Q = np.zeros((n_states, n_actions))
        self.alpha, self.gamma = alpha, gamma
        self.eps_start, self.eps_end, self.eps_decay = eps_start, eps_end, eps_decay
        self.rng = np.random.default_rng(seed)

    def epsilon(self, episode: int) -> float:
        return max(self.eps_end, self.eps_start * self.eps_decay ** episode)

    def act(self, state: int, valid: list[int], epsilon: float) -> int:
        if len(valid) == 1:
            return valid[0]
        if self.rng.random() < epsilon:
            return int(self.rng.choice(valid))
        q = self.Q[state, valid]
        best = np.flatnonzero(q == q.max())
        return valid[int(self.rng.choice(best))]

    def update(self, s: int, a: int, r: float, s2: int | None, valid2: list[int]) -> None:
        target = r if s2 is None else r + self.gamma * self.Q[s2, valid2].max()
        self.Q[s, a] += self.alpha * (target - self.Q[s, a])

    # ---- entrenamiento -------------------------------------------------------------------
    def train(self, env: ReviewEnv, years: list[int], episodes: int, observers=(), log_every: int = 250) -> list[dict]:
        """Ejecuta episodios; `observers` son funciones que reciben un dict por registro (Observer)."""
        history, window = [], []
        for ep in range(episodes):
            year = int(self.rng.choice(years))
            s = env.reset(year, self.rng)
            eps, total, done = self.epsilon(ep), 0.0, False
            while not done:
                valid = env.valid_actions()
                a = self.act(s, valid, eps)
                s2, r, done = env.step(a)
                self.update(s, a, r, s2, env.valid_actions() if not done else [SKIP])
                total += r
                s = s2
            window.append(total)
            if (ep + 1) % log_every == 0:
                rec = {"episodio": ep + 1, "epsilon": round(eps, 4),
                       "recompensa_media": round(float(np.mean(window)), 5)}
                history.append(rec)
                window = []
                for ob in observers:
                    ob(rec)
        return history

    # ---- política y priorización ---------------------------------------------------------
    def priority_scores(self, zone_states: np.ndarray, budget: int) -> np.ndarray:
        """Ventaja de priorizar cada zona al inicio del episodio con presupuesto completo."""
        idx = np.array([encode(z, budget, 0, budget) for z in zone_states])
        return self.Q[idx, REVIEW] - self.Q[idx, SKIP]

    # ---- persistencia -------------------------------------------------------------------
    def save(self, path: str | Path, discretizer: Discretizer, budget: int, meta: dict | None = None) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, Q=self.Q, budget=budget,
                 discretizer=json.dumps(discretizer.to_dict()), meta=json.dumps(meta or {}))

    @classmethod
    def load(cls, path: str | Path) -> tuple["QLearningAgent", Discretizer, int, dict]:
        data = np.load(path, allow_pickle=False)
        agent = cls(n_states=data["Q"].shape[0], n_actions=data["Q"].shape[1])
        agent.Q = data["Q"].copy()
        return (agent, Discretizer.from_dict(json.loads(str(data["discretizer"]))),
                int(data["budget"]), json.loads(str(data["meta"])))


assert N_ZONE_STATES == 81
