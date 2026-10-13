# Diccionario de variables

> Generado automáticamente desde `src/data/features.py` (`python -m src.data.features`). No editar a mano: modificar la lista `FEATURES` y regenerar.

## Resumen

- **23 variables de entrada** candidatas para el clasificador, en 8 grupos.
- Originales del catálogo o de las fuentes: 7; derivadas: 16.
- Candidatas a **estado del agente** de refuerzo: 4 (propuesta; se confirma al diseñar el entorno).
- **Unidad de análisis:** municipio × año. Años del panel: 2006–2025; 2026 queda fuera por ser parcial.
- **Umbral de magnitud** de los conteos: M ≥ 2.5 (completo en todos los años).
- **Sin fuga temporal:** cada variable de la fila del año *t* usa solo eventos con año ≤ *t*; las históricas usan años < *t*. La prueba `test_no_future_leakage` lo verifica.
- **Etiqueta:** no forma parte de este panel; se construye aparte con el año *t*+1.
- **Faltantes:** no se imputan aquí. La imputación se ajusta solo con datos de entrenamiento.

Filas del panel: 1740 (87 municipios × 20 años). Utilizables para modelar (≥ 3 años de historia): 1479 (2009–2025).

## Frecuencia

| Variable | Descripción | Fuente | Tipo | Fórmula | Unidad | % faltante | ρ con el año |
|---|---|---|---|---|---|---|---|
| `n_m25_anio` ★ | Sismos de magnitud ≥ 2,5 en el municipio durante el año t. | Catálogo SGC | derivada, conteo | count(magnitude ≥ 2,5, año = t) | sismos/año | 0.0 | -0.01 |
| `n_m25_hist_prom` ★ | Promedio anual de sismos M ≥ 2,5 en los años anteriores a t. | Catálogo SGC | derivada, numérica continua | mean(n_m25_anio de los años < t) | sismos/año | 0.0 | -0.03 |
| `n_m25_cambio_1a` | Cambio del conteo M ≥ 2,5 respecto al año anterior. | Catálogo SGC | derivada, numérica discreta | n_m25_anio(t) − n_m25_anio(t−1) | sismos/año | 0.0 | +0.01 |

| Variable | Tratamiento de faltantes | Justificación | Limitaciones |
|---|---|---|---|
| `n_m25_anio` | Sin faltantes: 0 si no hubo eventos. | Nivel de actividad del año. El umbral 2,5 es completo en todos los años del catálogo (Mc). | Conteos bajos por municipio: muchos años con 0. |
| `n_m25_hist_prom` | NaN en el primer año (sin historia). | Nivel base de largo plazo: separa un año excepcional de un municipio habitualmente activo. | Mezcla el régimen de red anterior y posterior a 2018. |
| `n_m25_cambio_1a` | NaN en el primer año. | Tendencia reciente de la actividad, distinta de su nivel. | Ruidosa cuando los conteos son pequeños. |

## Frecuencia espacial

| Variable | Descripción | Fuente | Tipo | Fórmula | Unidad | % faltante | ρ con el año |
|---|---|---|---|---|---|---|---|
| `n_m25_vecinos_anio` | Sismos M ≥ 2,5 del año t en otros municipios cuya cabecera está a ≤ 50 km. | Catálogo SGC + DIVIPOLA DANE | derivada, conteo | Σ n_m25_anio(vecino), distancia entre cabeceras ≤ 50 km | sismos/año | 0.0 | +0.06 |

| Variable | Tratamiento de faltantes | Justificación | Limitaciones |
|---|---|---|---|
| `n_m25_vecinos_anio` | Sin faltantes: 0 si no hay vecinos activos. | Contexto regional: la actividad cercana no queda capturada por el propio municipio. | Usa la cabecera como punto del municipio; la etiqueta `place` es una referencia, no un polígono. |

## Magnitud

| Variable | Descripción | Fuente | Tipo | Fórmula | Unidad | % faltante | ρ con el año |
|---|---|---|---|---|---|---|---|
| `magnitud_max_anio` | Mayor magnitud registrada en el municipio durante el año t. | Catálogo SGC | derivada, numérica continua | max(magnitude, año = t) | magnitud | 8.4 | -0.01 |
| `magnitud_media_m25_anio` | Magnitud media de los sismos M ≥ 2,5 del año t. | Catálogo SGC | derivada, numérica continua | mean(magnitude | magnitude ≥ 2,5, año = t) | magnitud | 58.8 | -0.10 |
| `magnitud_max_hist` | Mayor magnitud registrada en el municipio antes del año t. | Catálogo SGC | derivada, numérica continua | max(magnitude, años < t) | magnitud | 0.1 | +0.24 |
| `pct_m30_sobre_m25` | Porcentaje de los sismos M ≥ 2,5 del año que tienen M ≥ 3,0. | Catálogo SGC | derivada, porcentaje | 100 · n(M ≥ 3,0) / n(M ≥ 2,5) | % | 58.8 | -0.08 |

| Variable | Tratamiento de faltantes | Justificación | Limitaciones |
|---|---|---|---|
| `magnitud_max_anio` | NaN si no hubo eventos ese año. | Severidad del evento más fuerte; el máximo es robusto a la incompletitud del catálogo. | Mezcla tipos de magnitud (ML, MLr, MW) sin homogenizar. |
| `magnitud_media_m25_anio` | NaN si no hubo eventos M ≥ 2,5. | Forma típica de la distribución, distinta de su extremo. | Pocos eventos → media inestable. |
| `magnitud_max_hist` | NaN en el primer año o si no hubo eventos. | Techo conocido de la actividad del municipio. | Depende del periodo observado (20 años). |
| `pct_m30_sobre_m25` | NaN si no hubo eventos M ≥ 2,5. | Proporción de eventos relativamente fuertes (cola de la distribución). | Inestable con pocos eventos. |

## Profundidad

| Variable | Descripción | Fuente | Tipo | Fórmula | Unidad | % faltante | ρ con el año |
|---|---|---|---|---|---|---|---|
| `profundidad_mediana_anio` | Profundidad mediana de los sismos del año t. | Catálogo SGC | derivada, numérica continua | median(depth, año = t) | km | 8.4 | -0.04 |
| `pct_superficial_anio` ★ | Porcentaje de sismos del año con profundidad < 30 km. | Catálogo SGC | derivada, porcentaje | 100 · n(depth < 30) / n(total) | % | 8.4 | +0.11 |
| `profundidad_iqr_anio` | Rango intercuartílico de la profundidad de los sismos del año. | Catálogo SGC | derivada, numérica continua | Q3(depth) − Q1(depth), año = t | km | 8.4 | +0.14 |

| Variable | Tratamiento de faltantes | Justificación | Limitaciones |
|---|---|---|---|
| `profundidad_mediana_anio` | NaN si no hubo eventos. | Separa la sismicidad profunda (nido de Bucaramanga) de la superficial. | La profundidad tiene error (puede ser grande en eventos con pocas estaciones). |
| `pct_superficial_anio` | NaN si no hubo eventos. | Los eventos superficiales son los que más importan para las construcciones. | El umbral de 30 km es una convención del proyecto. |
| `profundidad_iqr_anio` | NaN si no hubo eventos. | Dispersión: detecta mezcla de poblaciones profundas y superficiales. | Requiere varios eventos para ser estable. |

## Calidad de localización

| Variable | Descripción | Fuente | Tipo | Fórmula | Unidad | % faltante | ρ con el año |
|---|---|---|---|---|---|---|---|
| `nst_mediano_anio` ⚠ | Mediana del número de estaciones/fases por evento. | Catálogo SGC | original, conteo | median(nst, año = t) | estaciones | 8.4 | +0.72 |
| `gap_mediano_anio` | Mediana del hueco azimutal (gap) de las localizaciones. | Catálogo SGC | original, numérica continua | median(gap, año = t) | grados | 8.4 | -0.24 |
| `error_horizontal_mediano_anio` ⚠ | Mediana del error horizontal de la localización. | Catálogo SGC | derivada, numérica continua | median(√(latitude_error² + longitude_error²), año = t) | km (supuesto) | 8.4 | +0.73 |
| `rms_mediano_anio` | Mediana del residuo (RMS) del ajuste de localización. | Catálogo SGC | original, numérica continua | median(rms, año = t) | s | 8.4 | +0.44 |
| `error_profundidad_mediano_anio` ⚠ | Mediana del error de profundidad reportado. | Catálogo SGC | original, numérica continua | median(depth_error, año = t) | km (supuesto) | 8.4 | -0.65 |

| Variable | Tratamiento de faltantes | Justificación | Limitaciones |
|---|---|---|---|
| `nst_mediano_anio` | NaN si no hubo eventos. | Indicador de cobertura de la red en la zona; condiciona qué tan completo es el catálogo allí. | Cambia de régimen hacia 2018 (ρ = 0,72 con el año): puede actuar como indicador de año. Se evalúa con y sin ella. |
| `gap_mediano_anio` | NaN si no hubo eventos. | Un hueco grande indica estaciones mal distribuidas alrededor del epicentro. | Un solo valor de gap por evento; no se ha validado frente a la geometría real de la red. |
| `error_horizontal_mediano_anio` | NaN si no hubo eventos o faltan ambos errores. | Incertidumbre de la ubicación: afecta a qué municipio se asigna el evento. | La unidad (km) se asume y no está verificada en la documentación del catálogo. Sigue al año (ρ = 0,73): se evalúa con y sin ella. |
| `rms_mediano_anio` | NaN si no hubo eventos. | Calidad del ajuste del modelo de velocidades a las llegadas observadas. | Correlaciona con el número de estaciones. |
| `error_profundidad_mediano_anio` | NaN si no hubo eventos o falta el error (263 casos en el catálogo). | Confiabilidad de la profundidad usada en las variables de profundidad. | Unidad asumida; valores extremos (hasta 1 000). Sigue al año (ρ = −0,65): se evalúa con y sin ella. |

## Amenaza oficial

| Variable | Descripción | Fuente | Tipo | Fórmula | Unidad | % faltante | ρ con el año |
|---|---|---|---|---|---|---|---|
| `pga_tr475` ★ | Aceleración máxima del suelo esperada (PGA) para Tr = 475 años. | Amenaza SGC 2020 | original, numérica continua | valor del ráster en la cabecera municipal | g | 0.0 | +0.00 |
| `intensidad_esperada` | Intensidad sísmica esperada según el SGC. | Amenaza SGC 2020 | original, ordinal (6, 7) | valor del ráster en la cabecera municipal | grado | 0.0 | +0.00 |
| `sa10_sobre_pga` | Cociente entre la aceleración espectral a 1,0 s y el PGA (Tr = 475 años). | Amenaza SGC 2020 | derivada, numérica continua | sa10_tr475 / pga_tr475 | adimensional | 0.0 | +0.00 |

| Variable | Tratamiento de faltantes | Justificación | Limitaciones |
|---|---|---|---|
| `pga_tr475` | Sin faltantes (87 de 87 municipios). | Estimación oficial de la amenaza por municipio. | Mapa estático de 2020, no independiente de los eventos usados; un punto por municipio; rango estrecho (0,20–0,28 g). |
| `intensidad_esperada` | Sin faltantes. | Medida oficial de efectos esperados, en una escala distinta de la aceleración. | Solo toma dos valores; correlaciona con el PGA. |
| `sa10_sobre_pga` | Sin faltantes. | Forma del espectro: aporta información sobre el contenido de periodos largos. | Muy poca variación entre municipios. |

## Geografía

| Variable | Descripción | Fuente | Tipo | Fórmula | Unidad | % faltante | ρ con el año |
|---|---|---|---|---|---|---|---|
| `distancia_los_santos_km` | Distancia desde la cabecera del municipio a la de Los Santos. | DIVIPOLA DANE | derivada, numérica continua | haversine(cabecera, cabecera de Los Santos) | km | 0.0 | +0.00 |

| Variable | Tratamiento de faltantes | Justificación | Limitaciones |
|---|---|---|---|
| `distancia_los_santos_km` | Sin faltantes. | Posición relativa a la zona donde se concentra la sismicidad profunda de la región. | Usa un municipio como referencia del nido sísmico; es una aproximación geográfica. |

## Exposición

| Variable | Descripción | Fuente | Tipo | Fórmula | Unidad | % faltante | ρ con el año |
|---|---|---|---|---|---|---|---|
| `poblacion_log10` | Logaritmo decimal de la población total proyectada del año t. | Población DANE | derivada, numérica continua | log10(poblacion_total) | log10(hab.) | 0.0 | +0.03 |
| `pct_poblacion_cabecera` | Porcentaje de la población que vive en la cabecera. | Población DANE | original, porcentaje | 100 · poblacion_cabecera / poblacion_total | % | 0.0 | +0.12 |
| `crecimiento_poblacion_pct` | Variación porcentual de la población respecto al año anterior. | Población DANE | derivada, numérica continua | 100 · (pob(t) / pob(t−1) − 1) | % | 0.0 | +0.40 |

| Variable | Tratamiento de faltantes | Justificación | Limitaciones |
|---|---|---|---|
| `poblacion_log10` | Sin faltantes (2005–2026). | Exposición: cuánta gente habita el municipio. El logaritmo estabiliza la asimetría. | Son proyecciones; mide exposición, no vulnerabilidad. |
| `pct_poblacion_cabecera` | Sin faltantes. | Grado de concentración urbana de la exposición. | Cambia lentamente; casi constante por municipio. |
| `crecimiento_poblacion_pct` | Sin faltantes (la serie incluye 2005). | Dinámica de la exposición. | Efecto del empalme de series 2017/2018 (verificado como pequeño). |

★ = candidata a estado del agente de refuerzo. ⚠ = indicador de régimen (sigue al año; se evalúa con y sin ella).

## Cuántas variables independientes hay

- Variables de entrada del panel: **23**.
- Sin las 3 que pueden codificar el año (⚠): **20**. El mínimo exigido (20) se cumple con y sin ellas.
- Regla aplicada: se descartó una variable de cada par con |ρ de Spearman| ≥ 0.90. Los pares entre 0,85 y 0,90 se conservan y se vigilan.

Pares con |ρ| ≥ 0,85 entre las variables **finales** (se conservan):

| Variable A | Variable B | ρ de Spearman |
|---|---|---|
| `magnitud_media_m25_anio` | `pct_m30_sobre_m25` | +0.875 |
| `n_m25_anio` | `magnitud_max_anio` | +0.873 |

## Variables evaluadas y descartadas

| Variable | Motivo | Evidencia |
|---|---|---|
| `meses_activos_m25` | Redundante con `n_m25_anio` (ρ de Spearman = 0,998): en la mayoría de los municipios-año con eventos, cada sismo cae en un mes distinto. | medida en el panel |
| `frac_anios_activos_hist` | Redundante con `n_m25_hist_prom` (ρ = 0,953): ambas miden qué tan habitualmente es activo el municipio. | medida en el panel |
| `n_total_anio (todos los sismos del año)` | Su conteo depende de la red de detección (pasa de ≈2 400 a ≈16 000 eventos/año), no solo de la sismicidad; se usa M ≥ 2,5 en su lugar. | documentada en fuentes_datos.md |
| `energia_anual (suma de energía liberada)` | Casi determinada por la magnitud máxima del año; no aporta una dimensión nueva con los conteos tan bajos por municipio. | criterio a priori, no medida |
| `valor_b_anual` | Inestable con los pocos eventos por municipio y año. | criterio a priori, no medida |
| `latitud / longitud de la cabecera` | Quedan resumidas por `distancia_los_santos_km`; las coordenadas crudas facilitarían identificar municipios y sobreajustar. | criterio a priori |
