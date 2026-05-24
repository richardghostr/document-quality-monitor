"""
quality/checks.py
Les 7 contrôles qualité automatiques du Document Quality Monitor.

Chaque fonction retourne un DataFrame d'anomalies avec les colonnes :
    - doc_id
    - type_anomalie
    - description
    - priorite  ('Critique' | 'Haute' | 'Moyenne')
"""

from datetime import datetime, timedelta

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("quality.checks")

STATUTS_VALIDES = {"Validé", "En révision", "Manquant", "Obsolète"}


def _source_has(mapping_report: dict | None, standard_col: str) -> bool:
    if not mapping_report:
        return True
    present = set(mapping_report.get("source_present_standard_columns", []))
    return standard_col in present


def _empty_anomalies() -> pd.DataFrame:
    return pd.DataFrame(columns=["doc_id", "type_anomalie", "description", "priorite"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Doublons
# ─────────────────────────────────────────────────────────────────────────────

def check_doublons(df: pd.DataFrame) -> pd.DataFrame:
    """
    Détecte les documents en doublon.
    Critère : même (nom_document, discipline, projet) sur plusieurs doc_id distincts.

    Risque métier : deux équipes travaillent sur des versions différentes du même document
    sans coordination, risque d'utiliser le mauvais plan en phase travaux.
    """
    required = ["nom_document", "discipline", "projet"]
    if any(c not in df.columns for c in required):
        return _empty_anomalies()

    mask = df.duplicated(subset=required, keep=False)
    doublons = df[mask].copy()

    if doublons.empty:
        logger.info("[CHECK 1] Doublons : aucun détecté")
        return _empty_anomalies()

    doublons["type_anomalie"] = "Doublon"
    doublons["description"] = (
        "Document en doublon sur (nom, discipline, projet) : "
        + doublons["nom_document"].fillna("?")
    )
    doublons["priorite"] = "Haute"

    logger.warning(f"[CHECK 1] Doublons : {len(doublons)} document(s) concerné(s)")
    return doublons[["doc_id", "type_anomalie", "description", "priorite"]]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Incohérences de versions
# ─────────────────────────────────────────────────────────────────────────────

def check_versions_incoherentes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Détecte les cas où un même nom de document a plusieurs versions actives simultanément.
    Seule la version la plus récente (max alphabétique) devrait être active.

    Risque métier : un sous-traitant exécute un ouvrage sur la base d'un plan périmé.
    """
    required = ["version", "nom_document", "discipline", "projet", "statut", "doc_id"]
    if any(c not in df.columns for c in required):
        return _empty_anomalies()

    anomalies = []

    groupes = df[df["version"].notna()].groupby(["nom_document", "discipline", "projet"])

    for (nom, disc, proj), groupe in groupes:
        versions_actives = groupe[groupe["statut"].isin(["Validé", "En révision"])]
        if len(versions_actives["version"].unique()) > 1:
            for _, row in versions_actives.iterrows():
                anomalies.append({
                    "doc_id": row["doc_id"],
                    "type_anomalie": "Version incohérente",
                    "description": f"Plusieurs versions actives pour '{nom}' ({disc}) : "
                                   f"{sorted(versions_actives['version'].unique())}",
                    "priorite": "Haute",
                })

    result = pd.DataFrame(anomalies)
    if result.empty:
        logger.info("[CHECK 2] Versions incohérentes : aucune détectée")
    else:
        logger.warning(f"[CHECK 2] Versions incohérentes : {len(result)} cas détecté(s)")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 3. Documents manquants (vs nomenclature cible)
# ─────────────────────────────────────────────────────────────────────────────

def check_documents_manquants(df: pd.DataFrame) -> pd.DataFrame:
    """
    Signale les documents dont le statut est explicitement 'Manquant'.

    En production, cette fonction comparerait le dataset avec une nomenclature
    de référence (liste exhaustive des documents attendus par le marché).

    Risque métier : absence d'un DOE ou d'un PV de réception bloque la réception du lot.
    """
    if "statut" not in df.columns:
        return _empty_anomalies()

    manquants = df[df["statut"] == "Manquant"].copy()

    if manquants.empty:
        logger.info("[CHECK 3] Documents manquants : aucun détecté")
        return _empty_anomalies()

    manquants["type_anomalie"] = "Document manquant"
    manquants["description"] = (
        "Document absent du registre documentaire : "
        + manquants.get("nom_document", pd.Series("?", index=manquants.index)).fillna("?")
        + " (projet : " + manquants.get("projet", pd.Series("?", index=manquants.index)).fillna("?") + ")"
    )
    # Criticité héritée du document
    criticite_series = manquants.get("criticite", pd.Series("Haute", index=manquants.index))
    manquants["priorite"] = criticite_series.map(
        {"Critique": "Critique", "Haute": "Haute", "Moyenne": "Moyenne", "Faible": "Moyenne"}
    ).fillna("Haute")

    logger.warning(f"[CHECK 3] Documents manquants : {len(manquants)} document(s)")
    return manquants[["doc_id", "type_anomalie", "description", "priorite"]]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Documents obsolètes
# ─────────────────────────────────────────────────────────────────────────────

def check_obsoletes(df: pd.DataFrame, seuil_jours: int = 180) -> pd.DataFrame:
    """
    Signale les documents actifs (statut Validé) non mis à jour depuis seuil_jours.

    Risque métier : un plan structurel non mis à jour depuis 6 mois peut ne plus
    correspondre aux modifications du chantier (avenants, optimisations).
    """
    required = ["statut", "date_mise_a_jour", "doc_id"]
    if any(c not in df.columns for c in required):
        return _empty_anomalies()

    limite = datetime.now() - timedelta(days=seuil_jours)

    mask = (
        (df["statut"] == "Validé")
        & (df["date_mise_a_jour"].notna())
        & (df["date_mise_a_jour"] < pd.Timestamp(limite))
    )
    obsoletes = df[mask].copy()

    if obsoletes.empty:
        logger.info(f"[CHECK 4] Obsolètes (>{seuil_jours}j) : aucun détecté")
        return _empty_anomalies()

    obsoletes["type_anomalie"] = "Document obsolète"
    obsoletes["description"] = (
        f"Non mis à jour depuis plus de {seuil_jours} jours. "
        "Dernière MAJ : " + obsoletes["date_mise_a_jour"].astype(str)
    )
    criticite_series = obsoletes.get("criticite", pd.Series("Moyenne", index=obsoletes.index))
    obsoletes["priorite"] = criticite_series.map(
        {"Critique": "Critique", "Haute": "Haute", "Moyenne": "Moyenne", "Faible": "Moyenne"}
    ).fillna("Moyenne")

    logger.warning(f"[CHECK 4] Obsolètes : {len(obsoletes)} document(s)")
    return obsoletes[["doc_id", "type_anomalie", "description", "priorite"]]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Champs obligatoires vides
# ─────────────────────────────────────────────────────────────────────────────

def check_champs_vides(df: pd.DataFrame,
                       champs: list = None) -> pd.DataFrame:
    """
    Signale les documents avec des champs obligatoires manquants.

    Risque métier : un document sans responsable ne peut pas être relancé en cas
    d'anomalie ; sans discipline, il ne sera pas adressé à la bonne équipe.
    """
    if champs is None:
        champs = ["responsable", "discipline", "criticite", "type_document", "projet"]

    champs_presents = [c for c in champs if c in df.columns]
    if not champs_presents:
        return _empty_anomalies()

    mask = df[champs_presents].isnull().any(axis=1)
    vides = df[mask].copy()

    if vides.empty:
        logger.info("[CHECK 5] Champs vides : aucun détecté")
        return _empty_anomalies()

    def lister_champs_vides(row):
        return [c for c in champs_presents if pd.isnull(row[c])]

    vides["champs_manquants"] = vides.apply(lister_champs_vides, axis=1)
    vides["type_anomalie"] = "Champ obligatoire vide"
    vides["description"] = "Champ(s) manquant(s) : " + vides["champs_manquants"].astype(str)
    vides["priorite"] = "Haute"

    logger.warning(f"[CHECK 5] Champs vides : {len(vides)} document(s) concerné(s)")
    return vides[["doc_id", "type_anomalie", "description", "priorite"]]


# ─────────────────────────────────────────────────────────────────────────────
# 6. Statuts invalides
# ─────────────────────────────────────────────────────────────────────────────

def check_statuts_invalides(df: pd.DataFrame) -> pd.DataFrame:
    """
    Détecte les documents dont le statut ne fait pas partie du référentiel autorisé.

    Risque métier : des statuts non normalisés ('Draft', 'En cours', 'Archivé')
    brisent les règles de gestion et faussent les KPIs du dashboard.
    """
    if "statut" not in df.columns:
        return _empty_anomalies()

    if "statut_invalide" not in df.columns:
        mask = ~df["statut"].isin(STATUTS_VALIDES)
    else:
        mask = df["statut_invalide"] == True  # noqa: E712

    invalides = df[mask].copy()

    if invalides.empty:
        logger.info("[CHECK 6] Statuts invalides : aucun détecté")
        return _empty_anomalies()

    invalides["type_anomalie"] = "Statut invalide"
    invalides["description"] = (
        "Statut hors référentiel : '"
        + invalides["statut"].fillna("NULL")
        + f"'. Valeurs autorisées : {sorted(STATUTS_VALIDES)}"
    )
    invalides["priorite"] = "Moyenne"

    logger.warning(f"[CHECK 6] Statuts invalides : {len(invalides)} document(s)")
    return invalides[["doc_id", "type_anomalie", "description", "priorite"]]


# ─────────────────────────────────────────────────────────────────────────────
# 7. Anomalies critiques (criticité haute + non conforme)
# ─────────────────────────────────────────────────────────────────────────────

def check_anomalies_critiques(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identifie les documents à double risque : criticité élevée ET non conformes.
    Ces cas déclenchent une alerte mail immédiate.

    Risque métier : un plan structurel critique non conforme peut entraîner
    une non-conformité réglementaire ou un sinistre lors des travaux.
    """
    required = ["criticite", "conformite", "doc_id"]
    if any(c not in df.columns for c in required):
        return _empty_anomalies()

    mask = (
        df["criticite"].isin(["Critique", "Haute"])
        & (df["conformite"] == "Non conforme")
    )
    critiques = df[mask].copy()

    if critiques.empty:
        logger.info("[CHECK 7] Anomalies critiques : aucune détectée")
        return _empty_anomalies()

    critiques["type_anomalie"] = "Anomalie critique"
    critiques["description"] = (
        "Document critique non conforme — action immédiate requise. "
        "Responsable : " + critiques["responsable"].fillna("Non assigné")
    )
    critiques["priorite"] = "Critique"

    logger.warning(f"[CHECK 7] Anomalies critiques : {len(critiques)} document(s) — ALERTE")
    return critiques[["doc_id", "type_anomalie", "description", "priorite"]]


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrateur des contrôles
# ─────────────────────────────────────────────────────────────────────────────

def run_all_checks(df: pd.DataFrame, config: dict = None, mapping_report: dict | None = None) -> pd.DataFrame:
    """
    Lance les 7 contrôles qualité et retourne un DataFrame unifié de toutes les anomalies.

    Args:
        df: DataFrame transformé
        config: Dictionnaire de configuration (pour les seuils)

    Returns:
        DataFrame des anomalies avec colonnes [doc_id, type_anomalie, description, priorite]
    """
    seuil = 180
    if config:
        seuil = config.get("quality", {}).get("seuil_obsolescence_jours", 180)

    logger.info("=" * 60)
    logger.info("Lancement des 7 contrôles qualité...")
    logger.info("=" * 60)

    resultats = []

    if _source_has(mapping_report, "nom_document") and _source_has(mapping_report, "discipline") and _source_has(mapping_report, "projet"):
        resultats.append(check_doublons(df))
    else:
        logger.warning("[CHECK 1] Doublons ignoré : colonnes source insuffisantes")

    if all(_source_has(mapping_report, c) for c in ["version", "nom_document", "discipline", "projet", "statut"]):
        resultats.append(check_versions_incoherentes(df))
    else:
        logger.warning("[CHECK 2] Versions incohérentes ignoré : colonne version/statut absente")

    if _source_has(mapping_report, "statut"):
        resultats.append(check_documents_manquants(df))
    else:
        logger.warning("[CHECK 3] Documents manquants ignoré : colonne statut absente")

    if _source_has(mapping_report, "statut") and _source_has(mapping_report, "date_mise_a_jour"):
        resultats.append(check_obsoletes(df, seuil_jours=seuil))
    else:
        logger.warning("[CHECK 4] Obsolètes ignoré : colonne date/statut absente")

    champs = ["responsable", "discipline", "criticite", "type_document", "projet"]
    champs_source = [c for c in champs if _source_has(mapping_report, c)]
    if champs_source:
        resultats.append(check_champs_vides(df, champs=champs_source))
    else:
        logger.warning("[CHECK 5] Champs vides ignoré : aucun champ obligatoire détecté")

    if _source_has(mapping_report, "statut"):
        resultats.append(check_statuts_invalides(df))
    else:
        logger.warning("[CHECK 6] Statuts invalides ignoré : colonne statut absente")

    if _source_has(mapping_report, "criticite") and _source_has(mapping_report, "conformite"):
        resultats.append(check_anomalies_critiques(df))
    else:
        logger.warning("[CHECK 7] Anomalies critiques ignoré : criticité/conformité absentes")

    # Filtrage des DataFrames vides avant concaténation
    non_vides = [r for r in resultats if not r.empty]

    if not non_vides:
        logger.info("Aucune anomalie détectée. Base documentaire conforme.")
        return pd.DataFrame(columns=["doc_id", "type_anomalie", "description", "priorite"])

    anomalies = pd.concat(non_vides, ignore_index=True)
    logger.info(f"Total anomalies détectées : {len(anomalies)}")
    logger.info(f"  Critiques : {(anomalies['priorite'] == 'Critique').sum()}")
    logger.info(f"  Hautes    : {(anomalies['priorite'] == 'Haute').sum()}")
    logger.info(f"  Moyennes  : {(anomalies['priorite'] == 'Moyenne').sum()}")
    return anomalies
