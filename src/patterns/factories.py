"""Factory Method: crea el modelo de clasificación según su nombre de configuración.

Resuelve: poder comparar y reemplazar algoritmos (regresión logística, bosque aleatorio, …)
sin que el flujo de entrenamiento conozca sus detalles. Usado en `src/models/classifier.py`.
"""
from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RANDOM_STATE = 42


def _logistic() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)),
    ])


def _random_forest() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("model", RandomForestClassifier(
            n_estimators=300, max_depth=6, min_samples_leaf=5, class_weight="balanced_subsample",
            random_state=RANDOM_STATE, n_jobs=-1)),
    ])


_BUILDERS = {"regresion_logistica": _logistic, "random_forest": _random_forest}
MODEL_NAMES = list(_BUILDERS)


def make_classifier(name: str) -> Pipeline:
    """Devuelve un pipeline nuevo (imputación ajustada solo al entrenar) para el modelo pedido."""
    try:
        return _BUILDERS[name]()
    except KeyError as exc:
        raise ValueError(f"Modelo desconocido: {name}. Opciones: {MODEL_NAMES}") from exc
