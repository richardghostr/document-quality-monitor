"""
etl/transform.py
Nettoyage, normalisation et enrichissement tolérant aux schémas variables.
"""

import os
import pandas as pd

from src.etl.schema_mapper import load_manual_mapping, standardize_dataframe
from src.utils.logger import get_logger

logger = get_logger("etl.transform")

# Valeurs autorisées (référentiel métier)
STATUTS_VALIDES = {"Validé", "En révision", "Manquant", "Obsolète"}
CRITICITES_VALIDES = {"Critique", "Haute", "Moyenne", "Faible"}
CONFORMITES_VALIDES = {"Conforme", "Non conforme", "En attente"}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise les noms de colonnes (strip, lowercase si besoin).
    Standardise les valeurs texte : strip des espaces superflus, gestion de la casse.
    """
    logger.info("Normalisation des colonnes et valeurs texte...")
    df.columns = [c.strip() for c in df.columns]

    text_cols = [
        "nom_document", "statut", "responsable", "discipline",
        "criticite", "type_document", "projet", "conformite", "version", "commentaire",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": None, "": None, "None": None})

    return df


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Convertit la colonne date_mise_a_jour en datetime. Les valeurs invalides → NaT."""
    logger.info("Parsing des dates...")
    if "date_mise_a_jour" in df.columns:
        df["date_mise_a_jour"] = pd.to_datetime(df["date_mise_a_jour"], errors="coerce")
        nb_nat = df["date_mise_a_jour"].isna().sum()
        if nb_nat > 0:
            logger.warning(f"  → {nb_nat} date(s) invalide(s) convertie(s) en NaT")
    return df


def cast_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Convertit nb_revisions en entier."""
    if "nb_revisions" in df.columns:
        df["nb_revisions"] = pd.to_numeric(df["nb_revisions"], errors="coerce").fillna(0).astype(int)
    return df


def flag_statut_invalide(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute une colonne booléenne indiquant si le statut est hors référentiel."""
    df["statut_invalide"] = ~df["statut"].isin(STATUTS_VALIDES)
    nb = df["statut_invalide"].sum()
    if nb > 0:
        logger.warning(f"  → {nb} document(s) avec statut invalide détecté(s)")
    return df


def flag_criticite_invalide(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute une colonne booléenne pour les criticités hors référentiel."""
    df["criticite_invalide"] = ~df["criticite"].isin(CRITICITES_VALIDES)
    nb = df["criticite_invalide"].sum()
    if nb > 0:
        logger.warning(f"  → {nb} document(s) avec criticité invalide détecté(s)")
    return df


def enrich_age_document(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule l'âge du document en jours depuis la dernière mise à jour.
    Colonne enrichie : age_jours (int)
    """
    now = pd.Timestamp.now()
    if "date_mise_a_jour" in df.columns:
        df["age_jours"] = (now - df["date_mise_a_jour"]).dt.days
    else:
        df["age_jours"] = pd.NA
    return df


def enrich_annee_mois(df: pd.DataFrame) -> pd.DataFrame:
    """Extrait l'année et le mois de la date de mise à jour pour les analyses temporelles."""
    if "date_mise_a_jour" in df.columns:
        df["annee_maj"] = df["date_mise_a_jour"].dt.year
        df["mois_maj"] = df["date_mise_a_jour"].dt.month
    else:
        df["annee_maj"] = pd.NA
        df["mois_maj"] = pd.NA
    return df


def _mapping_path_from_config(config: dict | None) -> str:
    default_path = "data/raw/manual_mapping.json"
    if not config:
        return default_path
    return config.get("paths", {}).get("manual_mapping", default_path)


def transform(
    df: pd.DataFrame,
    config: dict | None = None,
    manual_mapping: dict | None = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Pipeline de transformation complet.
    Applique dans l'ordre : normalisation → parsing → cast → flags → enrichissement.

    Args:
        df: DataFrame brut issu de l'extraction

    Returns:
        DataFrame nettoyé et enrichi, prêt pour les contrôles qualité et le chargement
    """
    logger.info(f"Début transformation — {len(df)} lignes en entrée")

    if manual_mapping is None:
        mapping_path = _mapping_path_from_config(config)
        if os.path.exists(mapping_path):
            manual_mapping = load_manual_mapping(mapping_path)
            logger.info(f"Mapping manuel chargé : {mapping_path}")
        else:
            manual_mapping = {}

    # Standardisation robuste du schéma (synonymes + fuzzy + valeurs par défaut).
    df, mapping_report = standardize_dataframe(df, manual_mapping=manual_mapping)
    logger.info(
        "Mapping auto appliqué : %s colonne(s) reconnue(s), %s non reconnue(s)",
        len(mapping_report.get("source_present_standard_columns", [])),
        len(mapping_report.get("unmapped_source_columns", [])),
    )

    df = normalize_columns(df)
    df = parse_dates(df)
    df = cast_numeric(df)
    df = flag_statut_invalide(df)
    df = flag_criticite_invalide(df)
    df = enrich_age_document(df)
    df = enrich_annee_mois(df)

    logger.info(f"Transformation terminée — {len(df)} lignes en sortie")
    return df, mapping_report