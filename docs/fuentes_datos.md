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
| `place` | texto | 0 | Formato `Municipio - Departamento, Colombia`. Se interpreta como localidad de referencia; **no verificado** si es el municipio que contiene el epicentro o el más cercano. |
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

## 2. Amenaza sísmica oficial (segunda fuente candidata)

**Pendiente.** `amenazasismica.sgc.gov.co` dio error SSL desde este equipo (2026-10-13). Otros
puntos referenciados por el SGC: `srvags.sgc.gov.co/jsviewer/Amenaza_Sismica_2020`. Debe
verificarse si ofrece datos descargables por municipio.

## 3. DANE (población / división político-administrativa)

**Pendiente.** Candidatos: proyecciones de población municipal, Censo 2018 y el código DIVIPOLA
como clave oficial de municipio.
