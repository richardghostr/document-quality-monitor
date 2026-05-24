"""
reporting/report.py
Générateur de rapports HTML et Excel pour Document Quality Monitor.
"""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("reporting.report")


class ReportGenerator:
    """Génère des rapports HTML et Excel de synthèse."""

    def __init__(
        self,
        df: pd.DataFrame,
        anomalies: pd.DataFrame,
        stats: dict,
        output_dir: str = "data/outputs",
        mapping_report: dict | None = None,
    ):
        """
        Initialise le générateur de rapports.

        Args:
            df: DataFrame des documents avec scores
            anomalies: DataFrame des anomalies
            stats: Dict de statistiques globales
            output_dir: Répertoire de sortie
        """
        self.df = df
        self.anomalies = anomalies
        self.stats = stats
        self.output_dir = output_dir
        self.mapping_report = mapping_report or {}
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def generate_html_report(self, filename: str = "rapport_qualite.html") -> str:
        """
        Génère un rapport HTML complet et formaté.

        Args:
            filename: Nom du fichier de sortie

        Returns:
            Chemin du fichier généré
        """
        logger.info(f"Génération rapport HTML...")

        # Timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_report = datetime.now().strftime("%d/%m/%Y")

        # KPIs
        total = self.stats.get("total_documents", 0)
        conformes = self.stats.get("documents_conformes", 0)
        critiques = self.stats.get("documents_critiques", 0)
        a_ameliorer = self.stats.get("documents_a_ameliorer", 0)
        taux = self.stats.get("taux_conformite_pct", 0)
        score_moyen = self.stats.get("score_moyen", 0)

        # Couleur taux
        if taux >= 90:
            couleur_taux = "#28a745"
        elif taux >= 75:
            couleur_taux = "#ffc107"
        else:
            couleur_taux = "#dc3545"

        # Top documents critiques
        if "conformite_score" in self.df.columns:
            docs_critiques = self.df[self.df["conformite_score"] < 50].nsmallest(10, "conformite_score")
        else:
            docs_critiques = pd.DataFrame()
        rows_critiques = ""
        for _, row in docs_critiques.iterrows():
            doc_id = row.get("doc_id", "N/A")
            nom_document = str(row.get("nom_document", "N/A"))[:50]
            responsable = row.get("responsable", "N/A")
            score = row.get("conformite_score", 0)
            classification = row.get("classification", "N/A")
            rows_critiques += f"""
            <tr>
                <td>{doc_id}</td>
                <td>{nom_document}</td>
                <td>{responsable}</td>
                <td style="color: red; font-weight: bold;">{score:.0f}</td>
                <td>{classification}</td>
            </tr>
            """

        mapping_rows = ""
        for item in self.mapping_report.get("mapping_details", []):
            mapping_rows += (
                "<tr>"
                f"<td>{item.get('source_column', '')}</td>"
                f"<td>{item.get('standard_column', '')}</td>"
                f"<td>{item.get('method', '')}</td>"
                f"<td>{item.get('confidence', 0)}%</td>"
                "</tr>"
            )

        html = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Document Quality Monitor - Rapport</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: #f5f5f5;
                    color: #333;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                header {{
                    background: linear-gradient(135deg, #003366 0%, #005c99 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 8px;
                    margin-bottom: 30px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                header h1 {{
                    font-size: 28px;
                    margin-bottom: 10px;
                }}
                header p {{
                    font-size: 14px;
                    opacity: 0.9;
                }}
                .kpis {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-bottom: 30px;
                }}
                .kpi-card {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    border-left: 4px solid #003366;
                }}
                .kpi-title {{
                    font-size: 12px;
                    text-transform: uppercase;
                    color: #999;
                    margin-bottom: 8px;
                }}
                .kpi-value {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #003366;
                }}
                .kpi-card.critical {{ border-left-color: #dc3545; }}
                .kpi-card.critical .kpi-value {{ color: #dc3545; }}
                .kpi-card.warning {{ border-left-color: #ffc107; }}
                .kpi-card.warning .kpi-value {{ color: #ffc107; }}
                .kpi-card.success {{ border-left-color: #28a745; }}
                .kpi-card.success .kpi-value {{ color: #28a745; }}
                .section {{
                    background: white;
                    padding: 25px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .section h2 {{
                    font-size: 20px;
                    margin-bottom: 15px;
                    border-bottom: 2px solid #003366;
                    padding-bottom: 10px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 15px;
                }}
                th {{
                    background: #f5f5f5;
                    padding: 12px;
                    text-align: left;
                    font-weight: bold;
                    border-bottom: 2px solid #ddd;
                    font-size: 13px;
                }}
                td {{
                    padding: 10px 12px;
                    border-bottom: 1px solid #eee;
                }}
                tr:hover {{
                    background: #f9f9f9;
                }}
                .badge {{
                    display: inline-block;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                .badge-conforme {{ background: #d4edda; color: #155724; }}
                .badge-ameliorer {{ background: #fff3cd; color: #856404; }}
                .badge-critique {{ background: #f8d7da; color: #721c24; }}
                .progress-bar {{
                    width: 100%;
                    height: 20px;
                    background: #e9ecef;
                    border-radius: 4px;
                    overflow: hidden;
                    margin: 10px 0;
                }}
                .progress-fill {{
                    height: 100%;
                    background: {couleur_taux};
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 12px;
                    font-weight: bold;
                }}
                footer {{
                    margin-top: 40px;
                    padding: 20px;
                    text-align: center;
                    color: #999;
                    font-size: 12px;
                    border-top: 1px solid #eee;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>📊 Document Quality Monitor</h1>
                    <p>Rapport de Conformité Documentaire</p>
                    <p>Généré le {date_report} à {now}</p>
                </header>

                <div class="kpis">
                    <div class="kpi-card success">
                        <div class="kpi-title">Taux de Conformité</div>
                        <div class="kpi-value">{taux:.1f}%</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Total Documents</div>
                        <div class="kpi-value">{total}</div>
                    </div>
                    <div class="kpi-card success">
                        <div class="kpi-title">Conformes</div>
                        <div class="kpi-value">{conformes}</div>
                    </div>
                    <div class="kpi-card warning">
                        <div class="kpi-title">À Améliorer</div>
                        <div class="kpi-value">{a_ameliorer}</div>
                    </div>
                    <div class="kpi-card critical">
                        <div class="kpi-title">Critiques</div>
                        <div class="kpi-value">{critiques}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Score Moyen</div>
                        <div class="kpi-value">{score_moyen:.1f}</div>
                    </div>
                </div>

                <div class="section">
                    <h2>📈 Distribution de Conformité</h2>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {taux}%;">{taux:.1f}%</div>
                    </div>
                </div>

                <div class="section">
                    <h2>🚨 Top 10 Documents Critiques</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Document ID</th>
                                <th>Nom</th>
                                <th>Responsable</th>
                                <th>Score</th>
                                <th>Classification</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_critiques}
                        </tbody>
                    </table>
                </div>

                <div class="section">
                    <h2>🧭 Mapping Automatique Appliqué</h2>
                    <p>Colonnes reconnues : <strong>{len(self.mapping_report.get('source_present_standard_columns', []))}</strong></p>
                    <p>Colonnes non reconnues : <strong>{len(self.mapping_report.get('unmapped_source_columns', []))}</strong></p>
                    {
                        '<table><thead><tr><th>Colonne source</th><th>Colonne standard</th><th>Méthode</th><th>Confiance</th></tr></thead><tbody>'
                        + mapping_rows
                        + '</tbody></table>' if mapping_rows else '<p>Aucun mapping détaillé disponible.</p>'
                    }
                </div>

                <div class="section">
                    <h2>📋 Anomalies Détectées</h2>
                    <p>Total : <strong>{len(self.anomalies)}</strong> anomalies</p>
                    {'<table><thead><tr><th>Doc ID</th><th>Type</th><th>Description</th><th>Priorité</th></tr></thead><tbody>' + ''.join([f'<tr><td>{a["doc_id"]}</td><td>{a["type_anomalie"]}</td><td>{a["description"]}</td><td><span class="badge">{a["priorite"]}</span></td></tr>' for _, a in self.anomalies.iterrows()]) + '</tbody></table>' if not self.anomalies.empty else '<p>Aucune anomalie.</p>'}
                </div>

                <footer>
                    <p>Rapport généré automatiquement par Document Quality Monitor</p>
                </footer>
            </div>
        </body>
        </html>
        """

        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"✓ Rapport HTML généré : {output_path}")
        return output_path

    def export_excel_report(self, filename: str = "rapport_qualite.xlsx") -> str:
        """
        Exporte un rapport Excel multi-feuilles.

        Args:
            filename: Nom du fichier

        Returns:
            Chemin du fichier généré
        """
        logger.info(f"Génération rapport Excel...")

        output_path = os.path.join(self.output_dir, filename)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # Feuille 1 : Résumé statistiques
            stats_df = pd.DataFrame([
                {"Métrique": "Total documents", "Valeur": self.stats["total_documents"]},
                {"Métrique": "Conformes", "Valeur": self.stats["documents_conformes"]},
                {"Métrique": "À améliorer", "Valeur": self.stats["documents_a_ameliorer"]},
                {"Métrique": "Critiques", "Valeur": self.stats["documents_critiques"]},
                {"Métrique": "Taux conformité (%)", "Valeur": self.stats["taux_conformite_pct"]},
                {"Métrique": "Score moyen", "Valeur": self.stats["score_moyen"]},
            ])
            stats_df.to_excel(writer, sheet_name="Résumé", index=False)

            # Feuille 2 : Tous les documents
            self.df.to_excel(writer, sheet_name="Documents", index=False)

            # Feuille 3 : Anomalies
            if not self.anomalies.empty:
                self.anomalies.to_excel(writer, sheet_name="Anomalies", index=False)

            # Feuille 4 : Documents critiques
            docs_critiques = self.df[self.df["conformite_score"] < 50]
            if not docs_critiques.empty:
                docs_critiques.to_excel(writer, sheet_name="Critiques", index=False)

        logger.info(f"✓ Rapport Excel généré : {output_path}")
        return output_path
