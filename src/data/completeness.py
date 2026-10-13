"""Magnitud de completitud (Mc) del catálogo.

Un catálogo sísmico solo es completo por encima de cierta magnitud (Mc); por debajo, los
eventos pequeños se detectan de forma desigual según la red de estaciones. Si no se corrige,
las variables de frecuencia reflejan la evolución de la red y no la sismicidad.

Método: máxima curvatura (MAXC) con la corrección habitual de +0,2 (Woessner y Wiemer, 2005)
y valor b de Aki-Utsu con corrección por discretización. Son estimaciones rápidas y
conocidas; MAXC tiende a subestimar Mc, por eso se informa junto al conteo por encima de Mc.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BIN_WIDTH = 0.1
MAXC_CORRECTION = 0.2
MIN_EVENTS = 200


def mc_maxc(magnitudes, bin_width: float = BIN_WIDTH, correction: float = MAXC_CORRECTION) -> float:
    """Mc por máxima curvatura: el contenedor de magnitud más poblado (+ corrección)."""
    m = np.asarray(magnitudes, dtype="float64")
    m = m[np.isfinite(m)]
    if m.size == 0:
        return float("nan")
    bins = np.round(m / bin_width).astype(int)
    values, counts = np.unique(bins, return_counts=True)
    return float(values[np.argmax(counts)] * bin_width + correction)


def b_value_aki(magnitudes, mc: float, bin_width: float = BIN_WIDTH) -> float:
    """Valor b de Gutenberg-Richter (Aki-Utsu) para los eventos con M >= Mc."""
    m = np.asarray(magnitudes, dtype="float64")
    m = m[np.isfinite(m) & (m >= mc - 1e-9)]
    if m.size < 2:
        return float("nan")
    denom = m.mean() - (mc - bin_width / 2.0)
    if denom <= 0:
        return float("nan")
    return float(np.log10(np.e) / denom)


def mc_by_year(
    events: pd.DataFrame,
    time_col: str = "utc_time",
    mag_col: str = "magnitude",
    min_events: int = MIN_EVENTS,
) -> pd.DataFrame:
    """Tabla anual: n de eventos, Mc (MAXC), eventos con M>=Mc y valor b.

    Los años con menos de `min_events` eventos devuelven Mc nulo (muestra insuficiente).
    """
    years = events[time_col].dt.year
    rows = []
    for year, group in events.groupby(years):
        m = group[mag_col].to_numpy()
        enough = len(m) >= min_events
        mc = mc_maxc(m) if enough else float("nan")
        rows.append({
            "anio": int(year),
            "n_eventos": int(len(m)),
            "mc_maxc": mc,
            "n_sobre_mc": int((m >= mc - 1e-9).sum()) if enough else np.nan,
            "valor_b": b_value_aki(m, mc) if enough else float("nan"),
        })
    return pd.DataFrame(rows)


def main() -> None:
    """Escribe data/processed/mc_por_anio.csv a partir de los eventos limpios."""
    from src.data.loaders import load_clean_events

    events = load_clean_events("data/processed/eventos_santander_limpio.csv.gz")
    table = mc_by_year(events)
    table.to_csv("data/processed/mc_por_anio.csv", index=False, float_format="%.3f")
    mc_all = mc_maxc(events["magnitude"])
    print(table.round(2).to_string(index=False))
    print(f"\nMc global (MAXC+0.2): {mc_all:.1f}  b: {b_value_aki(events['magnitude'], mc_all):.2f}")


if __name__ == "__main__":
    main()
