"""Pipeline page: trigger and monitor backend pipeline execution."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.front.services.data_service import get_logs_tail, load_bundle, run_existing_pipeline
from src.front.utils.ui import inject_css, render_hero, render_kpi

st.set_page_config(page_title="Pipeline", page_icon="⚙️", layout="wide")
inject_css()

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = 0

render_hero("Exécution du pipeline", "Lance le pipeline existant et suit son exécution en temps réel simplifié.")

st.markdown(
    """
    <div class='dqm-signature'>
        <div class='dqm-signature-mark'></div>
        <div>
            <div class='dqm-signature-title'>Bouygues Travaux Publics · Orchestration pipeline</div>
            <div class='dqm-signature-sub'>Une exécution lisible, suivie et industrialisable, avec supervision des sorties et des logs.</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class='dqm-stepper'>
        <div class='dqm-step'><div class='dqm-step-label'>Entrée</div><div class='dqm-step-value'>Données prêtes</div></div>
        <div class='dqm-step'><div class='dqm-step-label'>Traitement</div><div class='dqm-step-value'>ETL + Qualité</div></div>
        <div class='dqm-step'><div class='dqm-step-label'>Sorties</div><div class='dqm-step-value'>SQLite + rapports</div></div>
        <div class='dqm-step'><div class='dqm-step-label'>Diffusion</div><div class='dqm-step-value'>Power BI ready</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

bundle = load_bundle(st.session_state.refresh_token)
stats = bundle["stats"]

k1, k2, k3 = st.columns(3)
with k1:
    render_kpi("Documents en base", str(stats["total_documents"]), "Avant exécution")
with k2:
    render_kpi("Anomalies", str(stats["anomalies"]), "Avant exécution")
with k3:
    render_kpi("Base", bundle["db_path"], "Chemin SQLite")

st.markdown("---")

st.markdown(
    """
    <div class='dqm-panel'>
        <div class='dqm-panel-title'>
            <h3>Contrôle d'exécution</h3>
            <span class='dqm-panel-tag'>Run monitor</span>
        </div>
        <p class='dqm-focus'>Le pipeline lance les scripts métier existants sans reconfiguration manuelle.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

status_box = st.empty()
progress = st.progress(0)

if st.button("Exécuter le pipeline", type="primary", width="stretch"):
    start = time.perf_counter()
    status_box.info("Pipeline en cours...")

    checkpoints = [20, 45, 70, 90]
    for pct in checkpoints:
        progress.progress(pct)
        time.sleep(0.15)

    try:
        code = run_existing_pipeline()
        elapsed = time.perf_counter() - start
        if code == 0:
            progress.progress(100)
            status_box.success(f"Pipeline terminé avec succès en {elapsed:.2f} s")
            st.session_state.refresh_token += 1
            st.cache_data.clear()
        else:
            status_box.error(f"Pipeline terminé avec erreur (code={code})")
    except Exception as exc:
        status_box.error(f"Erreur d'exécution: {exc}")

st.markdown("### Logs simplifiés")
logs = get_logs_tail(140)
st.code(logs, language="text")
