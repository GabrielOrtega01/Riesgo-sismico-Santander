# Explicación de cada lámina de Seismox

Guía para exponer con más información. Cada lámina trae: **qué muestra**, **qué decir**, **datos de
respaldo** (todos verificados en el repositorio) y **qué responder si preguntan**.

**Equipo:** Bucara Hackers · Juan Jose Perucho Quintero (láminas 1 a 7) y Gabriel Augusto Ortega
Martínez (láminas 8 a 14) · **Aplicación:** https://seismox.streamlit.app/

---

## Antes de empezar

### Tres frases que resumen el proyecto
1. Con datos oficiales del SGC y del DANE, **clasificamos** cada municipio de Santander según su actividad sísmica esperada y **priorizamos** qué zonas revisar primero.
2. Cumplimos los tres niveles del reto: supervisado (Básico), no supervisado (Medio) y refuerzo (Avanzado).
3. **Medimos todo contra una referencia sencilla y decimos con claridad dónde ganamos y dónde no.**

### Vocabulario mínimo
| Término | Qué significa, dicho fácil |
|---|---|
| Magnitud | Qué tan fuerte es un sismo (cada punto es unas 32 veces más energía) |
| Profundidad | A cuántos km bajo la superficie ocurre |
| M ≥ 2,5 | Sismos de magnitud 2,5 o más; el umbral que el catálogo registra completo en todos los años |
| PGA | Aceleración del suelo esperada; mayor valor, sacudida esperada más fuerte |
| Amenaza / exposición / vulnerabilidad | Qué tan fuerte puede sacudir / cuánta gente hay / qué tan frágil es lo construido. **Solo medimos las dos primeras** |
| Persistencia (línea base) | La regla más simple: «el año siguiente será igual que este» |
| Validación temporal | Entrenar con años pasados y probar con años posteriores que el modelo nunca vio |
| Fuga de información | Que el modelo «vea» el futuro sin querer; la evitamos y hay una prueba automática |
| K-means | Algoritmo que agrupa municipios parecidos sin usar etiquetas |
| Índice de silueta | De −1 a 1: qué tan separados quedan los grupos (el nuestro es 0,21: bajo) |
| Q-learning | Aprendizaje por refuerzo: el agente aprende por ensayo y error qué decisiones dan mejor recompensa |
| Utilidad | Parte de la actividad y de la población del año siguiente que queda en las zonas elegidas |

### Lo que nunca hay que decir
- ❌ «Predice terremotos» → ✅ «clasifica la actividad histórica esperada del año siguiente».
- ❌ «Evalúa el riesgo» → ✅ «análisis exploratorio; no es una evaluación oficial».
- ❌ «El agente es mejor que todo» → ✅ «aprende y es competitivo con las mejores reglas simples».

---

## 1 · Portada — *Juan Jose* (30 s)

**Qué muestra.** El nombre del proyecto (Seismox), el equipo (Bucara Hackers), el nivel (Avanzado) y la dirección pública.

**Qué decir.** «Buenas tardes. Somos Bucara Hackers y les vamos a presentar nuestro proyecto: Seismox. Es una herramienta que clasifica y prioriza zonas de Santander según su actividad sísmica, con datos oficiales. Yo les cuento el problema y los datos; Gabriel les cuenta los modelos.»

**Si preguntan.** *¿Qué significa Seismox?* Es el nombre que elegimos para el proyecto; no tiene un significado técnico.

---

## 2 · El problema — *Juan Jose* (45 s)

**Qué muestra.** Cuatro cifras: 184 722 sismos, 87 municipios, 95 % a más de 100 km de profundidad y magnitud máxima 6,4.

**Qué decir.** «Santander es uno de los departamentos con mayor actividad sísmica de Colombia. En 20 años el catálogo del SGC registra 184 722 sismos en 87 municipios. Casi todos son pequeños y muy profundos: el 95 % ocurre a más de 100 km, por el nido sísmico de Bucaramanga. Con tantos datos, la pregunta es: ¿qué zonas conviene vigilar primero?»

**Datos de respaldo.**
- Catálogo: del 2006-01-01 al 2026-10-13. El archivo original trae 184 725 filas; quedan **184 722** tras eliminar 3 registros duplicados.
- **Los Santos concentra el 56 %** de todos los sismos (103 545) y Zapatoca el 11 %.
- Mayor magnitud: 6,4 (marzo de 2015, Los Santos, a 165 km de profundidad).
- Solo el 2,2 % de los sismos es superficial (< 30 km).

**Si preguntan.** *¿Por qué casi todos son profundos?* Porque el catálogo está dominado por el nido sísmico de Bucaramanga, una zona de sismicidad intermedia muy activa (lo menciona el propio reto).

---

## 3 · Así se ve Seismox (inicio) — *Juan Jose* (20 s)

**Qué muestra.** La pantalla de inicio de la aplicación: qué es, cómo funciona y qué no es.

**Qué decir.** «Antes de entrar en los detalles, así se ve el producto. La página de inicio explica en lenguaje sencillo el problema, los tres pasos del proyecto y, de entrada, aclara que no predice terremotos.»

**Datos de respaldo.** Aplicación en Streamlit, publicada en seismox.streamlit.app; 10 secciones en el menú (inicio, zona, mapa, comparar, grupos, clasificación, priorización, calidad de datos, fuentes y glosario).

---

## 4 · Datos oficiales — *Juan Jose* (45 s)

**Qué muestra.** Tres fuentes y la frase «87 municipios integrados sin perder ni duplicar un solo sismo».

**Qué decir.** «Usamos tres fuentes oficiales. Del SGC, el catálogo sísmico y su estudio de amenaza sísmica 2020. Del DANE, el código oficial de cada municipio y la población proyectada año por año. Las unimos por municipio y comprobamos que cada sismo quedara en su municipio, sin perder ni duplicar ninguno.»

**Datos de respaldo.**
| Fuente | Qué aporta | Detalle |
|---|---|---|
| SGC · catálogo | Cada sismo: fecha, lugar, magnitud, profundidad | sgc.gov.co/catalogo; exportación del 2026-10-13; filtro Santander, 2006–2026 |
| SGC · amenaza sísmica 2020 | PGA y otras variables en la cabecera de cada municipio | Servicio ArcGIS del SGC; 8 capas muestreadas en 87 puntos |
| DANE · DIVIPOLA | Código oficial y ubicación de cada municipio | datos.gov.co, conjunto `kyaq-ecfy` |
| DANE · proyecciones | Población 2005–2026 por municipio | Dos libros Excel; sin saltos en el empalme 2017→2018 (+1,75 %) |

- Los nombres de municipio venían escritos de **111 formas** distintas; tras repararlos quedaron **87**, que coinciden uno a uno con DIVIPOLA.
- El municipio asignado a cada sismo es la cabecera más cercana al epicentro en el **89 %** de los casos.

**Si preguntan.** *¿Por qué no usaron polígonos municipales?* No estaban disponibles en el tiempo del reto; usamos la cabecera como punto (limitación declarada).

---

## 5 · El catálogo cambió en 2018 — *Juan Jose* (45 s)

**Qué muestra.** Dos tarjetas: todos los sismos (2 400 → 16 000 por año) frente a los de magnitud ≥ 2,5 (700 a 1 400 por año, estable).

**Qué decir.** «Al revisar los datos vimos que el número de sismos por año se multiplica por seis. No es que Santander tiemble más: la red detecta más eventos pequeños. Hacia 2018 además cambia el tipo de magnitud. Por eso contamos solo sismos de magnitud 2,5 o más, que son estables en todos los años. Sin esta corrección, un modelo habría aprendido el año en vez de la actividad sísmica.»

**Datos de respaldo.**
- 2006–2008: 2 400 a 3 100 sismos por año. 2019–2025: 11 000 a 16 000.
- Con M ≥ 2,5: entre 677 y 1 426 por año en **todos** los años.
- Hacia 2018: el tipo de magnitud pasa de ML a MLr_3/MLr_vmm; la mediana de estaciones por evento pasa de 7 a 14; el valor b sube de ≈ 0,85 a ≈ 1,15.
- Magnitud de completitud (Mc) por año: entre 1,6 y 2,5.

**Si preguntan.** *¿Por qué cambió?* Los datos muestran que el catálogo cambia de régimen; **no verificamos con documentación del SGC** la causa exacta (probablemente densidad de la red y método de magnitud). Es una inferencia, y así la tratamos.

---

## 6 · 23 variables sin mirar al futuro — *Juan Jose* (45 s)

**Qué muestra.** Siete grupos de variables y el total de 23.

**Qué decir.** «Construimos 23 variables en siete grupos; el reto Avanzado pide al menos 20. Describen cuántos sismos hay, qué tan fuertes y profundos son, qué tan bien se localizaron, la amenaza oficial, la geografía y cuánta gente vive allí. Y algo importante: cada variable usa solo información hasta ese año. Una prueba automática lo verifica.»

**Datos de respaldo.**
| Grupo | N.º | Ejemplos |
|---|---|---|
| Frecuencia | 4 | sismos M ≥ 2,5 del año; promedio anual previo; cambio respecto al año anterior; sismos en municipios vecinos (≤ 50 km) |
| Magnitud | 4 | máxima del año; media; máxima histórica; % de M ≥ 3 |
| Profundidad | 3 | mediana; % superficiales; dispersión |
| Calidad de localización | 5 | estaciones por evento; hueco azimutal; errores horizontal y de profundidad; residuo RMS |
| Amenaza oficial | 3 | PGA (Tr = 475 años); intensidad esperada; forma del espectro |
| Geografía | 1 | distancia a Los Santos |
| Exposición | 3 | población (log); % en cabecera; crecimiento |

- Descartamos 2 variables por redundancia (correlación de Spearman de 0,998 y 0,953).
- **3 variables siguen al año** (estaciones por evento y los dos errores de localización): reflejan el cambio de red. El mejor modelo se entrenó **sin ellas**, con 20 variables, y no perdió desempeño.
- Panel: 87 municipios × 20 años = 1 740 filas; 1 392 filas con historia y etiqueta para modelar (2009–2024).

**Si preguntan.** *¿Cómo evitan la fuga de información?* División temporal, umbrales de las etiquetas ajustados solo con años de entrenamiento, variables históricas con años estrictamente anteriores y la prueba `test_no_future_leakage`, que agrega eventos futuros y comprueba que las variables pasadas no cambian.

---

## 7 · Explorar una zona (pantallazo) — *Juan Jose* (40 s)

**Qué muestra.** La pantalla de Bucaramanga: frase explicativa, indicadores de actividad, amenaza oficial, población y gráficos.

**Qué decir.** «Esta es la pantalla de un municipio, aquí Bucaramanga. Arriba, una frase en lenguaje claro: 224 sismos en 20 años, 17 de magnitud 2,5 o más, puesto 35 de 87, casi todos muy profundos. Debajo, la actividad registrada y, en otra fila, la amenaza oficial del SGC y la población del DANE. Cualquier persona entiende un municipio sin ser experta.»

**Datos de respaldo (Bucaramanga).** 224 sismos; 17 con M ≥ 2,5; magnitud máxima 4,2; profundidad típica 147 km; PGA esperada 0,263 g; intensidad esperada 6; 618 548 habitantes (proyección 2026); 9,8 % de sismos superficiales.

**Cierre del bloque.** «Hasta aquí los datos. Gabriel les cuenta ahora los modelos.»

---

## 8 · Nivel Básico: clasificación — *Gabriel* (60 s)

**Qué muestra.** Las tres categorías con su definición y la tabla de resultados.

**Qué decir.** «Nivel Básico: un modelo supervisado clasifica cada municipio en Bajo, Medio o Alto para el año siguiente, según cuántos sismos de magnitud 2,5 o más habrá. Lo evaluamos con años que el modelo nunca vio, 2023 y 2024, y acierta el 75,3 %. Para saber si es bueno lo comparamos con la regla más simple, repetir el año actual, que acierta el 73,6 %. Es una mejora real pero modesta, porque la actividad sísmica es muy persistente, y lo decimos.»

**Datos de respaldo.**
- **Definición:** Bajo = ningún sismo M ≥ 2,5; Medio = de 1 a 3; Alto = más de 3. Si el mayor sismo del año es ≥ 4,1, la categoría sube un nivel. Umbrales ajustados **solo con años de entrenamiento**.
- **Modelo:** Random Forest (300 árboles), con 20 variables. Se comparó contra regresión logística.
- **Años:** entrenamiento ≤ 2020 (1 044 filas); validación 2021–2022 (174); prueba 2023–2024 (174).
- **Prueba:** exactitud 75,3 %, F1 macro 0,755. Persistencia: 73,6 % y 0,733. Clase mayoritaria: 56,3 % y 0,240.
- **Matriz de confusión (prueba):** Bajo 76 acertados y 22 clasificados como Medio; Medio 35 acertados; Alto 20 acertados de 23. **Ningún Alto se confundió con Bajo.**
- Por clase: Alto con precisión 0,80 y recall 0,87; Medio es la más difícil (precisión 0,58, recall 0,66).

**Si preguntan.** *¿Por qué solo 1,7 puntos más que la persistencia?* Porque la actividad de un municipio se repite mucho de un año a otro; es la regla más fuerte. Con 174 casos de prueba, esa diferencia no es concluyente, y por eso la presentamos como «modesta».

---

## 9 · Clasificación en la aplicación (pantallazo) — *Gabriel* (40 s)

**Qué muestra.** La pantalla de clasificación: categoría y probabilidades por municipio.

**Qué decir.** «En la aplicación el usuario elige un año y ve la categoría esperada del año siguiente para cada municipio, con su probabilidad. Más abajo están las métricas, la matriz de confusión y las variables que más pesan. Todo es verificable en pantalla.»

**Datos de respaldo.** Para el año 2025 (categoría esperada para 2026) los municipios con mayor probabilidad de «Alto» son Santa Helena del Opón, Los Santos, El Carmen de Chucurí, Zapatoca y El Playón. Variables que más pesan: promedio anual previo, sismos M ≥ 2,5 del año y magnitud máxima.

---

## 10 · Nivel Medio: grupos territoriales — *Gabriel* (45 s)

**Qué muestra.** La explicación de K-means y la tabla de los 6 grupos.

**Qué decir.** «Nivel Medio: aprendizaje no supervisado. Sin darle etiquetas, el algoritmo K-means agrupa los municipios que se parecen en actividad sísmica, amenaza y población. Encontró 6 grupos. El grupo 1 es solo Los Santos, que concentra más de la mitad de los sismos; los demás van de actividad moderada a casi nula. El mapa está en la aplicación.»

**Datos de respaldo.**
| Grupo | Municipios | Sismos M ≥ 2,5 por año (promedio) |
|---|---|---|
| 1 | 1 | 706 |
| 2 | 28 | 5,6 |
| 3 | 8 | 3,3 |
| 4 | 22 | 1,2 |
| 5 | 12 | 0,3 |
| 6 | 16 | 0,1 |

- 20 variables (promedio 2009–2025 por municipio), estandarizadas. k elegido por el mejor índice de silueta entre 3 y 6.
- **Silueta 0,21: baja.** Los grupos son una simplificación útil, no fronteras nítidas.

**Si preguntan.** *¿Por qué k entre 3 y 6?* Con k = 2 solo se separa «activo» de «tranquilo», que no ayuda a interpretar el territorio; exigimos al menos 3.

---

## 11 · Grupos en la aplicación (pantallazo) — *Gabriel* (30 s)

**Qué muestra.** El mapa de Santander con cada municipio coloreado por grupo y el perfil medio de cada uno.

**Qué decir.** «Esta es la visualización territorial del nivel Medio. A la izquierda el mapa, un color por grupo; a la derecha el perfil medio de cada uno. El usuario puede elegir un grupo y ver sus municipios.»

---

## 12 · Nivel Avanzado: el agente — *Gabriel* (60 s)

**Qué muestra.** Tres pasos: observa, decide y aprende.

**Qué decir.** «Nivel Avanzado: aprendizaje por refuerzo. Es un agente que aprende por ensayo y error. Cada año se le presentan las zonas una por una; ve la categoría que predijo el clasificador, la actividad reciente, la amenaza y la población, y decide si priorizarla o saltarla, con un presupuesto de 10 zonas. Su recompensa es cuánta actividad y cuánta población del año siguiente quedó en las zonas que eligió. Aquí se integra el clasificador con el agente.»

**Datos de respaldo.**
- **Algoritmo:** Q-learning tabular; 12 000 episodios; tasa de aprendizaje 0,1; exploración que baja de 0,5 a 0,02.
- **Estado:** categoría esperada (3) × actividad del año (3) × amenaza (3) × exposición (3) × presupuesto restante (3 niveles) × mitad del episodio (2) = **486 estados**.
- **Acciones:** priorizar o saltar.
- **Recompensa:** 0,5 × parte de los sismos del año siguiente + 0,5 × parte de la exposición afectada − 0,01 por revisión.
- **Años:** entrenamiento 2012–2020; validación 2021–2022; prueba 2023–2024.
- **Integración:** las probabilidades del clasificador usadas como estado son **fuera de muestra** (modelos reentrenados año por año), para que el agente no vea el futuro.

**Si preguntan.** *¿Por qué Q-learning tabular y no redes profundas?* Con 87 zonas y pocos años, un espacio de 486 estados es pequeño y explicable; una red profunda sobreajustaría y no podríamos explicar la política.

---

## 13 · Resultados del agente — *Gabriel* (60 s)

**Qué muestra.** La tabla de utilidad por estrategia y el salto de 0,11 a 0,90.

**Qué decir.** «La utilidad es la parte de la actividad y de la población del año siguiente que queda en las 10 zonas elegidas; el máximo posible, conociendo el futuro, es 0,954. Elegir al azar da 0,11. Nuestro agente da 0,89, a la par de las reglas simples; repetir la actividad del año da 0,91. En el protocolo secuencial en el que aprendió, pasa de 0,11 con acciones al azar a 0,90 en prueba. Somos claros: aprende y es competitivo, pero no supera de forma consistente a la mejor regla simple, porque la actividad de un municipio se repite mucho de un año a otro.»

**Datos de respaldo.**
| Estrategia (años 2021–2024) | Utilidad |
|---|---|
| Óptimo (conoce el futuro) | 0,954 |
| Repetir la actividad del año | 0,914 |
| Solo el clasificador | 0,904 |
| **Agente de refuerzo** | **0,893** |
| Promedio histórico | 0,883 |
| Al azar | 0,114 |

| Protocolo secuencial | Validación | Prueba |
|---|---|---|
| Agente (política aprendida) | 0,849 | 0,897 |
| Regla fija: actividad alta | 0,899 | 0,809 |
| Aleatoria | 0,111 | 0,108 |

- **Evidencia de aprendizaje:** la recompensa media por episodio pasa de 0,197 (episodio 500) a 0,691 (episodio 12 000); un agente sin entrenar obtiene 0.

**Si preguntan.** *¿Entonces el agente es mejor o no?* Depende del conjunto: en **prueba** supera a la mejor regla fija (0,90 contra 0,81); en **validación** no (0,85 contra 0,90). En el ranking queda a la par de las reglas simples. Con 4 años de evaluación no es concluyente, y así lo reportamos.

---

## 14 · Priorización en la aplicación (pantallazo) — *Gabriel* (45 s)

**Qué muestra.** La lista de las 10 zonas que propone el agente y la comparación con reglas simples.

**Qué decir.** «Este es el producto del nivel Avanzado: la lista de las 10 zonas que el agente propone revisar primero, con su categoría esperada, la actividad reciente y la amenaza. Debajo, la comparación con el azar y con reglas simples en años que no vio, y la explicación de cómo funciona el agente. Es el flujo completo: datos, clasificador, agente y priorización, sin API, como pide el reto.»

**Datos de respaldo (con información hasta 2025).** Orden propuesto: 1 Los Santos, 2 El Carmen de Chucurí, 3 Zapatoca, 4 El Playón, 5 Rionegro, 6 Girón, 7 Jordán, 8 Charalá, 9 Vélez, 10 Mogotes.

**Si preguntan.** *¿Por qué aparecen Charalá y Mogotes si tuvieron pocos sismos?* Porque el valor que aprendió el agente en algunos estados poco frecuentes es ruidoso; con 486 estados y pocos años, esas posiciones tienen más incertidumbre. Es una limitación del enfoque tabular, y la lista de la parte alta (los primeros 7) es la más sólida.

---

## 15 · Demostración en vivo — *Juan Jose conduce, Gabriel comenta* (90 s)

**Ruta sugerida**, con enlaces directos (abren la sección ya cargada):
1. **Inicio** — `https://seismox.streamlit.app/` — qué es y el aviso de que no predice.
2. **Explorar una zona** — `?pagina=zona` — Bucaramanga y luego Los Santos (contraste).
3. **Mapa** y **Grupos** — `?pagina=mapa` y `?pagina=grupos`.
4. **Clasificación** — `?pagina=clasificacion` — año 2025; matriz de confusión.
5. **Priorización** — `?pagina=priorizacion` — las 10 zonas y la comparación.

**Plan B.** Si no hay internet: `streamlit run src/app.py` desde la carpeta del proyecto (datos y modelos están en el repositorio).

**Recomendación.** Abrir la aplicación **antes** de pasar; la primera carga tarda unos segundos. Si pueden, cambien el control «Magnitud mínima» a 3,0 para mostrar que la app responde.

---

## 16 · Lo que Seismox no hace — *Gabriel* (45 s)

**Qué decir.** «Queremos ser claros con lo que no hace. No predice terremotos: clasifica la actividad histórica esperada. No es una evaluación oficial del riesgo. No mide la vulnerabilidad de las construcciones. Y las mejoras de nuestros modelos sobre las referencias simples son modestas. Preferimos medirlo y decirlo que prometer de más.»

**Por qué conviene esta lámina.** El desempate del reto es primero impacto e innovación y luego solidez técnica del componente de ML. Reconocer los límites de forma precisa demuestra solidez técnica y evita que una pregunta del jurado desmonte el proyecto.

---

## 17 · Preguntas frecuentes — *Los dos* (respaldo)

Respuestas en la lámina y ampliación:

| Pregunta | Respuesta ampliada |
|---|---|
| ¿Predice terremotos? | No. Clasifica la actividad histórica esperada del año siguiente (cuántos sismos M ≥ 2,5), evaluada con años que no vio. |
| ¿Hay fuga de información? | No: división temporal, umbrales con datos de entrenamiento, variables solo con años previos y una prueba automática. |
| ¿Por qué magnitud 2,5? | Es el umbral completo en todos los años; con 2,0, los años 2006 a 2008 no son comparables. |
| ¿Por qué la mejora es modesta? | La actividad de un municipio se repite mucho de un año a otro; repetirla ya es una regla fuerte. |
| ¿Qué aporta el agente? | Una política que combina categoría, actividad, amenaza y población. En prueba llega a 0,90 frente a 0,81 de la mejor regla fija; en validación, a 0,85 frente a 0,90. |
| ¿Se puede reproducir? | Sí: fuentes con dirección y fecha, comandos en el repositorio y 115 pruebas automáticas. |

**Preguntas adicionales posibles.**
- *¿Por qué 2026 no está en el entrenamiento?* Es un año parcial (hasta el 13 de octubre); sus conteos no son comparables con años completos. Se muestra en la aplicación pero se excluye de los modelos.
- *¿Por qué K = 10?* Es una decisión de diseño: un presupuesto de revisión de ≈ 11 % de los 87 municipios. La aplicación permite cambiarlo; el agente se entrenó con 10.
- *¿Cuántos datos usó el modelo?* 1 392 municipios-año con historia y etiqueta (2009–2024).
- *¿Qué pasaría con más años?* Es el primer paso de «Qué sigue»: reevaluar con datos nuevos del SGC.

---

## 18 · Qué sigue — *Juan Jose* (30 s)

**Qué decir.** «Sabemos qué mejorar. Primero, evaluar con más años a medida que el SGC publique datos. Segundo, medir la vulnerabilidad, la calidad de las construcciones, que hoy no medimos. Tercero, usar los polígonos de cada municipio en lugar de un punto. Y cuarto, probar agentes más ricos y compararlos con el actual. Cada paso responde a un límite que declaramos.»

---

## 19 · Cierre — *Los dos* (30 s)

**Qué decir.** *Juan Jose:* «Cumplimos los tres niveles: un clasificador supervisado, grupos territoriales no supervisados y un agente de refuerzo integrado con el clasificador.» *Gabriel:* «Con 23 variables, tres fuentes oficiales, 115 pruebas automáticas y una aplicación pública que pueden abrir ahora mismo. Muchas gracias; con gusto respondemos preguntas.»

**Datos de respaldo.** Repositorio: https://github.com/GabrielOrtega01/Riesgo-sismico-Santander · Entregables y fuentes citadas: `docs/entrega.md` · Resultados completos: `docs/resultados.md`.

---

## Reparto del tiempo (≈ 10 minutos)

| Bloque | Quién | Láminas | Tiempo |
|---|---|---|---|
| Problema y datos | Juan Jose | 1–7 | ≈ 4:30 |
| Modelos | Gabriel | 8–14 | ≈ 5:00 |
| Demostración | Los dos | 15 | 1:30 |
| Límites y cierre | Gabriel / Juan Jose / los dos | 16, 18, 19 | ≈ 1:45 |
| Preguntas (3 min) | Los dos | 17 (respaldo) | — |

> Si el tiempo aprieta, se pueden saltar 3 (inicio) y 11 (grupos): sus mensajes ya están en la demostración.
