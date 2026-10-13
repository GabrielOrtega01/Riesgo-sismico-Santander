# Riesgo sísmico de Santander

Proyecto universitario (UTS, semillero, nivel avanzado del reto). Análisis y **priorización
exploratoria** de la actividad sísmica histórica de Santander, Colombia, combinando un
clasificador supervisado (Básico / Medio / Avanzado) con un agente de aprendizaje por refuerzo.

Repositorio: https://github.com/GabrielOrtega01/Riesgo-sismico-Santander.git (rama `main`).

## Reglas no negociables

- **No se predicen terremotos.** Nunca afirmar que el sistema predice fecha, lugar o magnitud
  de sismos futuros. Los resultados son análisis exploratorios con supuestos y limitaciones.
- **No es una evaluación oficial de riesgo.** Las categorías son una clasificación propia del
  proyecto, no categorías del SGC. Distinguir siempre amenaza, exposición y vulnerabilidad.
- **No inventar datos, métricas ni resultados.** Distinguir entre implementado, probado y pendiente.
  No afirmar que una prueba pasó si no se ejecutó.
- **Datos crudos inmutables.** `data/raw/` nunca se edita; todo lo derivado va a `data/processed/`.
- **Sin fuga de información.** Orden temporal en las divisiones; los estados del agente y las
  características de un periodo no usan información posterior a ese periodo.
- **Agente RL real.** No sustituirlo por reglas fijas, sumas de puntajes ni un clasificador.
- **Dependencias mínimas.** Agregar una librería solo si una tarea concreta la exige.
- **Patrones de diseño solo si aportan valor** (prioridad: Factory Method, Adapter, Facade, Strategy).

## Forma de trabajo

Dos integrantes, **una sola computadora**, un único entorno y una única copia del repositorio.
Ambos modifican los mismos archivos de forma secuencial: nunca se edita el mismo archivo en paralelo.
Un commit por tarea, con mensaje descriptivo. Sin comandos destructivos sin autorización.

| | Integrante 1 | Integrante 2 |
|---|---|---|
| Foco | Datos y ML supervisado | RL, arquitectura e interfaz |
| Carpetas | `src/data`, `src/models`, `notebooks`, `data` | `src/reinforcement_learning`, `src/services`, `src/patterns`, `src/app.py` |

Compartido: alcance, fuentes, variables, contratos de integración, pruebas, documentación, presentación.

## Estructura

```
data/raw/        originales sin modificar (descarga manual del catálogo SGC)
data/processed/  datos limpios e integrados, variables construidas
data/samples/    muestras pequeñas para pruebas (identificadas como muestras)
notebooks/       exploración y evaluación
src/data/        cargadores, limpieza, integración de fuentes
src/models/      clasificador y evaluación
src/reinforcement_learning/  entorno, agente, recompensa
src/services/    flujo de análisis que une clasificador y agente
src/patterns/    factories, adapters, facade, strategies
src/app.py       aplicación Streamlit (aún no creada)
models/          artefactos entrenados (modelo, política Q)
config/          parámetros de experimento (periodos, semillas, umbrales)
tests/  docs/
```

Los módulos `.py` concretos se crean cuando se implementan; no hay stubs.

## Comandos (PowerShell, desde la raíz)

```powershell
.\.venv\Scripts\Activate.ps1      # activar el entorno (Python 3.14)
pip install -r requirements.txt   # reinstalar dependencias
pytest                            # ejecutar pruebas
streamlit run src/app.py          # aplicación (cuando exista)
```

## Estado de las fuentes de datos (verificado 2026-10-13)

- **Catálogo SGC** (`sgc.gov.co/catalogo`): aplicación React sobre `apicatalogador.sgc.gov.co`.
  `GET /api/events/search/` responde 403 y la exportación oficial llega **por correo**
  (`POST /api/events/download/`). Ruta adoptada: descarga manual a `data/raw/`.
  **Descargado y perfilado**: 184 725 eventos, 2006-01-01 a 2026-10-13, 18 columnas. El detalle,
  las advertencias de calidad y el SHA256 están en [docs/fuentes_datos.md](docs/fuentes_datos.md).
  Usar siempre `utc_time` (`local_time` está mal etiquetada) y normalizar el municipio.
- **Amenaza sísmica SGC**: `amenazasismica.sgc.gov.co` dio error SSL desde este equipo; pendiente
  de confirmar. Candidato adicional: `srvags.sgc.gov.co/jsviewer/Amenaza_Sismica_2020`.
- **DANE** (población municipal): no verificado.

## Decisiones pendientes

1. ~~Construcción de etiquetas~~ **Decidido (2026-10-13): opción B.** La etiqueta es la categoría de
   actividad sísmica del periodo *siguiente*; las variables de entrada usan solo información del
   periodo actual y anteriores; la amenaza oficial entra como variable, no como etiqueta. Los
   umbrales de categoría se ajustan solo con los periodos de entrenamiento. Obligatorio reportar
   una línea base de persistencia ("misma categoría que el periodo actual") junto al clasificador.
   Redacción: se clasifica actividad sísmica histórica evaluada fuera de muestra; no se predicen
   terremotos concretos.
2. Unidad de análisis (87 municipios tras normalizar; ≈57 con ≥100 eventos, cifra preliminar) y granularidad temporal
   (año vs. semestre) y umbral de magnitud Mc: por decidir con los datos.
3. Rúbrica completa y fecha de entrega del reto.

## Notas de dominio (por confirmar con los datos)

- Santander tiene el nido sísmico de Bucaramanga (eventos profundos); la profundidad puede ser bimodal.
- Los eventos recientes del catálogo pueden no estar revisados: fijar una fecha de corte justificada.
