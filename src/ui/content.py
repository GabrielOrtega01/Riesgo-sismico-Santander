"""Textos de la aplicación en lenguaje claro: menú, glosario, fuentes y limitaciones."""

# ---- menú ----------------------------------------------------------------------------------
PAGE_HOME = "🏠 Inicio"
PAGE_ZONE = "📍 Explorar una zona"
PAGE_MAP = "🗺️ Mapa de Santander"
PAGE_COMPARE = "⚖️ Comparar zonas"
PAGE_CLASS = "🧠 Clasificación"
PAGE_PRIO = "🎯 Priorización"
PAGE_CATALOG = "📊 Calidad de los datos"
PAGE_SOURCES = "📚 Fuentes y límites"
PAGE_GLOSSARY = "❓ Glosario"

PAGES = [PAGE_HOME, PAGE_ZONE, PAGE_MAP, PAGE_COMPARE, PAGE_CLASS, PAGE_PRIO,
         PAGE_CATALOG, PAGE_SOURCES, PAGE_GLOSSARY]

PAGE_HINTS = {
    PAGE_ZONE: "Elige un municipio y mira su actividad sísmica, su amenaza oficial y su población.",
    PAGE_MAP: "Ve de un vistazo dónde se concentran los sismos, la amenaza o la población.",
    PAGE_COMPARE: "Pon varios municipios lado a lado y compáralos año por año.",
}

# ---- glosario --------------------------------------------------------------------------------
GLOSSARY = [
    ("Sismo / evento sísmico",
     "Cada registro del catálogo: un movimiento del terreno detectado por la red del Servicio "
     "Geológico Colombiano. La mayoría son tan pequeños que las personas no los sienten."),
    ("Magnitud",
     "Medida de la energía que libera un sismo en su origen. Por cada punto que sube, la energía "
     "liberada es aproximadamente 32 veces mayor. Los sismos de magnitud 5 o más son poco "
     "frecuentes en este catálogo."),
    ("Profundidad",
     "Distancia desde la superficie hasta el punto donde se origina el sismo, en kilómetros. En "
     "esta aplicación llamamos «superficial» a un evento de menos de 30 km."),
    ("PGA (aceleración máxima del suelo)",
     "Valor esperado de la sacudida más fuerte del terreno, medido en «g» (la gravedad). Un valor "
     "mayor indica sacudidas esperadas más fuertes. Es un dato de amenaza del SGC, no del catálogo."),
    ("Periodo de retorno (Tr)",
     "Cada cuánto tiempo, en promedio, se espera una sacudida que supere cierto nivel. Tr = 475 "
     "años equivale a una probabilidad de 10 % de ser superada en 50 años; Tr = 2 475 años, a 2 %."),
    ("Intensidad sísmica esperada",
     "Grado, en una escala por niveles, de los efectos que se esperan en personas y construcciones. "
     "En Santander el SGC reporta valores de 6 y 7."),
    ("Magnitud de completitud (Mc)",
     "Magnitud mínima por encima de la cual el catálogo registra prácticamente todos los eventos. "
     "Por debajo de ella faltan eventos, y faltan más en los años en que había menos estaciones."),
    ("Amenaza",
     "Qué tan fuerte y qué tan frecuente es la sacudida que se espera en un lugar. Depende de la "
     "geología y de las fuentes sísmicas, no de quién vive allí."),
    ("Exposición",
     "Cuántas personas o bienes están en el lugar. Aquí se mide con la población municipal."),
    ("Vulnerabilidad",
     "Qué tan susceptible a daño es lo que está expuesto (por ejemplo, la calidad de las "
     "construcciones). Esta aplicación no la mide."),
    ("Nido sísmico de Bucaramanga",
     "Zona bajo Santander donde se concentran sismos a unos 150 km de profundidad. Por eso casi "
     "todos los eventos del catálogo son profundos y se registran en municipios como Los Santos "
     "y Zapatoca."),
    ("Clasificación supervisada",
     "Un modelo de aprendizaje automático que aprende de datos históricos a asignar una categoría "
     "(Básico, Medio o Avanzado) a cada municipio."),
    ("Aprendizaje por refuerzo",
     "Un agente que aprende por ensayo y error qué decisiones dan mejores resultados. Aquí "
     "decidirá en qué orden conviene revisar las zonas."),
    ("Persistencia (línea base)",
     "Estrategia sencilla de comparación: suponer que el próximo año una zona será igual que "
     "este. Un modelo solo aporta si supera a esta referencia."),
]

# ---- fuentes -----------------------------------------------------------------------------------
SOURCES = [
    {
        "titulo": "Catálogo sísmico del SGC",
        "entidad": "Servicio Geológico Colombiano",
        "aporta": "Cada sismo registrado en Santander: fecha, ubicación, magnitud y profundidad.",
        "cobertura": "2006-01-01 a 2026-10-13 · 184 722 eventos tras la limpieza",
        "limite": "La red de detección cambió con los años (sobre todo hacia 2018): los conteos de "
                  "sismos pequeños no son comparables entre épocas.",
    },
    {
        "titulo": "Amenaza Sísmica 2020 del SGC",
        "entidad": "Servicio Geológico Colombiano",
        "aporta": "Aceleración esperada del suelo (PGA) y de otras variables, en la cabecera de cada municipio.",
        "cobertura": "Mapa estático de 2020, 87 municipios",
        "limite": "No cambia en el tiempo y casi no distingue entre municipios (todo Santander es de "
                  "amenaza alta).",
    },
    {
        "titulo": "DIVIPOLA y población municipal",
        "entidad": "DANE",
        "aporta": "Código oficial, ubicación de la cabecera y población proyectada de cada municipio.",
        "cobertura": "87 municipios · población 2005–2026 (proyecciones)",
        "limite": "Son proyecciones, no conteos. La población mide exposición, no vulnerabilidad.",
    },
]

LIMITATIONS = [
    "**No predice terremotos.** No dice cuándo, dónde ni de qué tamaño será el próximo sismo.",
    "**No es una evaluación oficial del riesgo.** Es un análisis académico y exploratorio.",
    "**El catálogo no es homogéneo.** Cambia la forma de medir hacia 2018; por eso se compara con "
    "magnitud mínima 2,5.",
    "**El mapa de amenaza es estático** y se muestrea en un punto por municipio.",
    "**Casi todos los sismos son profundos y pequeños.** Eso no implica que no haya sismos "
    "dañinos, solo describe lo que registra el catálogo.",
    "**No se mide vulnerabilidad** (calidad de las construcciones) ni daños reales.",
]
