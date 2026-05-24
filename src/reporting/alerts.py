"""
reporting/alerts.py
Système d'alertes automatiques par email pour documents critiques.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("reporting.alerts")


class AlertingSystem:
    """Gère l'envoi d'alertes email pour documents critiques."""

    def __init__(self, config: dict):
        """
        Initialise le système d'alertes avec config SMTP.

        Args:
            config: Dict contenant les paramètres SMTP
        """
        self.smtp_config = config.get("smtp", {})
        self.smtp_host = self.smtp_config.get("host", "smtp.gmail.com")
        self.smtp_port = self.smtp_config.get("port", 587)
        self.sender_email = self.smtp_config.get("projetpython12345@gmail.com")
        self.sender_password = self.smtp_config.get("esjk jtgz syvw lbmq")
        self.destinataires_defaut = self.smtp_config.get("destinataires_defaut", [])
        self.sujet_prefixe = self.smtp_config.get("sujet_prefixe", "[DQM]")

    def send_email(self, recipient: str, subject: str, body_html: str) -> bool:
        """
        Envoie un email via SMTP.

        Args:
            recipient: Email destinataire
            subject: Sujet du message
            body_html: Corps HTML du message

        Returns:
            True si succès, False sinon
        """
        if not self.sender_email or not self.sender_password:
            logger.warning("Config SMTP incomplète — alertes désactivées")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = recipient

            # Ajout du contenu HTML
            html_part = MIMEText(body_html, "html", "utf-8")
            msg.attach(html_part)

            # Envoi via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient, msg.as_string())

            logger.info(f"✓ Email envoyé à {recipient}")
            return True

        except Exception as e:
            logger.error(f"✗ Erreur envoi email à {recipient} : {e}")
            return False

    def generate_alert_email(self, doc: pd.Series, anomalies: pd.DataFrame) -> str:
        """
        Génère un email HTML pour document critique.

        Args:
            doc: Ligne du DataFrame (document)
            anomalies: DataFrame des anomalies pour ce doc

        Returns:
            String HTML
        """
        doc_id = doc.get("doc_id", "N/A")
        nom = doc.get("nom_document", "Document sans nom")
        score = doc.get("conformite_score", 0)
        responsable = doc.get("responsable", "Non assigné")
        projet = doc.get("projet", "N/A")
        criticite = doc.get("criticite", "N/A")

        # Lister les anomalies
        anomalies_doc = anomalies[anomalies["doc_id"] == doc_id]
        rows_html = ""
        for _, anom in anomalies_doc.iterrows():
            rows_html += f"""
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 10px; background: #f9f9f9;">{anom.get('type_anomalie', '')}</td>
                <td style="padding: 10px;">{anom.get('description', '')}</td>
                <td style="padding: 10px; text-align: center;"><strong>{anom.get('priorite', '')}</strong></td>
            </tr>
            """

        # Couleur du badge score
        if score >= 90:
            color_badge = "#28a745"  # Vert
        elif score >= 75:
            color_badge = "#ffc107"  # Orange
        elif score >= 50:
            color_badge = "#fd7e14"  # Rouge-orange
        else:
            color_badge = "#dc3545"  # Rouge

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #003366; color: white; padding: 15px; border-radius: 5px; }}
                .header h2 {{ margin: 0; }}
                .score-badge {{
                    display: inline-block;
                    background: {color_badge};
                    color: white;
                    padding: 10px 15px;
                    border-radius: 5px;
                    font-size: 18px;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                .metadata {{ background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 3px; }}
                .metadata p {{ margin: 5px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th {{ background: #003366; color: white; padding: 10px; text-align: left; }}
                .action {{ margin-top: 20px; padding: 15px; background: #fff3cd; border-left: 4px solid #ffc107; }}
                .footer {{ font-size: 12px; color: #999; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🚨 Alerte Qualité Documentaire</h2>
                </div>

                <h3>Document : {nom}</h3>

                <div class="metadata">
                    <p><strong>ID :</strong> {doc_id}</p>
                    <p><strong>Projet :</strong> {projet}</p>
                    <p><strong>Responsable :</strong> {responsable}</p>
                    <p><strong>Criticité :</strong> {criticite}</p>
                </div>

                <p><strong>Score de Conformité :</strong></p>
                <div class="score-badge">{score:.0f} / 100</div>

                <h3>Anomalies Détectées :</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Type d'Anomalie</th>
                            <th>Description</th>
                            <th>Priorité</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>

                <div class="action">
                    <strong>⚠️ Action requise :</strong>
                    <p>Veuillez corriger les anomalies identifiées et mettre à jour le document dans le registre.</p>
                </div>

                <div class="footer">
                    <p>Message généré automatiquement par Document Quality Monitor</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html_body

    def send_alerts_for_critical_docs(self, df: pd.DataFrame, anomalies: pd.DataFrame,
                                      seuil_score: float = 75) -> Dict[str, bool]:
        """
        Envoie alertes pour tous les documents sous le seuil de score.

        Args:
            df: DataFrame des documents scorés
            anomalies: DataFrame des anomalies
            seuil_score: Seuil de score déclenchant alerte (défaut: 75)

        Returns:
            Dict doc_id -> True/False (succès/échec envoi)
        """
        logger.info(f"Traitement des alertes (seuil: {seuil_score})...")

        docs_alerte = df[df["conformite_score"] < seuil_score].copy()

        if docs_alerte.empty:
            logger.info("Aucun document en alerte.")
            return {}

        resultats = {}

        for idx, doc in docs_alerte.iterrows():
            doc_id = doc["doc_id"]
            email_responsable = doc.get("responsable_email")

            # Fallback sur destinataires par défaut si email responsable absent
            if pd.isna(email_responsable) or not email_responsable:
                if self.destinataires_defaut:
                    email_responsable = self.destinataires_defaut[0]
                    logger.warning(f"Email responsable absent pour {doc_id}, utilisation défaut")
                else:
                    logger.warning(f"Email responsable absent et aucun défaut — alerte non envoyée pour {doc_id}")
                    resultats[doc_id] = False
                    continue

            # Générer email HTML
            body = self.generate_alert_email(doc, anomalies)

            # Envoyer
            subject = f"{self.sujet_prefixe} Alerte — {doc['nom_document'][:40]}"
            success = self.send_email(email_responsable, subject, body)
            resultats[doc_id] = success

        logger.info(f"Alertes : {sum(resultats.values())}/{len(resultats)} envoyées avec succès")
        return resultats
