"""Pruebas con catálogos SINTÉTICOS generados con semilla fija (no son datos reales)."""
import numpy as np
import pandas as pd

from src.data.completeness import b_value_aki, mc_by_year, mc_maxc


def _synthetic_gr_catalog(n, mc_true, b=1.0, seed=0):
    """Magnitudes tipo Gutenberg-Richter completas por encima de mc_true, redondeadas a 0,1."""
    rng = np.random.default_rng(seed)
    beta = b * np.log(10)
    m = mc_true - 0.05 + rng.exponential(1 / beta, size=n)
    return np.round(m, 1)


def test_mc_maxc_recovers_known_completeness():
    m = _synthetic_gr_catalog(20000, mc_true=1.5, b=1.0, seed=1)
    # MAXC sin corrección apunta al contenedor modal ≈ mc_true; con +0,2 queda cerca de 1,7
    assert mc_maxc(m, correction=0.0) == 1.5
    assert abs(mc_maxc(m) - 1.7) < 1e-9


def test_b_value_close_to_truth():
    m = _synthetic_gr_catalog(50000, mc_true=1.5, b=1.0, seed=2)
    assert abs(b_value_aki(m, mc=1.5) - 1.0) < 0.05


def test_empty_and_degenerate_inputs_return_nan():
    assert np.isnan(mc_maxc([]))
    assert np.isnan(b_value_aki([2.0], mc=2.0))
    assert np.isnan(b_value_aki([1.0, 1.0], mc=3.0))


def test_mc_by_year_flags_small_samples_and_counts_above_mc():
    big = _synthetic_gr_catalog(3000, mc_true=2.0, seed=4)
    small = _synthetic_gr_catalog(50, mc_true=1.0, seed=5)
    times = pd.to_datetime(
        ["2010-06-01"] * len(big) + ["2011-06-01"] * len(small), utc=True
    )
    events = pd.DataFrame({"utc_time": times, "magnitude": np.concatenate([big, small])})
    table = mc_by_year(events, min_events=200).set_index("anio")

    assert table.loc[2010, "n_eventos"] == 3000
    assert abs(table.loc[2010, "mc_maxc"] - 2.2) < 1e-9
    assert table.loc[2010, "n_sobre_mc"] == int((big >= 2.2 - 1e-9).sum())
    assert np.isnan(table.loc[2011, "mc_maxc"])          # muestra insuficiente
