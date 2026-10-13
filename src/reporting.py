"""Genera docs/resultados.md a partir de los JSON de métricas (sin transcribir cifras a mano).

    python -m src.reporting
"""
from __future__ import annotations

import json
from pathlib import Path

P = Path("data/processed")


def _load(name: str) -> dict:
    return json.loads((P / name).read_text(encoding="utf-8"))


def _pct(x: float) -> str:
    return f"{x * 100:.1f} %"


def render() -> str:
    cm, ar, gm = _load("clasificador_metricas.json"), _load("agente_resultados.json"), _load("grupos_metricas.json")
    th, test, base = cm["umbrales"], cm["prueba"], cm["linea_base"]["prueba"]
    L = ["# Resultados", "",
         "> Generado por `python -m src.reporting` desde los archivos de métricas. No editar a mano.", "",
         "Todas las cifras proceden de datos reales del SGC y del DANE. El proyecto **no predice "
         "terremotos** y **no es una evaluación oficial del riesgo**: clasifica y prioriza la "
         "actividad sísmica histórica.", "",
         "## 1. Clasificador supervisado (nivel Básico)", "",
         f"**Etiqueta (año t+1):** conteo de sismos M ≥ 2,5: Bajo ≤ {th['count_low']:.0f}, Medio ≤ "
         f"{th['count_high']:.0f}, Alto mayor; sube un nivel si el mayor sismo del año es ≥ "
         f"{th['strong_magnitude']:.1f}. Umbrales ajustados solo con años de entrenamiento (≤ 2020).", "",
         "| Conjunto | Años (t) | Filas | Bajo | Medio | Alto |", "|---|---|---|---|---|---|"]
    years = {"entrenamiento": "2009–2020", "validacion": "2021–2022", "prueba": "2023–2024"}
    shown = {"entrenamiento": "entrenamiento", "validacion": "validación", "prueba": "prueba"}
    for k, d in cm["distribucion_etiquetas"].items():
        L.append(f"| {shown[k]} | {years[k]} | {cm['filas'][k]} | {d['Bajo']} | {d['Medio']} | {d['Alto']} |")
    L += ["", "### Comparación en validación (2021–2022)", "",
          "| Modelo | Variables | Exactitud | F1 macro |", "|---|---|---|---|"]
    for key, m in cm["validacion"].items():
        model, vars_ = key.split("|")
        L.append(f"| {model} | {vars_} | {m['exactitud']:.3f} | {m['f1_macro']:.3f} |")
    for name, m in cm["linea_base"]["validacion"].items():
        L.append(f"| *línea base: {name}* | — | {m['exactitud']:.3f} | {m['f1_macro']:.3f} |")
    el = cm["modelo_elegido"]
    L += ["", f"**Modelo elegido:** {el['modelo']} con variables «{el['variables']}». {el['criterio']}.", "",
          "### Prueba final (2023–2024, vista una sola vez)", "",
          "| Estrategia | Exactitud | F1 macro |", "|---|---|---|",
          f"| **{el['modelo']}** | **{test['exactitud']:.3f}** | **{test['f1_macro']:.3f}** |"]
    for name, m in base.items():
        L.append(f"| línea base: {name} | {m['exactitud']:.3f} | {m['f1_macro']:.3f} |")
    L += ["", "Matriz de confusión (filas = real; columnas = predicho; orden "
          f"{', '.join(test['orden_clases'])}):", ""]
    for cls, row in zip(test["orden_clases"], test["matriz_confusion"]):
        L.append(f"- {cls}: {row}")
    L += ["", "| Clase | Precisión | Recall | F1 | Casos |", "|---|---|---|---|---|"]
    for cls, m in test["por_clase"].items():
        L.append(f"| {cls} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['soporte']} |")
    L += ["", "**Lectura:** la mejora sobre la persistencia es modesta "
          f"({(test['exactitud'] - base['persistencia']['exactitud']) * 100:+.1f} puntos de exactitud, "
          f"{test['f1_macro'] - base['persistencia']['f1_macro']:+.3f} de F1) y se mide con "
          f"{test['n']} municipios-año; no es concluyente. Los indicadores de régimen de red "
          "(`nst`, errores de localización) no aportaron en validación.", "",
          "## 2. Grupos territoriales (aprendizaje no supervisado, nivel Medio)", "",
          f"K-means con {gm['n_variables']} variables (promedio 2009–2025 por municipio). k = {gm['k']} "
          f"elegido por silueta entre 3 y 6 (silueta = {gm['silhouette']:.3f}; por k: "
          f"{gm['silhouette_por_k']}). Tamaños: {gm['tamanos']}.", "",
          "La silueta es baja: los grupos son una simplificación útil, no fronteras nítidas. Un "
          "municipio (Los Santos) forma su propio grupo por concentrar la sismicidad.", "",
          "## 3. Agente de aprendizaje por refuerzo (nivel Avanzado)", ""]
    c = ar["configuracion"]
    L += [f"Q-learning tabular · K = {c['presupuesto_K']} zonas · {c['episodios']:,} episodios · "
          f"α = {c['alpha']} · γ = {c['gamma']} · {c['estados_totales']} estados "
          f"({c['estados_visitados']} visitados) · costo de revisión {c['costo_revision']} · "
          f"entrenamiento {c['años_entrenamiento'][0]}–{c['años_entrenamiento'][1]}, validación "
          f"{c['años_validacion']}, prueba {c['años_prueba']}.", "",
          "### Protocolo secuencial (utilidad capturada con presupuesto K)", "",
          "| Política | Validación | Prueba |", "|---|---|---|"]
    for name in ar["evaluacion_en_linea"]["prueba"]:
        L.append(f"| {name} | {ar['evaluacion_en_linea']['validacion'][name]:.3f} | "
                 f"{ar['evaluacion_en_linea']['prueba'][name]:.3f} |")
    L.append(f"| *agente sin entrenar* | {ar['agente_sin_entrenar_en_linea_validacion']:.3f} | — |")
    L += ["", "### Ranking: utilidad de las K zonas elegidas", "",
          "| Estrategia | Validación | Prueba | Validación + prueba |", "|---|---|---|---|"]
    ev = ar["evaluacion"]
    for name in ev["prueba"]:
        L.append(f"| {name} | {ev['validacion'][name]['utilidad_media']:.3f} | "
                 f"{ev['prueba'][name]['utilidad_media']:.3f} | "
                 f"{ev['validacion_y_prueba'][name]['utilidad_media']:.3f} |")
    first, last = ar["curva_de_aprendizaje"][0], ar["curva_de_aprendizaje"][-1]
    L += ["", f"**Aprendizaje:** la recompensa media por episodio pasa de {first['recompensa_media']:.3f} "
          f"(episodio {first['episodio']}) a {last['recompensa_media']:.3f} (episodio {last['episodio']}).", "",
          "**Lectura honesta:** el agente supera con claridad a la política aleatoria y a las reglas "
          "fijas por categoría, y es competitivo con las mejores referencias; en el ranking queda "
          "ligeramente por debajo de la persistencia y no la supera de forma consistente. Con "
          "4 años de evaluación las diferencias entre las estrategias mejores no son concluyentes.", "",
          "**Limitaciones:** la recompensa mide actividad y exposición observadas, no daños ni "
          "vulnerabilidad; la actividad está muy concentrada en un municipio; las probabilidades del "
          "clasificador usadas como estado provienen de modelos de origen móvil (sin ver el futuro) "
          "pero los umbrales de etiqueta se ajustaron con años hasta 2020.", ""]
    return "\n".join(L)


def main() -> None:
    Path("docs/resultados.md").write_text(render(), encoding="utf-8")
    print("docs/resultados.md generado")


if __name__ == "__main__":
    main()
