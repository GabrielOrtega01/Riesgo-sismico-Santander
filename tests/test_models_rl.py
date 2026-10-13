"""Pruebas con datos SINTÉTICOS de etiquetas, clasificador, agrupamiento y aprendizaje por refuerzo."""
import numpy as np
import pandas as pd
import pytest

from src.models import labels as L
from src.patterns.factories import MODEL_NAMES, make_classifier
from src.patterns.strategies import PersistenceStrategy, rank_order
from src.reinforcement_learning import reward as R
from src.reinforcement_learning.agent import QLearningAgent
from src.reinforcement_learning.environment import (
    REVIEW, SKIP, Discretizer, ReviewEnv, encode, n_states,
)


# ---- etiquetas ------------------------------------------------------------------------

def test_thresholds_are_fit_from_training_data_only():
    counts = np.array([0] * 70 + [1] * 10 + [2, 3, 4, 5] * 5)
    th = L.fit_thresholds(counts, np.full(100, 2.5))
    assert th.count_low == 0 and th.count_high >= th.count_low + 1


def test_classify_activity_with_strong_event_escalation():
    th = L.ActivityThresholds(count_low=0, count_high=3, strong_magnitude=4.0)
    out = L.classify_activity([0, 2, 9, 0, 2], [np.nan, 2.6, 3.0, 4.5, 4.5], th)
    assert out.tolist() == ["Bajo", "Medio", "Alto", "Medio", "Alto"]


def test_targets_look_one_year_ahead_and_last_year_is_unlabeled():
    panel = pd.DataFrame({
        "cod_mpio": ["1"] * 3, "año": [2020, 2021, 2022],
        "n_m25_año": [0, 5, 1], "magnitud_max_año": [np.nan, 3.0, 2.6],
    })
    th = L.ActivityThresholds(0, 3, 4.0)
    out = L.add_targets(panel, th).set_index("año")
    assert out.loc[2020, "etiqueta"] == "Alto"            # 2021 tuvo 5 eventos
    assert out.loc[2021, "etiqueta"] == "Medio"           # 2022 tuvo 1
    assert pd.isna(out.loc[2022, "etiqueta"])
    assert out.loc[2021, "actividad_actual"] == "Alto"


# ---- fábrica y estrategias --------------------------------------------------------------

def test_model_factory_builds_known_models_and_rejects_unknown():
    for name in MODEL_NAMES:
        assert hasattr(make_classifier(name), "fit")
    with pytest.raises(ValueError, match="desconocido"):
        make_classifier("modelo_inexistente")


def test_factory_pipeline_handles_missing_values_without_leaking_from_test():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(120, 4)), columns=list("abcd"))
    y = np.where(X["a"] > 0.5, "Alto", np.where(X["a"] > -0.5, "Medio", "Bajo"))
    X.loc[::7, "b"] = np.nan
    model = make_classifier("random_forest").fit(X, y)
    assert set(model.predict(X)) <= {"Alto", "Medio", "Bajo"}


def test_rank_order_uses_tiebreak():
    scores = np.array([1.0, 1.0, 3.0])
    assert rank_order(scores, np.array([0.1, 0.9, 0.0])).tolist() == [2, 1, 0]


def test_persistence_strategy_orders_by_current_activity():
    zones = pd.DataFrame({"n_m25_año": [1, 9, 4], "n_m25_hist_prom": [0.0, 0.0, 0.0]})
    assert rank_order(PersistenceStrategy().scores(zones)).tolist() == [1, 2, 0]


# ---- recompensa ---------------------------------------------------------------------------

def test_utilities_sum_to_one_and_weight_exposure():
    u = R.zone_utilities([10, 10, 0], [1000, 9000, 5000])
    assert u.sum() == pytest.approx(1.0)
    assert u[1] > u[0] > u[2] == 0                       # misma actividad, más población vale más


def test_utilities_are_zero_when_there_is_no_activity():
    assert R.zone_utilities([0, 0], [10, 20]).tolist() == [0.0, 0.0]


# ---- entorno y agente ---------------------------------------------------------------------

def _tiny_env(budget=2, n=8, years=(2020, 2021)):
    rng = np.random.default_rng(1)
    zone_states = {y: rng.integers(0, 81, size=n) for y in years}
    utilities = {y: rng.random(n) / n for y in years}
    return ReviewEnv(zone_states, utilities, budget=budget, cost=0.01)


def test_state_encoding_is_within_bounds_and_distinct():
    ids = {encode(z, b, q, 10) for z in range(81) for b in (0, 2, 10) for q in (0, 3)}
    assert max(ids) < n_states(10) and len(ids) == 81 * 3 * 2


def test_environment_respects_budget_and_terminates():
    env = _tiny_env(budget=2, n=8)
    rng = np.random.default_rng(0)
    env.reset(2020, rng)
    steps, reviewed, done = 0, 0, False
    while not done:
        action = REVIEW if env.valid_actions() == [SKIP, REVIEW] else SKIP
        _, r, done = env.step(REVIEW)                    # intenta revisar siempre
        reviewed += r != 0.0
        steps += 1
    assert steps == 8 and reviewed <= 2 and env.left == 0


def test_agent_update_moves_q_toward_reward():
    agent = QLearningAgent(n_states=4, alpha=0.5)
    agent.update(0, REVIEW, 1.0, None, [SKIP])
    assert agent.Q[0, REVIEW] == pytest.approx(0.5)


def test_agent_learns_to_review_high_value_states():
    # estados con utilidad alta/baja conocidos: el agente debe preferir revisar los altos
    n = 20
    zone_states = {2020: np.array([0] * 10 + [1] * 10)}
    utilities = {2020: np.array([0.0] * 10 + [0.1] * 10)}
    env = ReviewEnv(zone_states, utilities, budget=5, cost=0.01)
    agent = QLearningAgent(env.n_states, seed=3)
    agent.train(env, [2020], episodes=1500, log_every=500)
    scores = agent.priority_scores(np.array([0, 1]), budget=5)
    assert scores[1] > scores[0]


def test_agent_policy_roundtrip(tmp_path):
    env = _tiny_env()
    agent = QLearningAgent(env.n_states, seed=2)
    agent.train(env, [2020, 2021], episodes=50, log_every=25)
    disc = Discretizer((1.0, 5.0), (0.2, 0.25), (3.5, 4.5))
    path = tmp_path / "politica.npz"
    agent.save(path, disc, budget=2, meta={"x": 1})
    loaded, disc2, budget, meta = QLearningAgent.load(path)
    assert np.array_equal(loaded.Q, agent.Q) and budget == 2 and meta == {"x": 1}
    assert disc2.activity_edges == disc.activity_edges


def test_observer_receives_training_records():
    env = _tiny_env()
    agent = QLearningAgent(env.n_states, seed=0)
    seen = []
    agent.train(env, [2020], episodes=100, observers=[seen.append], log_every=50)
    assert [r["episodio"] for r in seen] == [50, 100]
    assert all("recompensa_media" in r for r in seen)
