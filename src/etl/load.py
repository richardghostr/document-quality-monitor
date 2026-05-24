"""
etl/load.py
Chargement des données transformées dans SQLite et exports CSV/Excel.
"""

import os
import sqlite3

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("etl.load")


def create_schema(conn: sqlite3.Connection) -> None:
    """
    Crée les tables SQL si elles n'existent pas.
    Appelé à chaque exécution pour garantir la cohérence du schéma.
    """
    logger.info("Vérification / création du schéma SQL...")
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id              TEXT PRIMARY KEY,
            nom_document        TEXT NOT NULL,
            version             TEXT,
            statut              TEXT,
            date_mise_a_jour    TEXT,
            responsable         TEXT,
            discipline          TEXT,
            criticite           TEXT,
            type_document       TEXT,
            projet              TEXT,
            conformite          TEXT,
            nb_revisions        INTEGER DEFAULT 0,
            commentaire         TEXT,
            age_jours           INTEGER,
            annee_maj           INTEGER,
            mois_maj            INTEGER,
            statut_invalide     INTEGER DEFAULT 0,
            criticite_invalide  INTEGER DEFAULT 0,
            charge_ts           TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS anomalies (
            anomalie_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id              TEXT REFERENCES documents(doc_id),
            type_anomalie       TEXT NOT NULL,
            description         TEXT,
            date_detection      TEXT DEFAULT CURRENT_DATE,
            statut_traitement   TEXT DEFAULT 'Ouvert',
            priorite            TEXT
        );

        CREATE TABLE IF NOT EXISTS runs (
            run_id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date_run            TEXT DEFAULT CURRENT_TIMESTAMP,
            nb_documents        INTEGER,
            nb_anomalies        INTEGER,
            taux_conformite     REAL,
            statut_run          TEXT
        );
    """)
    conn.commit()
    logger.info("  → Schéma SQL prêt")


def load_documents(df: pd.DataFrame, db_path: str) -> None:
    """
    Insère ou remplace les documents dans la table SQLite.

    Args:
        df: DataFrame transformé
        db_path: Chemin vers la base SQLite
    """
    logger.info(f"Chargement dans SQLite : {db_path}")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    cols_sql = [
        "doc_id", "nom_document", "version", "statut", "date_mise_a_jour",
        "responsable", "discipline", "criticite", "type_document", "projet",
        "conformite", "nb_revisions", "commentaire", "age_jours",
        "annee_maj", "mois_maj", "statut_invalide", "criticite_invalide"
    ]
    # On ne garde que les colonnes présentes dans le DataFrame
    cols_present = [c for c in cols_sql if c in df.columns]
    df_sql = df[cols_present].copy()

    # Conversion booléens → int pour SQLite
    for col in ["statut_invalide", "criticite_invalide"]:
        if col in df_sql.columns:
            df_sql[col] = df_sql[col].astype(int)

    # Conversion dates en string pour SQLite
    if "date_mise_a_jour" in df_sql.columns:
        df_sql["date_mise_a_jour"] = df_sql["date_mise_a_jour"].astype(str)

    with sqlite3.connect(db_path) as conn:
        create_schema(conn)
        df_sql.to_sql("documents", conn, if_exists="replace", index=False)
        logger.info(f"  → {len(df_sql)} document(s) chargé(s) dans la table 'documents'")


def load_anomalies(anomalies: pd.DataFrame, db_path: str) -> None:
    """
    Insère les anomalies détectées dans la table SQLite.

    Args:
        anomalies: DataFrame des anomalies issu de quality/checks.py
        db_path: Chemin vers la base SQLite
    """
    if anomalies.empty:
        logger.info("Aucune anomalie à charger en base.")
        return

    logger.info(f"Chargement des anomalies : {len(anomalies)} entrée(s)")

    cols = ["doc_id", "type_anomalie", "description", "priorite"]
    cols_present = [c for c in cols if c in anomalies.columns]
    df_an = anomalies[cols_present].copy()

    with sqlite3.connect(db_path) as conn:
        # Vider les anomalies existantes avant rechargement (run complet)
        conn.execute("DELETE FROM anomalies")
        df_an.to_sql("anomalies", conn, if_exists="append", index=False)
        logger.info(f"  → {len(df_an)} anomalie(s) insérée(s)")


def export_csv(df: pd.DataFrame, output_dir: str, filename: str = "documents_clean.csv") -> str:
    """Exporte le DataFrame nettoyé en CSV."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info(f"Export CSV : {path}")
    return path


def export_excel(df: pd.DataFrame, anomalies: pd.DataFrame, output_dir: str,
                 filename: str = "rapport_qualite.xlsx") -> str:
    """
    Exporte les documents et anomalies dans un fichier Excel multi-feuilles.
    Feuille 1 : Documents complets
    Feuille 2 : Anomalies détectées
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Documents", index=False)
        if not anomalies.empty:
            anomalies.to_excel(writer, sheet_name="Anomalies", index=False)

    logger.info(f"Export Excel : {path}")
    return path


def export_power_bi_bundle(
    df: pd.DataFrame,
    anomalies: pd.DataFrame,
    output_dir: str,
    subdir: str = "powerbi",
    mapping_report: dict | None = None,
) -> dict:
    """
    Génère un bundle prêt pour Power BI.

    Fichiers produits:
      - documents_powerbi.csv
      - anomalies_powerbi.csv
      - powerbi_readme.txt

    Args:
        df: DataFrame documents scorés
        anomalies: DataFrame anomalies
        output_dir: Répertoire principal des sorties
        subdir: Sous-dossier Power BI

    Returns:
        Dict des chemins générés
    """
    powerbi_dir = os.path.join(output_dir, subdir)
    os.makedirs(powerbi_dir, exist_ok=True)

    doc_cols = [
        "doc_id", "nom_document", "version", "statut", "date_mise_a_jour",
        "responsable", "discipline", "criticite", "type_document", "projet",
        "conformite", "conformite_score", "classification", "age_jours",
        "annee_maj", "mois_maj",
    ]
    docs_out = df[[c for c in doc_cols if c in df.columns]].copy()

    # Garantit une date exploitable en modèle Power BI
    if "date_mise_a_jour" in docs_out.columns:
        docs_out["date_mise_a_jour"] = pd.to_datetime(
            docs_out["date_mise_a_jour"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

    anomaly_cols = [
        "doc_id", "type_anomalie", "description", "priorite",
        "date_detection", "statut_traitement",
    ]
    anomalies_out = anomalies[[c for c in anomaly_cols if c in anomalies.columns]].copy()

    docs_path = os.path.join(powerbi_dir, "documents_powerbi.csv")
    anomalies_path = os.path.join(powerbi_dir, "anomalies_powerbi.csv")
    readme_path = os.path.join(powerbi_dir, "powerbi_readme.txt")
    mapping_path = os.path.join(powerbi_dir, "mapping_applique.csv")

    docs_out.to_csv(docs_path, index=False, encoding="utf-8-sig")
    anomalies_out.to_csv(anomalies_path, index=False, encoding="utf-8-sig")

    if mapping_report:
        mapping_rows = mapping_report.get("mapping_details", [])
        pd.DataFrame(mapping_rows).to_csv(mapping_path, index=False, encoding="utf-8-sig")

    readme_text = (
        "Document Quality Monitor - Power BI Bundle\n"
        "=======================================\n\n"
        "1) Chargez documents_powerbi.csv\n"
        "2) Chargez anomalies_powerbi.csv\n"
        "3) Créez la relation: documents_powerbi[doc_id] -> anomalies_powerbi[doc_id]\n"
        "4) Utilisez date_mise_a_jour pour l'analyse temporelle\n"
        "5) Consultez mapping_applique.csv pour tracer le mapping source -> standard\n"
    )
    with open(readme_path, "w", encoding="utf-8") as handle:
        handle.write(readme_text)

    logger.info(f"Export Power BI : {docs_path}")
    logger.info(f"Export Power BI : {anomalies_path}")
    if mapping_report:
        logger.info(f"Export Power BI : {mapping_path}")
    return {
        "documents": docs_path,
        "anomalies": anomalies_path,
        "readme": readme_path,
        "mapping": mapping_path if mapping_report else "",
    }