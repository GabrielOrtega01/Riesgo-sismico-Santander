"""Facade: flujo completo clasificador → estados → agente → priorización.

Une los componentes entrenados con una interfaz simple para la aplicación:

    datos procesados (panel) → clasificador (categoría y probabilidades) → estados discretos →
    política aprendida (valor de priorizar) → lista de zonas prioritarias

Todo se calcula con artefactos guardados; no se reentrena en cada ejecución.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.models.classifier import load_classifier, predict_zone_year
from src.models.labels import CLASSES
from src.patterns.strategies import rank_order
from src.reinforcement_learning.agent import QLearningAgent

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
CLASSIFIER_PATH = ROOT / "models" / "clasificador.joblib"
POLICY_PATH = ROOT / "models" / "politica_q.npz"


class RiskAnalysisService:
    """Carga los artefactos una vez y responde consultas por año."""

    def __init__(self, processed: Path = PROCESSED, classifier_path: Path = CLASSIFIER_PATH,
                 policy_path: Path = POLICY_PATH):
        self.processed = Path(processed)
        self.panel = pd.read_csv(self.processed / "panel_municipio_anio.csv", dtype={"cod_mpio": str})
        self.classifier = load_classifier(classifier_path)
        self.agent, self.discretizer, self.budget, self.policy_meta = QLearningAgent.load(policy_path)
        self.groups = pd.read_csv(self.processed / "grupos_territoriales.csv", dtype={"cod_mpio": str})

    # ---- consultas ---------------------------------------------------------------------------
    @property
    def years(self) -> list[int]:
        usable = self.panel[self.panel["anios_historia"] >= 3]
        return sorted(int(y) for y in usable["anio"].unique())

    def _rows(self, year: int) -> pd.DataFrame:
        rows = self.panel[self.panel["anio"] == year]
        if rows.empty:
            raise ValueError(f"El año {year} no está en el panel")
        return rows.reset_index(drop=True)

    def classify(self, year: int) -> pd.DataFrame:
        """Contrato del clasificador: zona, categoría y probabilidades (para el año siguiente)."""
        out = predict_zone_year(self.classifier, self._rows(year))
        return out.sort_values("p_Alto", ascending=False).reset_index(drop=True)

    def prioritize(self, year: int, k: int | None = None) -> pd.DataFrame:
        """Zonas ordenadas por prioridad según el agente (desempate: probabilidad de «Alto»)."""
        k = self.budget if k is None else k
        rows = self._rows(year)
        cls = predict_zone_year(self.classifier, rows)
        data = rows.merge(
            cls.rename(columns={"categoria": "prediccion"})[["cod_mpio", "p_Bajo", "p_Medio", "p_Alto", "prediccion"]],
            on="cod_mpio", validate="one_to_one",
        )
        states = self.discretizer.zone_states(data)
        scores = self.agent.priority_scores(states, self.budget)
        order = rank_order(scores, data["p_Alto"].to_numpy())
        out = data.iloc[order].reset_index(drop=True)
        out["prioridad"] = np.arange(1, len(out) + 1)
        out["puntaje_agente"] = scores[order]
        out["seleccionada"] = out["prioridad"] <= k
        out = out.merge(self.groups[["cod_mpio", "grupo"]], on="cod_mpio", how="left")
        return out[["prioridad", "seleccionada", "municipio", "cod_mpio", "prediccion", "p_Alto", "p_Medio",
                    "p_Bajo", "puntaje_agente", "n_m25_anio", "pga_tr475", "poblacion_log10", "grupo"]]

    # ---- métricas guardadas ---------------------------------------------------------------------
    def _json(self, name: str) -> dict:
        path = self.processed / name
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def classifier_metrics(self) -> dict:
        return self._json("clasificador_metricas.json")

    def agent_results(self) -> dict:
        return self._json("agente_resultados.json")

    def group_metrics(self) -> dict:
        return self._json("grupos_metricas.json")

    def group_profiles(self) -> pd.DataFrame:
        return pd.read_csv(self.processed / "grupos_perfil_medio.csv", index_col=0)


__all__ = ["RiskAnalysisService", "CLASSES"]
