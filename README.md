# Seismox · Riesgo sísmico de Santander

Análisis y priorización **exploratoria** de la actividad sísmica histórica de Santander (Colombia)
mediante Machine Learning supervisado y aprendizaje por refuerzo. Proyecto académico (UTS).

**Aplicación web:** https://seismox.streamlit.app/ (dirección prevista; ver «Aplicación» para
publicarla).

> **Alcance y limitaciones.** Este proyecto **no predice** la fecha, ubicación ni magnitud de
> futuros terremotos y **no es** una evaluación oficial del riesgo de desastres. Las categorías
> (Básico, Medio, Avanzado) son una clasificación exploratoria propia del proyecto.

## Estado

| Componente | Estado |
|---|---|
| Datos: catálogo SGC, limpieza y completitud | Implementado y probado |
| Segunda fuente: DIVIPOLA (DANE) y amenaza sísmica 2020 (SGC), integración | Implementado y probado |
| Aplicación Streamlit (inicio explicativo, zonas, mapa, comparación, calidad de datos, fuentes, glosario) | Implementada y probada |
| Población municipal (DANE, proyecciones 2005–2026) | Implementado y probado |
| Panel municipio × año y diccionario de 23 variables | Implementado y probado |
| Etiquetas (Básico / Medio / Avanzado) | Pendiente |
| Clasificador supervisado | Pendiente |
| Agente de aprendizaje por refuerzo y priorización | Pendiente |

La aplicación no muestra resultados de clasificación ni de priorización hasta que existan los
modelos entrenados.

## Instalación

Probado con Python 3.14 en Windows.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Reproducir los datos procesados

El catálogo original (`data/raw/sgc_catalogo_santander_20060101_20261013.csv`) y las fuentes
complementarias ya están en el repositorio. Para regenerar todo lo procesado:

```powershell
python -m src.data.preprocessing   # limpieza del catálogo
python -m src.data.completeness    # magnitud de completitud por año
python -m src.data.integration     # unión con DIVIPOLA y amenaza sísmica
python -m src.data.population      # población municipal por año (DANE)
python -m src.data.features        # panel de variables y diccionario
```

El catálogo se obtiene de https://sgc.gov.co/catalogo (la exportación llega por correo).
`python -m src.data.acquisition` vuelve a descargar DIVIPOLA y la amenaza (no sobrescribe datos
crudos). Detalle y limitaciones de cada fuente en [docs/fuentes_datos.md](docs/fuentes_datos.md).

## Aplicación

```powershell
streamlit run src/app.py
```

**Publicación en Streamlit Community Cloud** (la hace el propietario del repositorio):
1. Entrar a https://share.streamlit.io con la cuenta de GitHub y elegir **Create app**.
2. Repositorio `GabrielOrtega01/Riesgo-sismico-Santander`, rama `main`, archivo principal `src/app.py`.
   En **App URL** escribir `seismox` (queda `seismox.streamlit.app`); el formulario indica si el
   nombre está disponible.
3. En *Advanced settings*, elegir una versión de Python soportada por la plataforma (3.11 a 3.13).
   Las 84 pruebas del proyecto se ejecutaron con éxito en Python 3.11.9 y 3.14.
4. La aplicación lee solo archivos del repositorio; no requiere secretos ni acceso a internet.

## Pruebas

```powershell
pytest
```

## Estructura

Ver [CLAUDE.md](CLAUDE.md) para la descripción de carpetas, el reparto de responsabilidades y las
decisiones metodológicas pendientes.
