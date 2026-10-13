"""Grupos territoriales (aprendizaje NO supervisado) — componente del nivel Medio.

Agrupa los 87 municipios según su perfil sísmico, de amenaza y de exposición, sin usar
etiquetas. El perfil de cada municipio es el promedio, sobre 2009–2025, de las variables del
panel que no dependen del año (20 variables).

    python -m src.models.clustering
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from src.data.features import FEATURES, MIN_HISTORY_YEARS

PROFILE_FEATURES = [f.name for f in FEATURES if not f.regime_proxy]
LOG_FEATURES = ["n_m25_año", "n_m25_hist_prom", "n_m25_vecinos_año"]
K_RANGE = range(3, 7)      # k = 2 solo separa «activo / tranquilo»; se exige k ≥ 3 para interpretar
RANDOM_STATE = 42


def build_profiles(panel: pd.DataFrame) -> pd.DataFrame:
    """Una fila por municipio: promedio (2009–2025) de las variables independientes del año."""
    usable = panel[panel["años_historia"] >= MIN_HISTORY_YEARS]
    profile = usable.groupby(["cod_mpio", "municipio"])[PROFILE_FEATURES].mean()
    return profile.reset_index()


def _matrix(profile: pd.DataFrame) -> np.ndarray:
    X = profile[PROFILE_FEATURES].copy()
    for c in LOG_FEATURES:
        X[c] = np.log1p(X[c])
    X = X.fillna(X.median())
    return StandardScaler().fit_transform(X)


def fit_groups(profile: pd.DataFrame, k: int | None = None) -> dict:
    """Ajusta K-means (k elegido por silueta si no se indica) y devuelve resultados."""
    Z = _matrix(profile)
    sil = {}
    for kk in K_RANGE:
        labels = KMeans(n_clusters=kk, n_init=10, random_state=RANDOM_STATE).fit_predict(Z)
        sil[kk] = float(silhouette_score(Z, labels))
    chosen = k if k is not None else max(sil, key=sil.get)
    km = KMeans(n_clusters=chosen, n_init=10, random_state=RANDOM_STATE).fit(Z)

    # grupos numerados de mayor a menor actividad media (n_m25_año)
    order = (profile.assign(g=km.labels_).groupby("g")["n_m25_año"].mean()
             .sort_values(ascending=False).index.tolist())
    remap = {old: new + 1 for new, old in enumerate(order)}
    groups = np.array([remap[g] for g in km.labels_])

    pcs = PCA(n_components=2, random_state=RANDOM_STATE).fit(Z)
    coords = pcs.transform(Z)
    out = profile[["cod_mpio", "municipio"]].copy()
    out["grupo"] = groups
    out["pc1"], out["pc2"] = coords[:, 0], coords[:, 1]
    summary = (profile.assign(grupo=groups).groupby("grupo")[PROFILE_FEATURES].mean().round(3))
    sizes = pd.Series(groups).value_counts().sort_index().to_dict()
    return {
        "assignments": out, "k": int(chosen), "silhouette_por_k": {int(a): round(b, 4) for a, b in sil.items()},
        "silhouette": round(sil[chosen], 4), "tamanos": {int(a): int(b) for a, b in sizes.items()},
        "perfil_medio": summary, "varianza_pca": [round(float(v), 4) for v in pcs.explained_variance_ratio_],
        "n_variables": len(PROFILE_FEATURES),
    }


def describe_group(summary: pd.DataFrame, group: int) -> str:
    """Descripción breve y verificable de un grupo a partir de su perfil medio."""
    row = summary.loc[group]
    overall = summary.mean()
    parts = []
    if row["n_m25_año"] >= overall["n_m25_año"]:
        parts.append(f"actividad alta ({row['n_m25_año']:.1f} sismos M≥2,5/año en promedio)")
    else:
        parts.append(f"actividad baja ({row['n_m25_año']:.1f} sismos M≥2,5/año en promedio)")
    parts.append(f"PGA {row['pga_tr475']:.3f} g")
    parts.append(f"{row['pct_superficial_año']:.0f} % de sismos superficiales")
    return "; ".join(parts)


def main() -> None:
    panel = pd.read_csv("data/processed/panel_municipio_anio.csv", dtype={"cod_mpio": str})
    res = fit_groups(build_profiles(panel))
    out = Path("data/processed")
    res["assignments"].to_csv(out / "grupos_territoriales.csv", index=False, float_format="%.5f")
    res["perfil_medio"].to_csv(out / "grupos_perfil_medio.csv")
    meta = {k: v for k, v in res.items() if k not in ("assignments", "perfil_medio")}
    with open(out / "grupos_metricas.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("k =", res["k"], "| silueta =", res["silhouette"], "| por k:", res["silhouette_por_k"])
    print("tamaños:", res["tamanos"])
    print(res["perfil_medio"][["n_m25_año", "magnitud_max_hist", "pct_superficial_año", "pga_tr475",
                               "poblacion_log10", "distancia_los_santos_km"]])


if __name__ == "__main__":
    main()
