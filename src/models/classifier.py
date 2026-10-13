"""Entrenamiento, evaluación y uso del clasificador de actividad sísmica (supervisado).

Validación temporal (nunca aleatoria):
- Entrenamiento: años t ≤ 2020   (etiqueta hasta 2021)
- Validación:    años t = 2021–2022 (selección de modelo y de conjunto de variables)
- Prueba:        años t = 2023–2024 (se mira una sola vez, con el modelo elegido)

Línea base obligatoria: persistencia («el año siguiente tendrá la misma categoría que este»).

    python -m src.models.classifier
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support

from src.data.features import FEATURE_NAMES, MIN_HISTORY_YEARS, Feature, FEATURES
from src.models.labels import CLASSES, ActivityThresholds, add_targets, fit_thresholds
from src.patterns.factories import MODEL_NAMES, make_classifier

warnings.filterwarnings("ignore", message=".*sklearn.utils.parallel.delayed.*")

TRAIN_END, VAL_YEARS, TEST_YEARS = 2020, (2021, 2022), (2023, 2024)
FINAL_TRAIN_END = 2022
ROLLING_START = 2012
REGIME_PROXIES = [f.name for f in FEATURES if f.regime_proxy]
FEATURE_SETS = {
    "todas": list(FEATURE_NAMES),
    "sin_indicadores_de_regimen": [f for f in FEATURE_NAMES if f not in REGIME_PROXIES],
}
MODEL_PATH = Path("models/clasificador.joblib")


def _usable(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["años_historia"] >= MIN_HISTORY_YEARS]


def _metrics(y_true, y_pred) -> dict:
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=CLASSES, zero_division=0)
    return {
        "exactitud": round(float(accuracy_score(y_true, y_pred)), 4),
        "f1_macro": round(float(f1_score(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0)), 4),
        "por_clase": {c: {"precision": round(float(p[i]), 3), "recall": round(float(r[i]), 3),
                          "f1": round(float(f[i]), 3), "soporte": int(s[i])} for i, c in enumerate(CLASSES)},
        "matriz_confusion": confusion_matrix(y_true, y_pred, labels=CLASSES).tolist(),
        "orden_clases": CLASSES,
        "n": int(len(y_true)),
    }


def _fit(model_name: str, features: list[str], rows: pd.DataFrame):
    model = make_classifier(model_name)
    model.fit(rows[features], rows["etiqueta"])
    return model


def run_experiment(panel: pd.DataFrame) -> dict:
    """Entrena y compara modelos y conjuntos de variables; devuelve resultados y el mejor modelo."""
    labeled0 = _usable(panel)
    labeled0 = labeled0[labeled0["año"] <= TRAIN_END]
    # umbrales ajustados solo con la actividad de los años de entrenamiento (t+1 ≤ 2021)
    tmp = panel.sort_values(["cod_mpio", "año"])
    nxt_counts = tmp.groupby("cod_mpio")["n_m25_año"].shift(-1)
    nxt_mag = tmp.groupby("cod_mpio")["magnitud_max_año"].shift(-1)
    in_train = (tmp["años_historia"] >= MIN_HISTORY_YEARS) & (tmp["año"] <= TRAIN_END) & nxt_counts.notna()
    th = fit_thresholds(nxt_counts[in_train], nxt_mag[in_train])
    data = add_targets(panel, th)
    data = _usable(data)
    labeled = data[data["etiqueta"].notna()]

    train = labeled[labeled["año"] <= TRAIN_END]
    val = labeled[labeled["año"].isin(VAL_YEARS)]
    test = labeled[labeled["año"].isin(TEST_YEARS)]

    results = {"umbrales": th.as_dict(),
               "distribucion_etiquetas": {
                   name: part["etiqueta"].value_counts().reindex(CLASSES, fill_value=0).to_dict()
                   for name, part in (("entrenamiento", train), ("validacion", val), ("prueba", test))},
               "filas": {"entrenamiento": len(train), "validacion": len(val), "prueba": len(test)},
               "validacion": {}, "linea_base": {}}

    # líneas base (en validación y prueba)
    majority = train["etiqueta"].mode().iloc[0]
    for name, part in (("validacion", val), ("prueba", test)):
        results["linea_base"][name] = {
            "persistencia": _metrics(part["etiqueta"], part["actividad_actual"]),
            "clase_mayoritaria": _metrics(part["etiqueta"], [majority] * len(part)),
        }

    # comparación en validación
    scores: dict[tuple[str, str], float] = {}
    for set_name, feats in FEATURE_SETS.items():
        for model_name in MODEL_NAMES:
            model = _fit(model_name, feats, train)
            m = _metrics(val["etiqueta"], model.predict(val[feats]))
            results["validacion"][f"{model_name}|{set_name}"] = m
            scores[(model_name, set_name)] = m["f1_macro"]
    top = max(scores.values())
    # Parsimonia: entre los candidatos a ≤ 0,01 de F1 macro del mejor, se prefiere el conjunto
    # sin indicadores de régimen (no dependen del año) y, a igualdad, el de mayor F1.
    close = [k for k, v in scores.items() if top - v <= 0.01]
    close.sort(key=lambda k: (k[1] != "sin_indicadores_de_regimen", -scores[k]))
    best_model, best_set = close[0]
    results["modelo_elegido"] = {
        "modelo": best_model, "variables": best_set,
        "criterio": "mayor F1 macro en validación; empates (≤ 0,01) se resuelven a favor del "
                    "conjunto sin indicadores de régimen",
    }

    # modelo final: reajuste con años ≤ 2022 y evaluación única en prueba
    feats = FEATURE_SETS[best_set]
    final_rows = labeled[labeled["año"] <= FINAL_TRAIN_END]
    final = _fit(best_model, feats, final_rows)
    test_pred = final.predict(test[feats])
    results["prueba"] = _metrics(test["etiqueta"], test_pred)
    results["prueba_por_año"] = {
        int(y): _metrics(g["etiqueta"], final.predict(g[feats]))["exactitud"]
        for y, g in test.groupby("año")
    }
    results["importancias"] = _importances(final, feats)
    return {"results": results, "model": final, "features": feats, "thresholds": th,
            "model_name": best_model, "data": data, "feature_set": best_set}


def _importances(model, feats: list[str]) -> dict:
    est = model.named_steps["model"]
    imputer = model.named_steps["imputer"]
    names = list(feats) + [f"faltante:{feats[i]}" for i in imputer.indicator_.features_] \
        if getattr(imputer, "indicator_", None) is not None else list(feats)
    if hasattr(est, "feature_importances_"):
        vals = est.feature_importances_
    else:
        vals = np.abs(est.coef_).mean(axis=0)
    pairs = sorted(zip(names, vals), key=lambda p: -p[1])[:12]
    return {n: round(float(v), 4) for n, v in pairs}


def rolling_predictions(data: pd.DataFrame, model_name: str, feats: list[str],
                        final_model) -> pd.DataFrame:
    """Probabilidades fuera de muestra por año (origen móvil), para alimentar al agente.

    Para el año t se entrena solo con filas cuyo año t' tiene etiqueta ya conocida (t'+1 ≤ t).
    Los años de prueba y el último año usan el modelo final (entrenado con años ≤ 2022).
    """
    rows = []
    labeled = data[data["etiqueta"].notna()]
    for t in sorted(data["año"].unique()):
        cur = data[data["año"] == t]
        if t >= ROLLING_START and t <= FINAL_TRAIN_END:
            past = labeled[labeled["año"] <= t - 1]
            if past["etiqueta"].nunique() < 3 or len(past) < 100:
                continue
            model = _fit(model_name, feats, past)
            origin = "origen_movil"
        elif t > FINAL_TRAIN_END:
            model, origin = final_model, "modelo_final"
        else:
            continue
        proba = model.predict_proba(cur[feats])
        classes = list(model.classes_)
        out = cur[["cod_mpio", "municipio_key", "año"]].copy()
        for c in CLASSES:
            out[f"p_{c}"] = proba[:, classes.index(c)] if c in classes else 0.0
        out["prediccion"] = [classes[i] for i in proba.argmax(axis=1)]
        out["origen"] = origin
        rows.append(out)
    return pd.concat(rows, ignore_index=True)


def save_artifacts(bundle: dict, out_dir: str | Path = "data/processed", model_path: Path = MODEL_PATH) -> None:
    out_dir = Path(out_dir)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": bundle["model"], "features": bundle["features"],
                 "thresholds": bundle["thresholds"].as_dict(), "classes": CLASSES,
                 "model_name": bundle["model_name"], "feature_set": bundle["feature_set"]}, model_path)
    with open(out_dir / "clasificador_metricas.json", "w", encoding="utf-8") as fh:
        json.dump(bundle["results"], fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def load_classifier(path: str | Path = MODEL_PATH) -> dict:
    """Carga el modelo entrenado (no requiere volver a entrenar)."""
    return joblib.load(path)


def predict_zone_year(bundle: dict, panel_rows: pd.DataFrame) -> pd.DataFrame:
    """Categoría y probabilidades para las filas del panel dadas (formato del contrato)."""
    feats = bundle["features"]
    proba = bundle["model"].predict_proba(panel_rows[feats])
    classes = list(bundle["model"].classes_)
    out = pd.DataFrame({"zona": panel_rows["municipio"].to_numpy(),
                        "cod_mpio": panel_rows["cod_mpio"].to_numpy(),
                        "año": panel_rows["año"].to_numpy()})
    for c in CLASSES:
        out[f"p_{c}"] = proba[:, classes.index(c)] if c in classes else 0.0
    out["categoria"] = [classes[i] for i in proba.argmax(axis=1)]
    return out


def main() -> None:
    panel = pd.read_csv("data/processed/panel_municipio_anio.csv", dtype={"cod_mpio": str})
    bundle = run_experiment(panel)
    save_artifacts(bundle)
    preds = rolling_predictions(bundle["data"], bundle["model_name"], bundle["features"], bundle["model"])
    preds.to_csv("data/processed/predicciones_clasificador.csv", index=False, float_format="%.5f")
    r = bundle["results"]
    print("Umbrales:", r["umbrales"])
    print("Distribución:", r["distribucion_etiquetas"])
    print("Elegido:", r["modelo_elegido"])
    for k, v in r["validacion"].items():
        print(f"  val {k:50s} acc={v['exactitud']:.3f} f1m={v['f1_macro']:.3f}")
    for k, v in r["linea_base"]["validacion"].items():
        print(f"  val BASE {k:44s} acc={v['exactitud']:.3f} f1m={v['f1_macro']:.3f}")
    print("PRUEBA modelo:", r["prueba"]["exactitud"], r["prueba"]["f1_macro"], r["prueba"]["matriz_confusion"])
    for k, v in r["linea_base"]["prueba"].items():
        print(f"  prueba BASE {k:40s} acc={v['exactitud']:.3f} f1m={v['f1_macro']:.3f}")
    print("Importancias:", r["importancias"])


if __name__ == "__main__":
    main()
