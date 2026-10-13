# Resultados

> Generado por `python -m src.reporting` desde los archivos de métricas. No editar a mano.

Todas las cifras proceden de datos reales del SGC y del DANE. El proyecto **no predice terremotos** y **no es una evaluación oficial del riesgo**: clasifica y prioriza la actividad sísmica histórica.

## 1. Clasificador supervisado (nivel Básico)

**Etiqueta (año t+1):** conteo de sismos M ≥ 2,5: Bajo ≤ 0, Medio ≤ 3, Alto mayor; sube un nivel si el mayor sismo del año es ≥ 4.1. Umbrales ajustados solo con años de entrenamiento (≤ 2020).

| Conjunto | Años (t) | Filas | Bajo | Medio | Alto |
|---|---|---|---|---|---|
| entrenamiento | 2009–2020 | 1044 | 627 | 295 | 122 |
| validación | 2021–2022 | 174 | 99 | 51 | 24 |
| prueba | 2023–2024 | 174 | 98 | 53 | 23 |

### Comparación en validación (2021–2022)

| Modelo | Variables | Exactitud | F1 macro |
|---|---|---|---|
| regresion_logistica | todas | 0.621 | 0.577 |
| random_forest | todas | 0.707 | 0.699 |
| regresion_logistica | sin_indicadores_de_regimen | 0.644 | 0.594 |
| random_forest | sin_indicadores_de_regimen | 0.707 | 0.698 |
| *línea base: persistencia* | — | 0.684 | 0.655 |
| *línea base: clase_mayoritaria* | — | 0.569 | 0.242 |

**Modelo elegido:** random_forest con variables «sin_indicadores_de_regimen». mayor F1 macro en validación; empates (≤ 0,01) se resuelven a favor del conjunto sin indicadores de régimen.

### Prueba final (2023–2024, vista una sola vez)

| Estrategia | Exactitud | F1 macro |
|---|---|---|
| **random_forest** | **0.753** | **0.755** |
| línea base: persistencia | 0.736 | 0.733 |
| línea base: clase_mayoritaria | 0.563 | 0.240 |

Matriz de confusión (filas = real; columnas = predicho; orden Bajo, Medio, Alto):

- Bajo: [76, 22, 0]
- Medio: [13, 35, 5]
- Alto: [0, 3, 20]

| Clase | Precisión | Recall | F1 | Casos |
|---|---|---|---|---|
| Bajo | 0.854 | 0.776 | 0.813 | 98 |
| Medio | 0.583 | 0.660 | 0.619 | 53 |
| Alto | 0.800 | 0.870 | 0.833 | 23 |

**Lectura:** la mejora sobre la persistencia es modesta (+1.7 puntos de exactitud, +0.022 de F1) y se mide con 174 municipios-año; no es concluyente. Los indicadores de régimen de red (`nst`, errores de localización) no aportaron en validación.

## 2. Grupos territoriales (aprendizaje no supervisado, nivel Medio)

K-means con 20 variables (promedio 2009–2025 por municipio). k = 6 elegido por silueta entre 3 y 6 (silueta = 0.211; por k: {'3': 0.1825, '4': 0.1626, '5': 0.1881, '6': 0.2108}). Tamaños: {'1': 1, '2': 28, '3': 8, '4': 22, '5': 12, '6': 16}.

La silueta es baja: los grupos son una simplificación útil, no fronteras nítidas. Un municipio (Los Santos) forma su propio grupo por concentrar la sismicidad.

## 3. Agente de aprendizaje por refuerzo (nivel Avanzado)

Q-learning tabular · K = 10 zonas · 12,000 episodios · α = 0.1 · γ = 1.0 · 486 estados (192 visitados) · costo de revisión 0.01 · entrenamiento 2012–2020, validación [2021, 2022], prueba [2023, 2024].

### Protocolo secuencial (utilidad capturada con presupuesto K)

| Política | Validación | Prueba |
|---|---|---|
| Agente de refuerzo (política aprendida) | 0.849 | 0.897 |
| Aleatoria (acciones válidas al azar) | 0.111 | 0.108 |
| Primeras K zonas presentadas | 0.120 | 0.122 |
| Regla fija: categoría predicha ≥ Medio | 0.213 | 0.229 |
| Regla fija: actividad del año alta | 0.899 | 0.809 |
| *agente sin entrenar* | 0.000 | — |

### Ranking: utilidad de las K zonas elegidas

| Estrategia | Validación | Prueba | Validación + prueba |
|---|---|---|---|
| Agente de refuerzo (Q-learning) | 0.859 | 0.926 | 0.892 |
| Persistencia (actividad del año) | 0.899 | 0.928 | 0.914 |
| Historia (promedio anual previo) | 0.862 | 0.904 | 0.883 |
| Solo clasificador (categoría esperada) | 0.900 | 0.909 | 0.904 |
| Aleatoria | 0.111 | 0.111 | 0.114 |
| Óptimo (conoce el futuro; cota superior) | 0.953 | 0.956 | 0.954 |

**Aprendizaje:** la recompensa media por episodio pasa de 0.197 (episodio 500) a 0.691 (episodio 12000).

**Lectura honesta:** el agente supera con claridad a la política aleatoria y a las reglas fijas por categoría, y es competitivo con las mejores referencias; en el ranking queda ligeramente por debajo de la persistencia y no la supera de forma consistente. Con 4 años de evaluación las diferencias entre las estrategias mejores no son concluyentes.

**Limitaciones:** la recompensa mide actividad y exposición observadas, no daños ni vulnerabilidad; la actividad está muy concentrada en un municipio; las probabilidades del clasificador usadas como estado provienen de modelos de origen móvil (sin ver el futuro) pero los umbrales de etiqueta se ajustaron con años hasta 2020.
