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
src/app.py       aplicación Streamlit (creada; clasificación y priorización pendientes de modelos)
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
python -m src.data.preprocessing  # limpieza -> data/processed/eventos_santander_limpio.csv.gz
python -m src.data.completeness   # Mc por año -> data/processed/mc_por_anio.csv
python -m src.data.integration    # une catálogo + DIVIPOLA + amenaza -> municipios_santander.csv
python -m src.data.acquisition    # (una vez, con internet) descarga DIVIPOLA y amenaza a data/raw
streamlit run src/app.py          # aplicación (los datos procesados deben existir)
```

## Estado de las fuentes de datos (verificado 2026-10-13)

- **Catálogo SGC** (`sgc.gov.co/catalogo`): aplicación React sobre `apicatalogador.sgc.gov.co`.
  `GET /api/events/search/` responde 403 y la exportación oficial llega **por correo**
  (`POST /api/events/download/`). Ruta adoptada: descarga manual a `data/raw/`.
  **Descargado y perfilado**: 184 725 eventos, 2006-01-01 a 2026-10-13, 18 columnas. El detalle,
  las advertencias de calidad y el SHA256 están en [docs/fuentes_datos.md](docs/fuentes_datos.md).
  Usar siempre `utc_time` (`local_time` está mal etiquetada) y normalizar el municipio.
- **Amenaza sísmica SGC**: `amenazasismica.sgc.gov.co` tiene el certificado vencido (no se elude).
  Alternativa verificada: MapServer ArcGIS `srvags.sgc.gov.co/arcprod/rest/services/Amenaza_Sismica/`
  `Amenaza_Sismica/MapServer` (rásteres PGA/Sa; `identify` por punto funciona en los 87 municipios).
- **DANE DIVIPOLA** (datos.gov.co `kyaq-ecfy`): 87 municipios con código y coordenadas; coincide
  1 a 1 con los municipios normalizados del catálogo. Población municipal: no verificada.
- **Integración hecha** (2026-10-13): 184 722 eventos unidos a 87 municipios sin pérdidas ni
  duplicados. Salida: `data/processed/municipios_santander.csv` (clave `cod_mpio` / `municipio_key`).
- Detalle y limitaciones en [docs/fuentes_datos.md](docs/fuentes_datos.md).

## Decisiones pendientes

1. ~~Construcción de etiquetas~~ **Decidido (2026-10-13): opción B.** La etiqueta es la categoría de
   actividad sísmica del periodo *siguiente*; las variables de entrada usan solo información del
   periodo actual y anteriores; la amenaza oficial entra como variable, no como etiqueta. Los
   umbrales de categoría se ajustan solo con los periodos de entrenamiento. Obligatorio reportar
   una línea base de persistencia ("misma categoría que el periodo actual") junto al clasificador.
   Redacción: se clasifica actividad sísmica histórica evaluada fuera de muestra; no se predicen
   terremotos concretos.
2. ~~Unidad de análisis~~ **Decidido (2026-10-13): municipio × año** (87 municipios, 2006–2025 como
   años completos; 2026 es parcial y se trata aparte). Umbral de magnitud: propuesta M ≥ 2,5 (completo en todos los años; ver
   `docs/fuentes_datos.md`). **El catálogo cambia de régimen en 2018** (tipo de magnitud, `nst`,
   valor b): la división temporal debe incluir ambos regímenes en entrenamiento.
3. Rúbrica completa y fecha de entrega del reto.

## Notas de dominio (por confirmar con los datos)

- Santander tiene el nido sísmico de Bucaramanga (eventos profundos); la profundidad puede ser bimodal.
- Los eventos recientes del catálogo pueden no estar revisados: fijar una fecha de corte justificada.
