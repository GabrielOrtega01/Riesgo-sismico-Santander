# Fuentes de datos

Documento vivo. Solo contiene hechos verificados sobre los archivos reales; lo no verificado
está marcado como **pendiente**.

## 1. Catálogo sísmico del SGC (fuente principal)

| Campo | Valor |
|---|---|
| Origen | Servicio Geológico Colombiano, https://sgc.gov.co/catalogo (exportación enviada por correo) |
| Archivo original | `20261013_143231_3f5367c3-8fe8-487d-9e88-3d4f4fadf814.csv` (descargado 2026-10-13) |
| Copia en el repositorio | `data/raw/sgc_catalogo_santander_20060101_20261013.csv` (solo renombrada, contenido idéntico) |
| SHA256 | `DCC9516C88A6978AD0123DA6D2AF8FACBF81E3653F9313261CE2DD0E1931E803` |
| Tamaño / registros | 28,9 MB · 184 725 eventos · 18 columnas |
| Periodo cubierto | 2006-01-01 05:53:16 UTC → 2026-10-13 12:53:10 UTC (2026 es un año incompleto) |
| Selección espacial | Filtro por departamento Santander aplicado en el catálogo (el 100 % de `place` termina en "Santander, Colombia"). Los límites de coordenadas son lat 5,71–8,12 y lon −74,51 a −72,43. |
| Estado de revisión | 184 722 `manual`, 3 `automatic`. Única agencia: `SGC`. |

### Columnas

| Columna | Tipo | Nulos | Notas |
|---|---|---|---|
| `id` | texto | 0 | Único (0 duplicados). |
| `status` | cat. | 0 | Casi constante (`manual`). |
| `agency` | cat. | 0 | Constante (`SGC`): sin valor como variable. |
| `rms` | num. | 0 | Rango 0–9,4. |
| `gap` | num. | 1 | Grados, 24–352. |
| `place` | texto | 0 | Formato `Municipio - Departamento, Colombia`. El municipio es la cabecera más cercana en el 89 % de los eventos (ver sección 4); no se puede distinguir "contiene" de "más cercano" sin polígonos. |
| `local_time` | fecha | 0 | **Ver advertencia**: etiquetada `+00:00` pero equivale a UTC−5. |
| `utc_time` | fecha | 0 | Usar esta. |
| `magnitude` | num. | 0 | −1,3 a 6,4. |
| `magnitude_error` | num. | 79 092 (42,8 %) | |
| `nst` | num. | 0 | Número de estaciones/fases, 3–121. |
| `mag_type` | cat. | 0 | 14 tipos mezclados (MLr_3, ML, MLr_vmm, MW, …). |
| `latitude`, `longitude` | num. | 0 | |
| `latitude_error`, `longitude_error` | num. | 4 | Error de localización, hasta 32,5. |
| `depth` | num. | 0 | km; 56 valores negativos (mín. −5), 1 valor > 300 km. |
| `depth_error` | num. | 263 | Valores extremos hasta 1000. |

### Hallazgos de calidad

1. **Localidad (`place`) con variantes de escritura.** 111 cadenas distintas de municipio. Causas
   verificadas: diferencias de mayúsculas (`Palmas Del Socorro` / `Palmas del Socorro`), tildes
   ausentes (`Bolivar` 810 / `Bolívar` 147), 15 formas con mojibake UTF-8 leído como cp1252
   (`GirÃ³n`, `El PlayÃ³n`, `VÃ©lez`, `El PeÃ±Ã³n`, `Santa Helena del OpÃ³n`, …; reparables con
   `s.encode("cp1252").decode("utf-8")`), y 2 alias de nombre (`El Carmen` = `El Carmen De Chucurí`,
   `Jordán Sube` = `Jordán`).
   Recuento verificado: **111 formas → 89 tras reparar y normalizar → 87 tras unir los 2 alias.**
   La unión de alias es una hipótesis razonable, no una verdad oficial: **pendiente** confirmar
   contra el código DIVIPOLA del DANE (que además fija el número oficial de municipios) antes de
   usarla como clave de integración.
2. **`local_time` mal etiquetada**: siempre difiere de `utc_time` en exactamente 5 h con sufijo `+00:00`.
   Usar solo `utc_time`.
3. **Duplicados**: 0 por `id`; 3 pares con los mismos `utc_time`, coordenadas, magnitud y profundidad,
   pero `id` consecutivos distintos (2026-06-14, 2026-07-22, 2026-09-13). Probables registros dobles;
   decisión de eliminación **pendiente** en la limpieza.
4. **Concentración geográfica extrema**: Los Santos concentra el 56 % de los eventos (103 547) y
   Zapatoca el 11 % (20 426). El 95,4 % de los eventos tiene profundidad ≥ 100 km (nido sísmico
   de Bucaramanga). Solo el 2,19 % es superficial (< 30 km) y esos eventos se ubican sobre todo en
   Puerto Parra, La Belleza, Cimitarra, Puerto Wilches y Barrancabermeja.
5. **Completitud no estacionaria**: eventos por año pasan de ≈2 400–3 100 (2006–2008) a ≈11 000–16 000
   (2019–2025). Con M ≥ 2,5 el conteo anual es mucho más estable (≈680–1 430 en todos los años).
   Es coherente con mejoras de la red de detección, aunque esa interpretación no está verificada
   con documentación del SGC. **Pendiente**: estimar la magnitud de completitud (Mc) antes de
   construir variables de frecuencia.
6. **Escalas de magnitud mezcladas** (`mag_type`): ML y MLr_* dominan; MW/Mw(mB) son pocos (≈2 600).
   Se tratarán como una sola magnitud aproximada y se documentará la limitación.
7. **Escasez por municipio**: tras normalizar, la mayoría de municipios tiene pocos eventos por año;
   la agregación temporal y el umbral de magnitud condicionan cuántos ejemplos útiles hay.

### Resultado de la limpieza (`python -m src.data.preprocessing`)

Salida: `data/processed/eventos_santander_limpio.csv.gz` (determinista) y
`data/processed/limpieza_reporte.json` (todos los conteos).

| Concepto | Resultado real |
|---|---|
| Filas originales → limpias | 184 725 → **184 722** |
| Descartes por invalidez (campos vacíos, coordenadas, magnitud, profundidad) | 0 |
| Duplicados por `id` | 0 |
| Duplicados de evento (mismo instante, posición, magnitud y profundidad) | 3 eliminados: `SGC2026lpjrpw`, `SGC2026ohnsbr`, `SGC2026sbueng` (se conserva el menor `id`) |
| Eventos fuera de Santander | 0 |
| Municipios | 111 formas → **87** tras reparar mojibake, normalizar y unir 2 alias |
| Nulos conservados (no se imputan aquí) | `magnitude_error` 79 091 · `depth_error` 263 · `latitude_error` 4 · `longitude_error` 4 · `gap` 1 |
| Valores extremos conservados y marcados | `flag_profundidad_negativa` 56 · `flag_error_profundidad_extremo` (> 100 km) 23 |
| Columna descartada | `local_time` (mal etiquetada) |

Los valores atípicos por la regla de Tukey (p. ej. 9 905 en magnitud, 20 270 en profundidad) son
**descriptivos**: se conservan porque son eventos sísmicos válidos.

## Completitud y ruptura estructural del catálogo (`python -m src.data.completeness`)

Magnitud de completitud por año (MAXC + 0,2) en `data/processed/mc_por_anio.csv`:

| Periodo | Mc (rango anual) | `nst` mediano | Tipo de magnitud dominante | Valor b |
|---|---|---|---|---|
| 2006–2008 | 2,2 – 2,5 | 5–6 | ML | ≈ 0,78–0,89 |
| 2009–2017 | 1,6 – 2,0 | 6–8 | ML (y MW en 2012–2017, ≈ 230–860/año) | ≈ 0,80–0,91 |
| 2018–2026 | 1,8 – 2,0 | 10–16 | MLr_3 y MLr_vmm | ≈ 1,06–1,24 |

Hechos verificados en los datos:

1. **2018 es una ruptura**: el tipo de magnitud pasa de ML (hasta 2017) a MLr_3/MLr_vmm; la mediana
   de `nst` se duplica (7 → 14); el valor b sube de ≈ 0,85 a ≈ 1,15.
2. **Antes de 2009 el catálogo es menos completo** (Mc hasta 2,5). Un umbral de M ≥ 2,0 no es
   válido para 2006–2008.
3. **M ≥ 2,5 es completo en todos los años** (Mc máx. anual 2,5) y deja 84 de 87 municipios con
   al menos un evento; M ≥ 3,0 deja 67.
4. Mc global: 1,9; b global: 0,97.

Interpretaciones **no verificadas con documentación del SGC**: que el cambio de 2018 corresponda a
un cambio de método o de red. Los datos solo muestran que el catálogo no es homogéneo.

Consecuencias para el diseño (propuestas, por confirmar):
- Variables de frecuencia con umbral **M ≥ 2,5** (sensibilidad con M ≥ 2,0 desde 2009).
- Preferir variables relativas (proporciones, rangos) a conteos brutos de eventos pequeños.
- División temporal con datos de **ambos regímenes** en entrenamiento (no entrenar solo con
  2006–2017 y evaluar en 2018+, porque cambia la distribución de entrada).
- `nst` y `mag_type` son indicadores de régimen de la red; si se usan como variables, hay que
  justificar que no codifican simplemente el año.

## 2. Amenaza sísmica oficial del SGC (segunda fuente) — incorporada

**Acceso.** `amenazasismica.sgc.gov.co` **no es accesible**: Chrome muestra `ERR_CERT_DATE_INVALID`
con HSTS (certificado vencido en el servidor del SGC) y el navegador integrado rechaza la
navegación. No se elude la advertencia. El mismo estudio se publica en un visor ArcGIS que sí
responde: `https://srvags.sgc.gov.co/jsviewer/Amenaza_Sismica_2020/`, respaldado por el servicio
`https://srvags.sgc.gov.co/arcprod/rest/services/Amenaza_Sismica/Amenaza_Sismica/MapServer`
("Amenaza Sismica 2020", capacidades Map, Query, Data; también WMS).

**Contenido.** 22 capas **ráster** (no vectoriales): PGA [g], Sa(0,2) y Sa(1,0) para cinco periodos
de retorno (31, 225, 475, 975 y 2 475 años), más "Intensidad Máxima Observada" e "Intensidad
Sísmica Esperada". Las consultas por atributos no aplican; sí funciona `identify` (valor del píxel
en un punto).

**Muestreo de prueba (en memoria, 2026-10-13).** Valor de cada capa en la cabecera de los 87
municipios (coordenadas DIVIPOLA): 87/87 sin nulos. PGA Tr=475: mín. 0,198 g, mediana 0,238 g,
máx. 0,279 g (mayores: El Carmen de Chucurí, Sabana de Torres, El Playón; menores: Albania,
Gámbita, Puente Nacional). Intensidad esperada: solo valores 6 y 7.

**Limitaciones verificadas o por verificar:**
1. Mapa **estático** (2020): no varía en el tiempo y no es "conocimiento previo" para 2006–2019.
   El corte del catálogo con el que se calibró **no está verificado**; no es independiente de los
   eventos que usamos.
2. Se muestrea en la **cabecera municipal**, no el promedio del área del municipio.
3. Rango estrecho: todo Santander está en amenaza alta; poca capacidad de discriminar.
4. Las capas PGA/Sa de distintos periodos de retorno son casi colineales: cuentan como 1–2
   variables, no como 5 (no inflar el mínimo de 20).
5. **Excluir "Intensidad Máxima Observada"** como variable de entrada: resume efectos de sismos
   pasados y puede filtrar información de los periodos que se evalúan.
6. Licencia de uso del SGC: **no verificada**; citar la fuente.

## 3. DANE — DIVIPOLA (división político-administrativa) — incorporada

Conjunto "DIVIPOLA - Municipios Santander" en datos.gov.co (id `kyaq-ecfy`, DANE, licencia CC BY-SA 4.0):
87 filas con `cod_mpio`, `nom_mpio`, `longitud`, `latitud` (decimal con coma).

**Cruce con el catálogo verificado:** los 87 nombres normalizados del catálogo coinciden 1 a 1 con
los 87 de DIVIPOLA (0 sin pareja en ambos sentidos). Eso confirma los dos alias supuestos:
`El Carmen` → `El Carmen de Chucurí` y `Jordán Sube` → `Jordán` (las claves `el carmen` y
`jordan sube` no existen en DIVIPOLA).

La población municipal se documenta en la sección 5.

## 4. Integración de las fuentes (`python -m src.data.integration`)

Archivos crudos descargados el 2026-10-13 con `python -m src.data.acquisition` (no sobrescribe):

| Archivo | Fuente | Contenido |
|---|---|---|
| `data/raw/divipola_municipios_santander.csv` | DANE, datos.gov.co `kyaq-ecfy` | 87 filas, tal como se publica (coma decimal) |
| `data/raw/sgc_amenaza_2020_cabeceras.csv` | SGC, MapServer `Amenaza_Sismica`, operación `identify` | 87 filas × 8 capas; incluye coordenadas usadas y `fecha_consulta_utc` |

Salida: `data/processed/municipios_santander.csv` (una fila por municipio: código, nombre oficial,
coordenadas, 8 valores de amenaza y n.º de eventos) y `data/processed/integracion_reporte.json`.

Reglas de unión (validadas en código, ver `src/data/integration.py`):
- catálogo → DIVIPOLA por `municipio_key` (muchos a uno);
- DIVIPOLA → amenaza por `cod_mpio` (uno a uno).
La unión falla si pierde o duplica filas, si hay códigos sin pareja o si falta algún valor.

Resultado real:

| Comprobación | Resultado |
|---|---|
| Municipios | 87 (DIVIPOLA = catálogo = amenaza) |
| Eventos con municipio oficial | 184 722 de 184 722 (0 perdidos, 0 duplicados) |
| Municipios sin eventos | 0; con menos de 30 eventos: 10 |
| Compatibilidad geográfica | Para el 89,03 % de los eventos, el municipio de `place` es la cabecera DIVIPOLA más cercana al epicentro. Distancia a la cabecera propia: mediana 7,3 km, p90 12,5 km, máx. 87,5 km |
| Compatibilidad temporal | Amenaza = mapa estático 2020; catálogo 2006–2026 |
| Compatibilidad metodológica | Amenaza muestreada en la cabecera, no el área |

Interpretación de `place`: es coherente con "municipio más cercano o que contiene el epicentro";
sin polígonos municipales no se puede distinguir entre ambas. El 11 % restante puede deberse a
municipios extensos con cabecera descentrada. No se afirma más.

Redundancia entre capas de amenaza (correlación con PGA Tr=475): PGA Tr=225 0,995 · Tr=975 0,994
· Sa(0,2) 0,997 · Tr=2 475 0,955 · Tr=31 0,928 · Sa(1,0) 0,870. En consecuencia se tratarán como
**1–2 variables independientes**, no 8. La correlación entre PGA Tr=475 y log(1 + n.º de eventos)
por municipio es 0,35: la amenaza oficial y la actividad histórica comparten información, pero
no son lo mismo.

## 5. Población municipal (DANE) — incorporada

**Fuente:** proyecciones de población municipal por área geográfica, basadas en el Censo 2018,
publicadas por el DANE en https://www.dane.gov.co/ (sección Proyecciones de población). Descargadas
el 2026-10-13 con `python -m src.data.acquisition` (no sobrescribe):

| Archivo (`data/raw/`) | Hoja usada | Cobertura | Tamaño | SHA256 (inicio) |
|---|---|---|---|---|
| `DCD-area-proypoblacion-Mun-2005-2017_VP.xlsx` | `NuevaMpal` | 2005–2017 | 1,53 MB | `0D7E6B896955F37E…` |
| `PPED-AreaMun-2018-2042_VP.xlsx` | `PobMunicipalxÁrea` | 2018–2042 | 3,77 MB | `1EA83594AD308BEC…` |

Formato largo (departamento, municipio, año, área, población); el orden de columnas difiere entre
libros y el encabezado está en filas distintas, por lo que el lector detecta la fila `DP`.
Áreas: `Cabecera Municipal`, `Centros Poblados y Rural Disperso` y `Total`.

**Procesamiento** (`python -m src.data.population`): se filtra el departamento 68, se normaliza el
área y se genera `data/processed/poblacion_municipal_anual.csv` (una fila por municipio y año,
2005–2026) y `data/processed/poblacion_reporte.json`.

Resultado real:

| Comprobación | Resultado |
|---|---|
| Cobertura | 87 municipios × 22 años = 1 914 filas, rejilla completa, 0 nulos |
| Códigos frente a DIVIPOLA | 87 de 87, sin sobrantes en ningún sentido |
| Coherencia aritmética | `total = cabecera + rural` en las 1 914 filas (diferencia máxima 0) |
| Continuidad entre series (2017 → 2018) | Total Santander +1,75 %; por municipio de −2,7 % a +2,9 %; ningún municipio con salto > 10 % |

**Limitaciones:**
1. Son **proyecciones**, no conteos: los años posteriores al censo de 2018 (hasta 2026) son
   estimaciones y se revisan en cada actualización del DANE.
2. La población es un indicador de **exposición** (cuántas personas habitan una zona), no de
   amenaza ni de vulnerabilidad estructural.
3. Se usa el **total municipal**; no distingue la población realmente cercana a los epicentros.
4. Sin información de viviendas, edificaciones ni calidad constructiva.
5. Las dos series se construyeron en momentos distintos; aunque no hay saltos grandes en 2017–2018,
   la continuidad es una verificación empírica, no una garantía metodológica.
