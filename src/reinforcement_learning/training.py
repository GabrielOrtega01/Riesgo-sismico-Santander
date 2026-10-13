"""Entrenamiento y evaluación del agente de priorización.

Protocolo temporal (el agente nunca ve el futuro de los años que evalúa):
- Entrenamiento: años t = 2012–2020    (recompensas con eventos de t+1 ≤ 2021)
- Validación:    años t = 2021–2022    (curva de aprendizaje)
- Prueba:        años t = 2023–2024    (evaluación final, una sola vez)

Los estados usan las probabilidades del clasificador **fuera de muestra** (origen móvil).

    python -m src.reinforcement_learning.training
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.patterns.strategies import (
    AgentStrategy, ClassifierOnlyStrategy, HistoryStrategy, PersistenceStrategy, RandomStrategy,
    rank_order,
)
from src.reinforcement_learning.agent import QLearningAgent
from src.reinforcement_learning.environment import REVIEW, SKIP, Discretizer, ReviewEnv
from src.reinforcement_learning.reward import REVIEW_COST, zone_utilities

TRAIN_YEARS = list(range(2012, 2021))
VAL_YEARS = [2021, 2022]
TEST_YEARS = [2023, 2024]
BUDGET = 10
EPISODES = 12000
SEED = 7
POLICY_PATH = Path("models/politica_q.npz")


def build_dataset(panel: pd.DataFrame, preds: pd.DataFrame) -> pd.DataFrame:
    """Filas (zona, año t) con predicción del clasificador y el resultado observado de t+1."""
    p = panel.sort_values(["cod_mpio", "año"]).copy()
    p["conteo_siguiente"] = p.groupby("cod_mpio")["n_m25_año"].shift(-1)
    p["poblacion"] = 10 ** p["poblacion_log10"]
    d = p.merge(preds[["cod_mpio", "año", "p_Bajo", "p_Medio", "p_Alto", "prediccion"]],
                on=["cod_mpio", "año"], how="inner", validate="one_to_one")
    d = d.sort_values(["año", "cod_mpio"]).reset_index(drop=True)
    util = np.full(len(d), np.nan)
    share = np.full(len(d), np.nan)
    for year, idx in d.groupby("año").groups.items():
        sub = d.loc[idx]
        if sub["conteo_siguiente"].notna().all():
            util[idx] = zone_utilities(sub["conteo_siguiente"], sub["poblacion"])
            tot = sub["conteo_siguiente"].sum()
            share[idx] = (sub["conteo_siguiente"] / tot).to_numpy() if tot > 0 else 0.0
    d["utilidad"], d["parte_eventos"] = util, share
    return d


def evaluate_ranking(zones: pd.DataFrame, scores: np.ndarray, k: int) -> dict:
    order = rank_order(scores, zones["p_Alto"].to_numpy())
    top = order[:k]
    return {"utilidad": float(zones["utilidad"].to_numpy()[top].sum()),
            "cobertura_eventos": float(zones["parte_eventos"].to_numpy()[top].sum())}


def evaluate_strategy(data: pd.DataFrame, years: list[int], strategy, k: int, repeats: int = 1) -> dict:
    util, cov = [], []
    for y in years:
        zones = data[data["año"] == y].reset_index(drop=True)
        rs = [evaluate_ranking(zones, strategy.scores(zones), k) for _ in range(repeats)]
        util.append(np.mean([r["utilidad"] for r in rs]))
        cov.append(np.mean([r["cobertura_eventos"] for r in rs]))
    return {"utilidad_media": round(float(np.mean(util)), 4),
            "cobertura_eventos_media": round(float(np.mean(cov)), 4),
            "por_año": {int(y): round(float(u), 4) for y, u in zip(years, util)}}


def online_evaluation(env: ReviewEnv, agent: QLearningAgent, years: list[int], orders: int = 300,
                      seed: int = 123) -> dict:
    """Protocolo secuencial (el de entrenamiento): utilidad capturada con presupuesto K.

    Compara la política aprendida (voraz) con políticas que no aprenden:
    aleatoria, primeras K zonas, y dos reglas fijas sobre el estado de la zona.
    """
    def decode(zone_state: int) -> tuple[int, int]:      # (categoría predicha, nivel de actividad)
        return zone_state // 27, (zone_state // 9) % 3

    policies = {
        "Agente de refuerzo (política aprendida)": "agent",
        "Aleatoria (acciones válidas al azar)": "random",
        "Primeras K zonas presentadas": "first",
        "Regla fija: categoría predicha ≥ Medio": "rule_cat",
        "Regla fija: actividad del año alta": "rule_act",
    }
    out = {}
    for name, kind in policies.items():
        rng = np.random.default_rng(seed)
        totals = []
        for y in years:
            for _ in range(orders):
                s = env.reset(y, rng)
                done = False
                while not done:
                    valid = env.valid_actions()
                    zone = env.zone_states[y][env.order[env.i]]
                    cat, act = decode(zone)
                    if len(valid) == 1:
                        a = SKIP
                    elif kind == "agent":
                        a = int(valid[int(np.argmax(agent.Q[s, valid]))])
                    elif kind == "random":
                        a = int(rng.choice(valid))
                    elif kind == "first":
                        a = REVIEW
                    elif kind == "rule_cat":
                        a = REVIEW if cat >= 1 else SKIP
                    else:
                        a = REVIEW if act >= 2 else SKIP
                    s, _, done = env.step(a)
                totals.append(env.captured)
        out[name] = round(float(np.mean(totals)), 4)
    return out


def oracle_utility(data: pd.DataFrame, years: list[int], k: int) -> float:
    return round(float(np.mean([
        np.sort(data.loc[data["año"] == y, "utilidad"].to_numpy())[::-1][:k].sum() for y in years])), 4)


def run(panel: pd.DataFrame, preds: pd.DataFrame, episodes: int = EPISODES, budget: int = BUDGET,
        seed: int = SEED) -> dict:
    data = build_dataset(panel, preds)
    labeled = data[data["utilidad"].notna()]
    disc = Discretizer.fit(labeled[labeled["año"].isin(TRAIN_YEARS)])

    years = sorted(labeled["año"].unique())
    zone_states = {y: disc.zone_states(labeled[labeled["año"] == y]) for y in years}
    utilities = {y: labeled.loc[labeled["año"] == y, "utilidad"].to_numpy() for y in years}
    env = ReviewEnv(zone_states, utilities, budget=budget, cost=REVIEW_COST)

    agent = QLearningAgent(env.n_states, seed=seed)
    curve = []

    def observe(rec: dict) -> None:       # Observer: registra la curva de aprendizaje
        ev = evaluate_strategy(labeled, VAL_YEARS, AgentStrategy(agent, disc, budget), budget)
        rec["val_utilidad_top_k"] = ev["utilidad_media"]
        curve.append(rec)

    # punto de partida (política sin entrenar)
    base = evaluate_strategy(labeled, VAL_YEARS, AgentStrategy(agent, disc, budget), budget)
    agent.train(env, TRAIN_YEARS, episodes=episodes, observers=[observe], log_every=500)

    strategies = [AgentStrategy(agent, disc, budget), PersistenceStrategy(), HistoryStrategy(),
                  ClassifierOnlyStrategy()]
    table = {}
    for split, ys in (("validacion", VAL_YEARS), ("prueba", TEST_YEARS), ("validacion_y_prueba", VAL_YEARS + TEST_YEARS)):
        table[split] = {s.name: evaluate_strategy(labeled, ys, s, budget) for s in strategies}
        table[split][RandomStrategy.name] = evaluate_strategy(labeled, ys, RandomStrategy(seed), budget, repeats=500)
        table[split]["Óptimo (conoce el futuro; cota superior)"] = {"utilidad_media": oracle_utility(labeled, ys, budget)}

    online = {
        "validacion": online_evaluation(env, agent, VAL_YEARS),
        "prueba": online_evaluation(env, agent, TEST_YEARS),
    }
    untrained = online_evaluation(env, QLearningAgent(env.n_states, seed=seed), VAL_YEARS, orders=100)
    visited = int((np.abs(agent.Q).sum(axis=1) > 0).sum())
    results = {
        "configuracion": {"presupuesto_K": budget, "episodios": episodes, "alpha": agent.alpha,
                          "gamma": agent.gamma, "epsilon_inicial": agent.eps_start,
                          "costo_revision": REVIEW_COST, "semilla": seed,
                          "años_entrenamiento": [TRAIN_YEARS[0], TRAIN_YEARS[-1]],
                          "años_validacion": VAL_YEARS, "años_prueba": TEST_YEARS,
                          "estados_totales": int(env.n_states), "estados_visitados": visited},
        "discretizador": disc.to_dict(),
        "utilidad_validacion_sin_entrenar": base["utilidad_media"],
        "curva_de_aprendizaje": curve,
        "evaluacion": table,
        "evaluacion_en_linea": online,
        "agente_sin_entrenar_en_linea_validacion": untrained["Agente de refuerzo (política aprendida)"],
    }
    return {"results": results, "agent": agent, "disc": disc, "data": data, "budget": budget}


def save(bundle: dict, out_dir: str | Path = "data/processed") -> None:
    out = Path(out_dir)
    bundle["agent"].save(POLICY_PATH, bundle["disc"], bundle["budget"],
                         meta={"años_entrenamiento": [TRAIN_YEARS[0], TRAIN_YEARS[-1]]})
    with open(out / "agente_resultados.json", "w", encoding="utf-8") as fh:
        json.dump(bundle["results"], fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def main() -> None:
    panel = pd.read_csv("data/processed/panel_municipio_anio.csv", dtype={"cod_mpio": str})
    preds = pd.read_csv("data/processed/predicciones_clasificador.csv", dtype={"cod_mpio": str})
    bundle = run(panel, preds)
    save(bundle)
    r = bundle["results"]
    print("Config:", r["configuracion"])
    print("Utilidad validación sin entrenar:", r["utilidad_validacion_sin_entrenar"])
    for rec in r["curva_de_aprendizaje"]:
        print(f"  ep {rec['episodio']:>5}  eps={rec['epsilon']:.3f}  recompensa_media={rec['recompensa_media']:+.4f}  val_util@K={rec['val_utilidad_top_k']:.4f}")
    print("== EN LÍNEA (protocolo secuencial, utilidad capturada con presupuesto K) ==")
    print("  agente sin entrenar (validación):", r["agente_sin_entrenar_en_linea_validacion"])
    for split, vals in r["evaluacion_en_linea"].items():
        for name, v in vals.items():
            print(f"  {split:11s} {name:48s} {v:.4f}")
    for split in ("validacion", "prueba", "validacion_y_prueba"):
        print(f"== {split} (utilidad media @K={BUDGET}; cobertura de eventos) ==")
        for name, v in r["evaluacion"][split].items():
            print(f"  {name:48s} util={v['utilidad_media']:.4f}  cob={v.get('cobertura_eventos_media', float('nan')):.4f}")


if __name__ == "__main__":
    main()
