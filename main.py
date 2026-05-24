"""
Document Quality Monitor — Point d'entrée principal

Pipeline complet :
1. Extraction (CSV/Excel/Simulé)
2. Transformation (nettoyage, enrichissement)
3. Contrôles Qualité (7 checks)
4. Scoring (conformité 0-100)
5. Chargement (SQLite + exports)
6. Alertes (email optionnel)
7. Rapports (HTML + Excel)
"""

import sys
from pathlib import Path

# Ajouter le répertoire projet au path
sys.path.insert(0, str(Path(__file__).parent))

from src.etl.extract import load_config, extract
from src.etl.transform import transform
from src.etl.load import (
    load_documents,
    load_anomalies,
    export_csv,
    export_excel,
    export_power_bi_bundle,
)
from src.quality.checks import run_all_checks
from src.quality.scoring import ScoringEngine
from src.reporting.alerts import AlertingSystem
from src.reporting.report import ReportGenerator
from src.utils.logger import get_logger

logger = get_logger("main")


def run_pipeline():
    """Exécute le pipeline complet ETL + Qualité + Reporting."""

    logger.info("\n" + "=" * 70)
    logger.info("🚀 DOCUMENT QUALITY MONITOR - Pipeline de conformité documentaire")
    logger.info("=" * 70)

    try:
        # ─────────────────────────────────────────────────────────────────────
        # 1. CHARGEMENT CONFIGURATION
        # ─────────────────────────────────────────────────────────────────────
        logger.info("\n[1/8] Chargement configuration...")
        config = load_config("config.yaml")
        logger.info("✓ Configuration chargée")

        # ─────────────────────────────────────────────────────────────────────
        # 2. EXTRACTION
        # ─────────────────────────────────────────────────────────────────────
        logger.info("\n[2/8] Extraction données sources...")
        df_raw = extract(config)
        logger.info(f"✓ {len(df_raw)} documents extraits")

        # ─────────────────────────────────────────────────────────────────────
        # 3. TRANSFORMATION
        # ─────────────────────────────────────────────────────────────────────
        logger.info("\n[3/8] Transformation (nettoyage + enrichissement)...")
        df_clean, mapping_report = transform(df_raw, config=config)
        logger.info(f"✓ {len(df_clean)} documents transformés")

        # ─────────────────────────────────────────────────────────────────────
        # 4. CONTRÔLES QUALITÉ (7 checks)
        # ─────────────────────────────────────────────────────────────────────
        logger.info("\n[4/8] Lancement des 7 contrôles qualité...")
        anomalies = run_all_checks(df_clean, config, mapping_report=mapping_report)
        logger.info(f"✓ {len(anomalies)} anomalies détectées")

        # ─────────────────────────────────────────────────────────────────────
        # 5. SCORING & CLASSIFICATION
        # ─────────────────────────────────────────────────────────────────────
        logger.info("\n[5/8] Calcul des scores de conformité...")
        scorer = ScoringEngine(df_clean, anomalies)
        df_scored, stats = scorer.run()
        logger.info("✓ Scoring et classification terminés")

        # ─────────────────────────────────────────────────────────────────────
        # 6. CHARGEMENT BASE DE DONNÉES + EXPORTS CSV/EXCEL
        # ─────────────────────────────────────────────────────────────────────
        logger.info("\n[6/8] Chargement base données et exports...")
        db_path = config["paths"]["db_path"]
        load_documents(df_scored, db_path)
        load_anomalies(anomalies, db_path)

        output_dir = config["paths"]["outputs_dir"]
        export_csv(df_scored, output_dir)
        export_excel(df_scored, anomalies, output_dir)
        export_power_bi_bundle(df_scored, anomalies, output_dir, mapping_report=mapping_report)
        logger.info(f"✓ Base SQLite et exports générés")

        # ─────────────────────────────────────────────────────────────────────
        # 7. ALERTES EMAIL (optionnel)
        # ─────────────────────────────────────────────────────────────────────
        logger.info("\n[7/8] Traitement des alertes...")
        try:
            alerting_enabled = config.get("alerting", {}).get("enabled", False)
            if alerting_enabled:
                alerter = AlertingSystem(config)
                seuil = config.get("alerting", {}).get("alert_threshold_score", 75)
                alerter.send_alerts_for_critical_docs(df_scored, anomalies, seuil_score=seuil)
                logger.info("✓ Alertes traitées")
            else:
                logger.info("⊘ Alertes désactivées dans config")
        except Exception as e:
            logger.error(f"⚠️  Erreur traitement alertes : {e}")

        # ─────────────────────────────────────────────────────────────────────
        # 8. RAPPORTS HTML + EXCEL
        # ─────────────────────────────────────────────────────────────────────
        logger.info("\n[8/8] Génération des rapports...")
        report_gen = ReportGenerator(df_scored, anomalies, stats, output_dir, mapping_report=mapping_report)
        report_gen.generate_html_report()
        report_gen.export_excel_report()
        logger.info("✓ Rapports générés")

        # ─────────────────────────────────────────────────────────────────────
        # SUCCÈS
        # ─────────────────────────────────────────────────────────────────────
        logger.info("\n" + "=" * 70)
        logger.info("✅ PIPELINE EXÉCUTÉ AVEC SUCCÈS")
        logger.info("=" * 70)
        logger.info(f"\n📊 RÉSUMÉ FINAL :")
        logger.info(f"  • Total documents : {stats['total_documents']}")
        logger.info(f"  • Conformes : {stats['documents_conformes']} ({stats['taux_conformite_pct']:.1f}%)")
        logger.info(f"  • Anomalies détectées : {len(anomalies)}")
        logger.info(f"  • Fichiers générés : {output_dir}/")
        logger.info(f"\n💾 Base données : {db_path}")
        logger.info("=" * 70 + "\n")

        return 0

    except Exception as e:
        logger.error("\n" + "=" * 70)
        logger.error("❌ ERREUR CRITIQUE — Pipeline interrompu")
        logger.error("=" * 70, exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = run_pipeline()
    sys.exit(exit_code)
