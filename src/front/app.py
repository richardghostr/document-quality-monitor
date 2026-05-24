"""Home page for Document Quality Monitor Streamlit app."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.front.services.data_service import load_bundle
from src.front.utils.ui import inject_css, render_hero, render_kpi

st.set_page_config(page_title="Document Quality Monitor", page_icon="📑", layout="wide", initial_sidebar_state="expanded")
inject_css()

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = 0

bundle = load_bundle(st.session_state.refresh_token)
stats = bundle["stats"]

st.sidebar.markdown("## Workflow")
st.sidebar.page_link("pages/01_Import.py", label="1. Import", icon="📥")
st.sidebar.page_link("pages/02_Pipeline.py", label="2. Pipeline", icon="⚙️")
st.sidebar.page_link("pages/03_Resultats.py", label="3. Résultats", icon="📊")
st.sidebar.page_link("pages/04_Exports.py", label="4. Exports", icon="📦")

render_hero(
    "Document Quality Monitor",
    "Outil interne: import documentaire, exécution pipeline, centralisation des livrables et préparation Power BI.",
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    render_kpi("Documents", str(stats["total_documents"]), f"Source: {stats['source']}")
with c2:
    render_kpi("Anomalies", str(stats["anomalies"]), "Contrôles qualité existants")
with c3:
    render_kpi("Taux conformité", f"{stats['taux_conformite']:.1f}%", "Calcul backend")
with c4:
    render_kpi("Score moyen", f"{stats['score_moyen']:.1f}", "Sur 100")

st.markdown("---")
st.markdown("### Parcours recommandé")
st.markdown("1. **Import**: charger CSV/Excel ou enregistrer un lien SharePoint")
st.markdown("2. **Pipeline**: lancer les scripts existants sans modifier la logique métier")
st.markdown("3. **Résultats**: consulter le résumé qualité et les anomalies")
st.markdown("4. **Exports**: télécharger HTML, CSV, Excel et dataset pour Power BI")

st.info("L'application réutilise directement le backend déjà développé (ETL, checks, scoring, reporting).")
