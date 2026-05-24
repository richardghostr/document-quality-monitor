"""
etl/extract.py
Chargement des données sources : CSV, Excel, ou génération d'un dataset simulé.
"""

import os
import random
from datetime import datetime, timedelta

import pandas as pd
import yaml

from src.utils.logger import get_logger

logger = get_logger("etl.extract")


def load_config(config_path: str = "config.yaml") -> dict:
    """Charge le fichier de configuration YAML."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_from_csv(filepath: str) -> pd.DataFrame:
    """
    Charge un fichier CSV et retourne un DataFrame brut.

    Args:
        filepath: Chemin vers le fichier CSV source

    Returns:
        DataFrame brut non nettoyé
    """
    logger.info(f"Chargement CSV : {filepath}")
    if not os.path.exists(filepath):
        logger.error(f"Fichier introuvable : {filepath}")
        raise FileNotFoundError(f"Le fichier source est introuvable : {filepath}")

    tried = []
    df = None
    for encoding in ["utf-8", "utf-8-sig", "latin-1"]:
        try:
            # sep=None + engine="python" permet de détecter automatiquement ; , \t.
            df = pd.read_csv(filepath, sep=None, engine="python", encoding=encoding, dtype=str)
            break
        except Exception as exc:
            tried.append(f"{encoding}: {exc}")

    if df is None:
        raise ValueError(f"Impossible de lire le CSV avec encodages testés: {tried}")

    logger.info(f"  → {len(df)} ligne(s) chargée(s), {len(df.columns)} colonne(s)")
    return df


def extract_from_excel(filepath: str, sheet_name: str = 0) -> pd.DataFrame:
    """
    Charge un fichier Excel (.xlsx) et retourne un DataFrame brut.

    Args:
        filepath: Chemin vers le fichier Excel
        sheet_name: Nom ou index de la feuille à charger

    Returns:
        DataFrame brut
    """
    logger.info(f"Chargement Excel : {filepath} (feuille: {sheet_name})")
    if not os.path.exists(filepath):
        logger.error(f"Fichier introuvable : {filepath}")
        raise FileNotFoundError(f"Le fichier source est introuvable : {filepath}")

    df = pd.read_excel(filepath, sheet_name=sheet_name, dtype=str)
    logger.info(f"  → {len(df)} ligne(s) chargée(s)")
    return df


def generate_simulated_dataset(n: int = 500, output_path: str = "data/raw/documents.csv") -> pd.DataFrame:
    """
    Génère un dataset simulé réaliste de documents BTP.
    Introduit volontairement des anomalies pour tester les contrôles qualité.

    Args:
        n: Nombre de documents à générer
        output_path: Chemin de sauvegarde du CSV généré

    Returns:
        DataFrame simulé
    """
    logger.info(f"Génération dataset simulé : {n} documents...")

    random.seed(42)

    disciplines = ["Structure", "Génie civil", "VRD", "Électricité", "CVC", "Plomberie", "Façade"]
    types_doc = ["Plan d'exécution", "Note de calcul", "PV de réception", "Fiche de contrôle", "CCTP", "DOE"]
    statuts = ["Validé", "En révision", "Obsolète", "Manquant"]
    criticites = ["Critique", "Haute", "Moyenne", "Faible"]
    responsables = ["Lefebvre M.", "Martin T.", "Durand K.", "Bernard C.", "Rousseau S.", "Petit A.", None]
    projets = ["A89 Tunnel Est", "Grand Paris Ligne 16", "Stade Bordeaux", "Viaduc Saône"]
    versions = ["A", "B", "C", "D", "E"]

    rows = []
    for i in range(1, n + 1):
        discipline = random.choice(disciplines)
        type_doc = random.choice(types_doc)
        projet = random.choice(projets)
        statut = random.choices(statuts, weights=[60, 20, 12, 8])[0]
        criticite = random.choices(criticites, weights=[10, 25, 40, 25])[0]
        version = random.choice(versions)

        # Date de mise à jour — certains docs sont volontairement très anciens
        days_ago = random.choices(
            [random.randint(1, 60), random.randint(60, 365), random.randint(365, 900)],
            weights=[60, 25, 15]
        )[0]
        date_maj = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

        # Conformité dérivée du statut
        if statut == "Validé":
            conformite = random.choices(["Conforme", "Non conforme"], weights=[85, 15])[0]
        elif statut == "Manquant":
            conformite = "Non conforme"
        else:
            conformite = random.choices(["Conforme", "Non conforme", "En attente"], weights=[40, 30, 30])[0]

        nom_doc = f"{type_doc} {discipline} - {projet.split()[0]} - Lot {random.randint(1, 5)}"

        rows.append({
            "doc_id": f"BTP-2024-{i:04d}",
            "nom_document": nom_doc,
            "version": version if statut != "Manquant" else "",
            "statut": statut,
            "date_mise_a_jour": date_maj if statut != "Manquant" else "",
            "responsable": random.choice(responsables),  # None introduit des champs vides
            "discipline": discipline,
            "criticite": criticite,
            "type_document": type_doc,
            "projet": projet,
            "conformite": conformite,
            "nb_revisions": random.randint(0, 8),
            "commentaire": "",
        })

    # Injection de doublons volontaires (même nom, versions différentes)
    for j in range(20):
        base = random.choice(rows).copy()
        base["doc_id"] = f"BTP-2024-{n + j + 1:04d}"
        base["version"] = random.choice(versions)
        rows.append(base)

    # Injection de statuts invalides pour tester la détection
    for k in range(5):
        rows[k]["statut"] = random.choice(["En cours", "Archivé", "Draft"])

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"  → Dataset sauvegardé : {output_path} ({len(df)} lignes)")
    return df


def extract(config: dict) -> pd.DataFrame:
    """
    Point d'entrée principal de l'extraction.
    Charge depuis le CSV source défini dans config.yaml.
    Si le fichier n'existe pas, génère un dataset simulé.

    Args:
        config: Dictionnaire de configuration

    Returns:
        DataFrame brut prêt pour la transformation
    """
    raw_path = config["paths"]["raw_data"]

    if os.path.exists(raw_path):
        ext = os.path.splitext(raw_path)[1].lower()
        if ext in {".xlsx", ".xls"}:
            return extract_from_excel(raw_path)
        return extract_from_csv(raw_path)
    else:
        logger.warning(f"Fichier source absent ({raw_path}). Génération d'un dataset simulé.")
        return generate_simulated_dataset(n=500, output_path=raw_path)