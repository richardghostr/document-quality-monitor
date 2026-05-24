"""Reusable Streamlit UI helpers."""

from __future__ import annotations

from pathlib import Path

import streamlit as st


def inject_css() -> None:
    css_path = Path(__file__).resolve().parents[1] / "assets" / "styles.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def render_hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class='dqm-hero'>
            <h1>{title}</h1>
            <div class='dqm-sub'>{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi(label: str, value: str, hint: str = "") -> None:
    st.markdown(
        f"""
        <div class='dqm-kpi'>
            <div class='dqm-kpi-label'>{label}</div>
            <div class='dqm-kpi-value'>{value}</div>
            <div style='color:#6b7280;font-size:0.78rem'>{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
