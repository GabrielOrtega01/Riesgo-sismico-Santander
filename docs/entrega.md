# Entrega · Hackathon CIAI UTSmart 2026 · Nivel Avanzado

Equipo **Bucara Hackers**: Juan Jose Perucho Quintero · Gabriel Augusto Ortega Martínez
Repositorio: https://github.com/GabrielOrtega01/Riesgo-sismico-Santander
Aplicación (prevista): https://seismox.streamlit.app/

## Requisitos habilitantes

| Requisito | Cumplimiento | Dónde |
|---|---|---|
| Modelo de ML funcional entrenado por el equipo y demostrable en vivo | Sí | `models/clasificador.joblib`, `models/politica_q.npz`; aplicación Seismox |
| Supervisado (Básico) | Random Forest, validación temporal, línea base de persistencia | `src/models/classifier.py`, `docs/resultados.md` §1 |
| No supervisado (Medio) | K-means, 6 grupos territoriales con 20 variables, mapa | `src/models/clustering.py`, página «Grupos territoriales» |
| Aprendizaje por refuerzo (Avanzado) | Q-learning tabular, entorno propio, evaluación frente a referencias | `src/reinforcement_learning/`, `docs/resultados.md` §3 |
| Datos reales de fuente oficial citada | SGC y DANE (ver abajo) | `docs/fuentes_datos.md` |
| Variables mínimas (20 en Avanzado) | 23 (20 sin los indicadores de régimen) | `docs/diccionario_variables.md` |
| Segunda fuente oficial integrada | Amenaza sísmica 2020 (SGC), DIVIPOLA y población (DANE) | `src/data/integration.py` |
| Flujo funcional y verificable con demostración de la priorización (sin API) | Sí | `src/services/risk_analysis.py`, página «Priorización» |

## Entregables

| Entregable | Archivo |
|---|---|
| Dataset limpio (CSV) | `data/processed/eventos_santander_limpio.csv.gz` (184 722 eventos) y `data/processed/panel_municipio_anio.csv` (1 740 filas × variables) |
| Diccionario con la justificación de cada variable | `docs/diccionario_variables.md` |
| Fuente oficial citada (dirección, fecha y filtros) | ver «Fuentes» |
| Código del análisis y del entrenamiento (repositorio reproducible) | `src/`, `README.md` (comandos), `tests/` (117 pruebas) |
| Modelo obligatorio con métricas y validación | `data/processed/clasificador_metricas.json`, `agente_resultados.json`, `docs/resultados.md` |
| Prototipo / demostración | Aplicación Streamlit (`streamlit run src/app.py`) |
| Presentación | `docs/presentacion.md` (guion de 10 minutos) |

## Fuentes (con dirección, fecha y filtros)

| Fuente | Dirección | Fecha de descarga | Filtros |
|---|---|---|---|
| SGC · Catálogo sísmico de la Red Sismológica Nacional | https://sgc.gov.co/catalogo | 2026-10-13 | Departamento Santander; 2006-01-01 a 2026-10-13; todas las magnitudes; exportación CSV |
| SGC · Amenaza Sísmica 2020 | https://srvags.sgc.gov.co/arcprod/rest/services/Amenaza_Sismica/Amenaza_Sismica/MapServer | 2026-10-13 | Valores de PGA, Sa(0,2), Sa(1,0) e intensidad en la cabecera de los 87 municipios |
| DANE · DIVIPOLA Municipios Santander | https://www.datos.gov.co (conjunto `kyaq-ecfy`) | 2026-10-13 | Departamento Santander |
| DANE · Proyecciones de población municipal | https://www.dane.gov.co (Proyecciones de población, serie municipal por área) | 2026-10-13 | Departamento 68; 2005–2026 |

## Reproducir

```powershell
pip install -r requirements.txt
python -m src.data.preprocessing ; python -m src.data.integration ; python -m src.data.population
python -m src.data.features ; python -m src.models.classifier
python -m src.models.clustering ; python -m src.reinforcement_learning.training
python -m src.reporting ; pytest ; streamlit run src/app.py
```

## Límites que declaramos

No predice terremotos ni es una evaluación oficial del riesgo. El catálogo cambia de régimen en 2018.
La mejora del clasificador sobre la persistencia es modesta; el agente es competitivo pero no supera
de forma consistente a la mejor referencia simple. Ver `docs/resultados.md`.
