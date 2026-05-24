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

st.markdown(
    """
    <div class='dqm-signature'>
        <div class='dqm-signature-mark'></div>
        <div>
            <div class='dqm-signature-title'>Bouygues Travaux Publics · Import documentaire</div>
            <div class='dqm-signature-sub'>Ingestion robuste, mapping intelligent, validation manuelle et dépôt prêt pour le pipeline.</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class='dqm-stepper'>
        <div class='dqm-step'><div class='dqm-step-label'>Étape 1</div><div class='dqm-step-value'>Import CSV / Excel</div></div>
        <div class='dqm-step'><div class='dqm-step-label'>Étape 2</div><div class='dqm-step-value'>Détection & mapping</div></div>
        <div class='dqm-step'><div class='dqm-step-label'>Étape 3</div><div class='dqm-step-value'>Validation humaine</div></div>
        <div class='dqm-step'><div class='dqm-step-label'>Étape 4</div><div class='dqm-step-value'>Pipeline prêt</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1.2, 0.8], gap="large")

with left:
    st.markdown(
        """
        <div class='dqm-panel'>
            <div class='dqm-panel-title'>
                <h3>Upload & detection</h3>
                <span class='dqm-panel-tag'>Zone d'ingestion</span>
            </div>
            <p class='dqm-focus'>Le fichier source est lu avec tolérance aux formats réels d'entreprise.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Déposez un fichier source",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=False,
    )

    if uploaded is not None:
        st.markdown("#### Détection automatique")
        ok, message, payload = preview_uploaded_file(uploaded)
        if not ok:
            st.error(message)
        else:
            st.success("Mapping automatique détecté. Vérifiez et corrigez si besoin avant validation.")

            st.markdown(
                f"""
                <div class='dqm-strip'>
                    <span class='dqm-pill'>Colonnes reconnues: {len(payload.get('mapping_rows', []))}</span>
                    <span class='dqm-pill'>Non reconnues: {len(payload.get('unmapped_source_columns', []))}</span>
                    <span class='dqm-pill'>Manquantes: {len(payload.get('missing_standard_columns', []))}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

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

            st.markdown("#### Validation & import")
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
    st.markdown(
        """
        <div class='dqm-panel'>
            <div class='dqm-panel-title'>
                <h3>Sources externes</h3>
                <span class='dqm-panel-tag'>SharePoint</span>
            </div>
            <p class='dqm-focus'>Enregistrement des liens de partage ou d’export direct pour ingestion rapide.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
