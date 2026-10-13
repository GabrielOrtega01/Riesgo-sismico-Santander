# Arquitectura y patrones de diseño

## Flujo

```
fuentes oficiales            procesamiento              modelos                      aplicación
─────────────────            ─────────────              ───────                      ──────────
SGC catálogo ──┐             loaders → preprocessing
SGC amenaza ───┼─ acquisition → integration → features ─► clasificador (supervisado)  ┐
DANE DIVIPOLA ─┤             population ──────────────► grupos (no supervisado)       ├► RiskAnalysisService ─► Streamlit
DANE población ┘                                       ► agente RL (Q-learning)      ┘   (Facade)
```

## Módulos

| Módulo | Responsabilidad |
|---|---|
| `src/data/loaders.py`, `preprocessing.py`, `integration.py`, `population.py`, `acquisition.py` | Carga, limpieza, unión de fuentes y descarga reproducible |
| `src/data/features.py` | Panel municipio × año, 23 variables, diccionario y control de fuga |
| `src/models/labels.py` | Etiquetas Bajo/Medio/Alto del año siguiente |
| `src/models/classifier.py` | Entrenamiento, validación temporal, línea base y persistencia del modelo |
| `src/models/clustering.py` | Grupos territoriales (K-means) |
| `src/reinforcement_learning/` | `environment.py` (estados/acciones), `reward.py`, `agent.py` (Q-learning), `training.py` |
| `src/services/risk_analysis.py` | Flujo integrado clasificador → estados → agente → priorización |
| `src/app.py`, `src/ui/` | Interfaz Streamlit |

## Patrones aplicados (solo donde resuelven una necesidad)

| Patrón | Archivo | Problema que resuelve |
|---|---|---|
| **Factory Method** | `src/patterns/factories.py` (`make_classifier`) | Crear y comparar modelos (regresión logística, Random Forest) por nombre de configuración sin que el flujo de entrenamiento conozca sus detalles |
| **Strategy** | `src/patterns/strategies.py` | Intercambiar estrategias de priorización (agente, persistencia, historia, solo clasificador, aleatoria) con una misma evaluación |
| **Facade** | `src/services/risk_analysis.py` (`RiskAnalysisService`) | Ofrecer a la aplicación una interfaz simple sobre el flujo completo de modelos y artefactos |
| **Observer** (ligero) | `src/reinforcement_learning/agent.py` (`train(observers=…)`) | Registrar la curva de aprendizaje y evaluar en validación sin acoplar el agente a la evaluación |

No se implementaron Adapter ni Builder: la lectura de fuentes se resuelve con funciones de carga
específicas y la configuración del experimento es pequeña; agregarlos solo habría sumado patrones
sin necesidad real.

## Contrato clasificador → agente

Salida del clasificador (`predict_zone_year`): `zona`, `cod_mpio`, `anio`, `p_Bajo`, `p_Medio`,
`p_Alto`, `categoria`. El agente consume `categoria` (discretizada en 3 niveles) junto con la
actividad del año, la amenaza (PGA) y la exposición (población) del panel.
