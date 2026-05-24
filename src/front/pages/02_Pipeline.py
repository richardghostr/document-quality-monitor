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
