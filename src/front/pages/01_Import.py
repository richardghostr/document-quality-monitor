"""Import page: CSV/Excel upload and SharePoint link registration."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.front.services.import_service import (
    get_import_history,
    preview_uploaded_file,
    save_sharepoint_link,
    save_uploaded_file,
)
from src.etl.schema_mapper import standard_columns
from src.front.utils.ui import inject_css, render_hero

st.set_page_config(page_title="Import", page_icon="📥", layout="wide")
inject_css()

render_hero("Import des données", "Chargez vos fichiers bruts (CSV/Excel) ou enregistrez un lien SharePoint.")

left, right = st.columns([1.2, 0.8], gap="large")

with left:
    st.markdown("### Upload CSV / Excel")
    uploaded = st.file_uploader(
        "Déposez un fichier source",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=False,
    )

    if uploaded is not None:
        st.markdown("#### Étape 1 · Détection automatique")
        ok, message, payload = preview_uploaded_file(uploaded)
        if not ok:
            st.error(message)
        else:
            st.info("Mapping automatique détecté. Vérifiez et corrigez si besoin avant validation.")

            mapping_df = payload["mapping_rows"].copy()
            st.markdown("##### Aperçu des données détectées")
            st.dataframe(payload.get("preview", mapping_df.head(0)), width="stretch", hide_index=True)

            edited_mapping_df = st.data_editor(
                mapping_df,
                width="stretch",
                hide_index=True,
                column_config={
                    "source_column": st.column_config.TextColumn("Colonne source", disabled=True),
                    "target_standard": st.column_config.SelectboxColumn(
                        "Colonne standard",
                        options=[""] + standard_columns(),
                        required=False,
                    ),
                    "confidence": st.column_config.NumberColumn("Confiance", format="%.1f"),
                    "method": st.column_config.TextColumn("Méthode", disabled=True),
                },
                key="mapping_editor",
            )

            c1, c2 = st.columns(2)
            with c1:
                st.metric("Colonnes non reconnues", len(payload.get("unmapped_source_columns", [])))
            with c2:
                st.metric("Colonnes standard manquantes", len(payload.get("missing_standard_columns", [])))

            if payload.get("unmapped_source_columns"):
                st.warning("Colonnes non reconnues: " + ", ".join(payload["unmapped_source_columns"]))

            st.markdown("#### Étape 2 · Validation & import")
            if st.button("Valider import + mapping", type="primary", width="stretch"):
                manual_mapping = {}
                for _, row in edited_mapping_df.iterrows():
                    source = str(row.get("source_column", "")).strip()
                    target = str(row.get("target_standard", "")).strip()
                    if source and target:
                        manual_mapping[source] = target

                ok_save, msg_save, preview = save_uploaded_file(uploaded, manual_mapping=manual_mapping)
                if ok_save:
                    st.success(msg_save)
                    if preview is not None and not preview.empty:
                        st.markdown("#### Aperçu des données")
                        st.dataframe(preview, width="stretch", hide_index=True)
                else:
                    st.error(msg_save)

with right:
    st.markdown("### Lien SharePoint")
    sp_link = st.text_input("URL SharePoint / fichier public")
    if st.button("Enregistrer le lien", width="stretch"):
        if not sp_link.strip():
            st.warning("Veuillez saisir un lien.")
        else:
            ok, msg = save_sharepoint_link(sp_link.strip())
            if ok:
                st.success(msg)
            else:
                st.error(msg)

st.markdown("---")
st.markdown("### Historique des imports")
history = get_import_history()
if history.empty:
    st.info("Aucun import enregistré pour le moment.")
else:
    st.dataframe(history.sort_values("timestamp", ascending=False), width="stretch", hide_index=True)
