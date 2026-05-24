"""Results page: summarize quality outcomes from backend outputs."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.front.services.data_service import load_bundle
from src.front.utils.ui import inject_css, render_hero, render_kpi

st.set_page_config(page_title="Résultats", page_icon="📊", layout="wide")
inject_css()

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = 0

bundle = load_bundle(st.session_state.refresh_token)
documents = bundle["documents"]
anomalies = bundle["anomalies"]
stats = bundle["stats"]

render_hero("Résultats de traitement", "Synthèse qualité issue des scripts existants.")

st.markdown(
    """
    <div class='dqm-signature'>
        <div class='dqm-signature-mark'></div>
        <div>
            <div class='dqm-signature-title'>Bouygues Travaux Publics · Lecture qualité</div>
            <div class='dqm-signature-sub'>Vue synthétique des performances documentaires, anomalies et tendances détectées.</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    render_kpi("Total documents", str(stats["total_documents"]))
with c2:
    render_kpi("Taux conformité", f"{stats['taux_conformite']:.1f}%")
with c3:
    render_kpi("Documents critiques", str(stats["critiques"]))
with c4:
    render_kpi("Anomalies", str(stats["anomalies"]))

if documents.empty:
    st.warning("Aucun résultat disponible. Exécutez le pipeline depuis la page Pipeline.")
    st.stop()

st.markdown("---")

st.markdown(
    """
    <div class='dqm-stepper'>
        <div class='dqm-step'><div class='dqm-step-label'>Santé globale</div><div class='dqm-step-value'>Conformité & score</div></div>
        <div class='dqm-step'><div class='dqm-step-label'>Lecture métier</div><div class='dqm-step-value'>Statuts & risques</div></div>
        <div class='dqm-step'><div class='dqm-step-label'>Qualité</div><div class='dqm-step-value'>Anomalies prioritaires</div></div>
        <div class='dqm-step'><div class='dqm-step-label'>Diffusion</div><div class='dqm-step-value'>Exploitation dashboard</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1], gap="large")
with left:
    st.markdown(
        """
        <div class='dqm-panel'>
            <div class='dqm-panel-title'>
                <h3>Répartition des statuts</h3>
                <span class='dqm-panel-tag'>Vue opérationnelle</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if "statut" in documents.columns:
        status_df = documents["statut"].fillna("N/A").value_counts().reset_index()
        status_df.columns = ["statut", "count"]
        fig = px.pie(status_df, names="statut", values="count", hole=0.55, color="statut")
        fig.update_layout(height=360)
        st.plotly_chart(fig, width="stretch")

with right:
    st.markdown(
        """
        <div class='dqm-panel'>
            <div class='dqm-panel-title'>
                <h3>Top anomalies</h3>
                <span class='dqm-panel-tag'>Priorisation</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if anomalies.empty:
        st.info("Aucune anomalie détectée.")
    else:
        an_df = anomalies["type_anomalie"].value_counts().reset_index()
        an_df.columns = ["type_anomalie", "count"]
        fig = px.bar(an_df, x="count", y="type_anomalie", orientation="h")
        fig.update_layout(height=360)
        st.plotly_chart(fig, width="stretch")

st.markdown("---")
st.markdown(
    """
    <div class='dqm-panel'>
        <div class='dqm-panel-title'>
            <h3>Détail anomalies détectées</h3>
            <span class='dqm-panel-tag'>Traçabilité</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
if anomalies.empty:
    st.info("Aucune anomalie disponible.")
else:
    cols = [c for c in ["doc_id", "type_anomalie", "description", "priorite"] if c in anomalies.columns]
    st.dataframe(anomalies[cols], width="stretch", hide_index=True)
