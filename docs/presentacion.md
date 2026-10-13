# Guion de la presentación (10 min + 3 min de preguntas)

**Equipo:** Gabriel Augusto Ortega Martínez · Juan Jose Perucho Quintero · **Seismox** (Nivel Avanzado)

| Min | Quién | Qué decir / mostrar |
|---|---|---|
| 0:00–1:00 | Gabriel | Problema: Santander registra miles de sismos al año, casi todos profundos y pequeños (nido de Bucaramanga). Pregunta: ¿cómo clasificar y priorizar zonas con datos oficiales? **Qué no es:** no predice terremotos ni es evaluación oficial. |
| 1:00–2:30 | Gabriel | Datos: catálogo SGC (184 722 eventos, 2006–2026), amenaza sísmica 2020 (SGC), DIVIPOLA y población (DANE). 87 municipios integrados sin pérdidas. Hallazgo: el catálogo cambia de régimen en 2018 → usamos M ≥ 2,5. |
| 2:30–3:30 | Gabriel | 23 variables (diccionario), panel municipio × año, **control de fuga temporal** (prueba automática). |
| 3:30–5:00 | Juan Jose | **Básico:** clasificación Bajo/Medio/Alto del año siguiente. Validación temporal; Random Forest 75,3 % de exactitud vs 73,6 % de la persistencia: mejora **modesta**, lo decimos. Mostrar matriz de confusión en la app. |
| 5:00–6:00 | Juan Jose | **Medio:** K-means (6 grupos, 20 variables), mapa territorial. Silueta baja (0,21): simplificación útil. |
| 6:00–8:00 | Juan Jose | **Avanzado:** agente Q-learning. Estados, acciones, recompensa. Curva de aprendizaje; frente a referencias: supera a aleatoria (0,11 → ~0,9), competitivo con persistencia, no concluyente. |
| 8:00–9:30 | Ambos | **Demostración en vivo en Seismox:** Inicio → Explorar una zona → Mapa → Clasificación (año 2025) → Priorización (top 10) → Fuentes y límites. |
| 9:30–10:00 | Ambos | Cierre: lo que aprendimos, límites (vulnerabilidad no medida, actividad concentrada), qué sigue. |

## Preguntas probables y respuestas

- **¿Predice terremotos?** No. Clasifica la actividad histórica esperada del año siguiente; evaluada fuera de muestra.
- **¿Por qué la mejora es tan pequeña?** La actividad por municipio es muy persistente; la línea base de persistencia ya es fuerte. Lo reportamos sin maquillar.
- **¿Qué pasó con el agente frente a la persistencia?** Queda a la par; con 4 años de evaluación la diferencia no es concluyente.
- **¿Hay fuga de información?** División temporal, umbrales ajustados con entrenamiento, variables históricas solo con años previos y una prueba automática que lo verifica.
- **¿Por qué M ≥ 2,5?** Es el umbral completo en todos los años; con 2,0 los años 2006–2008 no son comparables.
- **¿Por qué las probabilidades del clasificador alimentan al agente?** Es la integración exigida; se usan probabilidades fuera de muestra (origen móvil).
