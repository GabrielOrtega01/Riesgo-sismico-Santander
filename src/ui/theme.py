"""Identidad visual de la aplicación: paleta, estilos y piezas HTML reutilizables.

La paleta sigue una referencia validada para visualización de datos: una sola tonalidad azul
para magnitud (secuencial), naranja solo para resaltar la entidad elegida, y tintas neutras
para el texto (el texto nunca usa el color de una serie).
"""
from __future__ import annotations

from html import escape

import streamlit as st

# ---- paleta --------------------------------------------------------------------------------
SURFACE = "#fcfcfb"
PANEL = "#f1f0ec"
GRID = "#e1e0d9"
INK = "#1a1a19"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"

BLUE_100, BLUE_250, BLUE_450, BLUE_550, BLUE_600, BLUE_700 = (
    "#cde2fb", "#86b6ef", "#2a78d6", "#1c5cab", "#184f95", "#0d366b",
)
# Categóricos en orden fijo (azul, naranja, aqua, amarillo, magenta, verde)
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
ACCENT = CATEGORICAL[1]            # naranja: solo para resaltar la zona seleccionada
SERIES = CATEGORICAL[0]            # azul: serie única

STATUS = {                          # estados reservados; siempre con icono y texto
    "ok": ("#0ca30c", "✔"),
    "wip": ("#b27300", "◔"),
    "pending": ("#898781", "○"),
}

CSS = f"""
<style>
  .block-container {{ padding-top: 2.2rem; max-width: 1180px; }}
  h1, h2, h3 {{ color: {INK}; letter-spacing: -0.01em; }}

  /* barra lateral */
  [data-testid="stSidebar"] {{ background: {PANEL}; border-right: 1px solid {GRID}; }}
  [data-testid="stSidebar"] .brand {{ font-weight: 700; font-size: 1.05rem; color: {BLUE_600}; }}
  [data-testid="stSidebar"] .brand-sub {{ color: {INK_SECONDARY}; font-size: 0.82rem; margin-bottom: .6rem; }}

  /* banner principal */
  .hero {{
    background: linear-gradient(120deg, {BLUE_700} 0%, {BLUE_550} 62%, {BLUE_450} 100%);
    color: #ffffff; border-radius: 16px; padding: 2.1rem 2.2rem; margin-bottom: 1.2rem;
  }}
  .hero h1 {{ color: #ffffff; margin: 0 0 .35rem 0; font-size: 2.1rem; }}
  .hero p {{ color: #e8f0fb; margin: 0; font-size: 1.08rem; max-width: 46rem; line-height: 1.5; }}

  /* tarjetas */
  .card {{
    background: {SURFACE}; border: 1px solid {GRID}; border-radius: 14px;
    padding: 1.1rem 1.2rem; height: 100%;
  }}
  .card h4 {{ margin: 0 0 .45rem 0; font-size: 1.02rem; color: {BLUE_600}; }}
  .card p, .card li {{ color: {INK_SECONDARY}; font-size: .95rem; line-height: 1.5; margin: 0; }}
  .card ul {{ padding-left: 1.1rem; margin: .2rem 0 0 0; }}
  .step-num {{
    display: inline-block; width: 1.7rem; height: 1.7rem; line-height: 1.7rem; text-align: center;
    border-radius: 50%; background: {BLUE_550}; color: #fff; font-weight: 700; margin-right: .5rem;
  }}

  /* indicadores */
  [data-testid="stMetric"] {{
    background: {SURFACE}; border: 1px solid {GRID}; border-radius: 12px; padding: .7rem .9rem;
  }}
  [data-testid="stMetricLabel"] p {{ color: {INK_SECONDARY}; font-size: .86rem; }}
  [data-testid="stMetricValue"] {{ color: {INK}; font-size: 1.75rem; }}
  [data-testid="stMetricValue"] > div {{ overflow: visible; text-overflow: clip; }}

  /* etiquetas de estado */
  .badge {{
    display: inline-block; padding: .12rem .6rem; border-radius: 999px; font-size: .8rem;
    font-weight: 600; border: 1px solid currentColor; white-space: nowrap;
  }}
  .zone-header {{
    background: {PANEL}; border-left: 6px solid {ACCENT}; border-radius: 10px;
    padding: .9rem 1.2rem; margin: .4rem 0 1rem 0;
  }}
  .zone-header .name {{ font-size: 1.5rem; font-weight: 700; color: {INK}; }}
  .zone-header .meta {{ color: {INK_SECONDARY}; font-size: .92rem; }}
  .lede {{ font-size: 1.04rem; color: {INK_SECONDARY}; line-height: 1.55; }}
  .footnote {{ color: {INK_MUTED}; font-size: .82rem; }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="hero"><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def card(title: str, body: str, number: int | None = None) -> str:
    """HTML de una tarjeta. `body` es HTML propio de la aplicación (no datos externos)."""
    num = f'<span class="step-num">{number}</span>' if number is not None else ""
    return f'<div class="card"><h4>{num}{escape(title)}</h4>{body}</div>'


def badge(text: str, kind: str) -> str:
    color, icon = STATUS[kind]
    return f'<span class="badge" style="color:{color}">{icon} {escape(text)}</span>'


def zone_header(name: str, meta: str) -> None:
    st.markdown(
        f'<div class="zone-header"><div class="name">{escape(name)}</div>'
        f'<div class="meta">{escape(meta)}</div></div>',
        unsafe_allow_html=True,
    )

