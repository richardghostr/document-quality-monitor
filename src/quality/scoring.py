"""
quality/scoring.py
Moteur de scoring global pour conformité documentaire.

Calcule un score de conformité 0-100 par document basé sur les anomalies détectées.
"""

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("quality.scoring")


class ScoringEngine:
    """Moteur de calcul des scores de conformité."""

    def __init__(self, df: pd.DataFrame, anomalies: pd.DataFrame):
        """
        Initialise le moteur de scoring.

        Args:
            df: DataFrame des documents
            anomalies: DataFrame des anomalies détectées
        """
        self.df = df.copy()
        self.anomalies = anomalies
        self.scores = None

    def calculate_document_scores(self) -> pd.DataFrame:
        """
        Calcule le score de conformité par document.

        Score de base = 100
        Déductions par type d'anomalie :
            - Doublon : -15 points
            - Version incohérente : -12 points
            - Document manquant : -25 points
            - Obsolète : -10 points
            - Champ vide : -20 points
            - Statut invalide : -20 points
            - Anomalie critique : -25 points

        Returns:
            DataFrame avec colonne 'conformite_score' (0-100)
        """
        logger.info("Calcul des scores de conformité...")

        poids_anomalies = {
            "Doublon": 15,
            "Version incohérente": 12,
            "Document manquant": 25,
            "Document obsolète": 10,
            "Champ obligatoire vide": 20,
            "Statut invalide": 20,
            "Anomalie critique": 25,
        }

        self.df["conformite_score"] = 100

        if not self.anomalies.empty:
            for _, anom in self.anomalies.iterrows():
                doc_id = anom["doc_id"]
                type_anom = anom["type_anomalie"]
                deduction = poids_anomalies.get(type_anom, 5)

                mask = self.df["doc_id"] == doc_id
                if mask.any():
                    self.df.loc[mask, "conformite_score"] -= deduction

        self.df["conformite_score"] = self.df["conformite_score"].clip(0, 100)

        logger.info("✓ Scores calculés")
        return self.df

    def classify_documents(self) -> pd.DataFrame:
        """
        Classe les documents selon leur score.

        Returns:
            DataFrame avec colonne 'classification'
        """
        def classify(score):
            if score >= 90:
                return "Conforme"
            if score >= 75:
                return "À améliorer"
            if score >= 50:
                return "Non conforme"
            return "Critique"

        self.df["classification"] = self.df["conformite_score"].apply(classify)
        logger.info("✓ Classification effectuée")
        return self.df

    def compute_statistics(self) -> dict:
        """
        Calcule les statistiques globales de conformité.

        Returns:
            Dict avec KPIs globaux
        """
        total = len(self.df)
        conformes = (self.df["conformite_score"] >= 90).sum()
        critiques = (self.df["conformite_score"] < 50).sum()
        a_ameliorer = ((self.df["conformite_score"] >= 50) & (self.df["conformite_score"] < 90)).sum()

        taux_conformite = (conformes / total * 100) if total > 0 else 0
        score_moyen = self.df["conformite_score"].mean()

        stats = {
            "total_documents": total,
            "documents_conformes": conformes,
            "documents_a_ameliorer": a_ameliorer,
            "documents_critiques": critiques,
            "taux_conformite_pct": round(taux_conformite, 2),
            "score_moyen": round(score_moyen, 2),
            "score_min": int(self.df["conformite_score"].min()) if total > 0 else 0,
            "score_max": int(self.df["conformite_score"].max()) if total > 0 else 0,
        }

        logger.info("\n" + "=" * 60)
        logger.info("STATISTIQUES GLOBALES DE CONFORMITÉ")
        logger.info("=" * 60)
        logger.info(f"Total documents          : {stats['total_documents']}")
        logger.info(f"  ✅ Conformes            : {stats['documents_conformes']} ({taux_conformite:.1f}%)")
        logger.info(f"  ⚠️  À améliorer         : {stats['documents_a_ameliorer']}")
        logger.info(f"  🔴 Critiques            : {stats['documents_critiques']}")
        logger.info(f"Score moyen              : {stats['score_moyen']:.2f}/100")
        logger.info(f"Plage                    : {stats['score_min']}-{stats['score_max']}")
        logger.info("=" * 60)

        return stats

    def run(self) -> tuple:
        """
        Exécute le pipeline complet de scoring.

        Returns:
            Tuple (df_scored, statistics)
        """
        self.calculate_document_scores()
        self.classify_documents()
        stats = self.compute_statistics()

        return self.df, stats
