# Guion de la presentación (10 minutos + 3 de preguntas)

**Equipo:** Bucara Hackers · Juan Jose Perucho Quintero · Gabriel Augusto Ortega Martínez
**Proyecto:** Seismox · Nivel Avanzado · https://seismox.streamlit.app/

La presentación en láminas tiene 14 láminas con notas del orador. Orden de exposición: **primero
Juan Jose, después Gabriel.**

| Lámina | Quién | Mensaje | Tiempo |
|---|---|---|---|
| 1 Portada | Juan Jose | «Somos Bucara Hackers y les vamos a presentar nuestro proyecto: Seismox» | 0:30 |
| 2 El problema | Juan Jose | 184 722 sismos, 87 municipios, 95 % profundos; la pregunta | 0:45 |
| 3 Datos oficiales | Juan Jose | SGC (catálogo y amenaza) y DANE; 87 municipios sin perder ningún sismo | 0:45 |
| 4 Hallazgo | Juan Jose | El catálogo cambió en 2018; usamos magnitud ≥ 2,5 | 0:45 |
| 5 Variables | Juan Jose | 23 variables, sin mirar al futuro (prueba automática) | 0:45 |
| 6 Básico | Gabriel | Clasificador Bajo/Medio/Alto: 75,3 % frente a 73,6 % | 1:00 |
| 7 Medio | Gabriel | K-means: 6 grupos territoriales | 0:45 |
| 8 Avanzado | Gabriel | Agente: observa, decide, aprende | 1:00 |
| 9 Resultados | Gabriel | De 0,11 al azar a 0,90; competitivo con las reglas simples y por qué | 1:00 |
| 10 Demostración | Los dos | Juan Jose conduce la app y Gabriel comenta | 1:30 |
| 11 Límites | Gabriel | Lo que Seismox no hace | 0:45 |
| 12 Preguntas | Los dos | Respuestas preparadas | respaldo |
| 13 Qué sigue | Juan Jose | Cuatro pasos, cada uno responde a un límite declarado | 0:30 |
| 14 Cierre | Los dos | Tres niveles cumplidos; gracias | 0:30 |

## Respuestas preparadas (lámina 12)

- **¿Predice terremotos?** No. Clasifica la actividad histórica esperada del año siguiente, evaluada con años que no vio.
- **¿Hay fuga de información?** No: división temporal, umbrales ajustados con datos de entrenamiento, variables solo con años previos y una prueba automática que lo verifica.
- **¿Por qué magnitud 2,5?** Es el umbral completo en todos los años; con 2,0, los años 2006 a 2008 no son comparables.
- **¿Por qué la mejora es modesta?** La actividad de un municipio se repite mucho de un año a otro; repetirla ya es una regla fuerte.
- **¿Qué aporta el agente?** Una política que combina categoría, actividad, amenaza y población; en el protocolo secuencial llega a 0,90 frente a 0,81 de la mejor regla fija.
- **¿Se puede reproducir?** Sí: fuentes con dirección y fecha, comandos en el repositorio y 115 pruebas automáticas.

## Plan B de la demostración

Si no hay internet o la página no carga: ejecutar localmente con `streamlit run src/app.py` desde la
carpeta del proyecto (los datos y los modelos ya están en el repositorio).
