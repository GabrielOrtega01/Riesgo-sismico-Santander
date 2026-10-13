# Riesgo sísmico de Santander

Análisis y priorización **exploratoria** de la actividad sísmica histórica de Santander (Colombia)
mediante Machine Learning supervisado y aprendizaje por refuerzo. Proyecto académico (UTS).

> **Alcance y limitaciones.** Este proyecto **no predice** la fecha, ubicación ni magnitud de
> futuros terremotos y **no es** una evaluación oficial del riesgo de desastres. Las categorías
> (Básico, Medio, Avanzado) son una clasificación exploratoria propia del proyecto.

## Estado

En desarrollo. Etapa 1 (diagnóstico y planificación) completada; la estructura del repositorio
está creada y los datos aún no se han descargado.

## Instalación

Requiere Python 3.14 (probado con 3.14.5) en Windows.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Datos

La fuente principal es el catálogo del Servicio Geológico Colombiano (https://sgc.gov.co/catalogo).
La exportación se recibe por correo y debe colocarse manualmente en `data/raw/` sin modificarla.

## Pruebas

```powershell
pytest
```

## Estructura

Ver [CLAUDE.md](CLAUDE.md) para la descripción de carpetas, el reparto de responsabilidades y las
decisiones metodológicas pendientes.
