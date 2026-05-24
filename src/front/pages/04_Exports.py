"""Exports page: centralize and download generated deliverables."""

from __future__ import annotations

import mimetypes
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.front.services.data_service import list_generated_exports, load_bundle
from src.front.utils.ui import inject_css, render_hero

st.set_page_config(page_title="Exports", page_icon="📦", layout="wide")
inject_css()

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = 0

bundle = load_bundle(st.session_state.refresh_token)
exports = list_generated_exports()

render_hero("Exports & livrables", "Téléchargez les livrables finaux pour diffusion et exploitation Power BI.")

if not exports:
    st.warning("Aucun export détecté. Exécutez le pipeline puis revenez ici.")
    st.stop()

# Mise en avant Power BI dataset
powerbi_candidates = [
    p for p in exports
    if p.suffix.lower() in {".pbix", ".csv"}
    and (
        "documents_powerbi" in p.name.lower()
        or "anomalies_powerbi" in p.name.lower()
        or "power" in p.name.lower()
        or "bi" in p.name.lower()
    )
]

if powerbi_candidates:
    st.markdown("### Bloc central Power BI")
    st.success("Bundle Power BI prêt: datasets documents + anomalies")
    st.caption("Workflow recommandé dans Power BI Desktop: charger les 2 CSV puis relier doc_id.")

    for pbi_file in powerbi_candidates[:2]:
        mime = mimetypes.guess_type(str(pbi_file))[0] or "application/octet-stream"
        st.download_button(
            label=f"Télécharger {pbi_file.name}",
            data=pbi_file.read_bytes(),
            file_name=pbi_file.name,
            mime=mime,
            width="stretch",
            type="primary",
            key=f"pbi_{pbi_file.name}",
        )

st.markdown("---")
st.markdown("### Tous les livrables")

rows = []
for path in exports:
    rows.append({
        "fichier": path.name,
        "taille_ko": round(path.stat().st_size / 1024, 2),
        "type": path.suffix.lower().replace(".", ""),
        "chemin": str(path),
    })

files_df = pd.DataFrame(rows)
st.dataframe(files_df, width="stretch", hide_index=True)

st.markdown("---")
st.markdown("### Téléchargements")
for path in exports:
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    c1, c2 = st.columns([0.74, 0.26])
    with c1:
        st.markdown(f"**{path.name}**")
        st.caption(str(path))
    with c2:
        st.download_button(
            label="Télécharger",
            data=path.read_bytes(),
            file_name=path.name,
            mime=mime,
            key=f"dl_{path.name}",
            width="stretch",
        )
