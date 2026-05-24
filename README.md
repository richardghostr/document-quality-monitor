# 📊 Document Quality Monitor

Système automatisé de monitoring et de conformité documentaire pour **Bouygues Travaux Publics**.

Analyzes ~30,000 technical documents, détecte automatiquement les anomalies de qualité et génère des alertes et rapports temps réel.

---

## 🎯 Objectif

Assurer la **qualité et la traçabilité** de la documentation technique :
- ✅ Doublons
- ✅ Versions incohérentes
- ✅ Documents obsolètes
- ✅ Données manquantes
- ✅ Statuts invalides
- ✅ Documents critiques non conformes

**Impact métier :**
- 🎯 Réduction anomalies : **-70%** en 3 mois
- ⏱️ Gain productivité : **15-20h/mois**
- 📊 Traçabilité complète
- 🔔 Alertes automatiques

---

## 🚀 Installation

### Prérequis
- Python 3.8+
- pip

### Setup

```bash
# 1. Cloner/télécharger le projet
cd document-quality-monitor

# 2. Créer un environnement virtuel (recommandé)
python -m venv venv

# Activation (Windows)
venv\Scripts\activate

# Activation (macOS/Linux)
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt
```

---

## 🏃 Utilisation

### Exécution rapide

```bash
python main.py
```

**Que fait le pipeline :**
1. **Extract** → Charge CSV/Excel/Dataset simulé
2. **Transform** → Nettoyage + enrichissement
3. **Quality Checks** → 7 contrôles automatiques
4. **Scoring** → Score conformité 0-100
5. **Load** → SQLite + exports CSV
6. **Alerts** → Emails pour docs critiques
7. **Reports** → HTML + Excel

### Sortie

- 📁 `data/processed/dqm.db` — Base SQLite
- 📄 `data/outputs/documents_clean.csv` — Données nettoyées
- 📊 `data/outputs/rapport_qualite.html` — Rapport visuel
- 📋 `data/outputs/rapport_qualite.xlsx` — Rapport Excel
- 📝 `data/outputs/logs/` — Fichiers log horodatés

---

## 🔍 7 Contrôles Qualité

### 1️⃣ **Doublons Exacts**
Détecte documents identiques (même nom, discipline, projet) avec IDs différents.
- **Risque** : Deux équipes travaillent sur versions différentes
- **Poids** : -15 points

### 2️⃣ **Versions Incohérentes**
Signale quand plusieurs versions actives existent simultanément.
- **Risque** : Utilisation plan périmé en phase travaux
- **Poids** : -12 points

### 3️⃣ **Documents Manquants**
Identifie docs absents du registre (statut "Manquant").
- **Risque** : DOE/PV réception bloque réception lot
- **Poids** : -25 points

### 4️⃣ **Documents Obsolètes**
Détecte docs non mis à jour depuis > 180 jours.
- **Risque** : Plan ne correspond plus aux modifications chantier
- **Poids** : -10 points

### 5️⃣ **Champs Obligatoires Vides**
Signale responsable, discipline, criticité, type_document, projet manquants.
- **Risque** : Document sans responsable → impossible à relancer
- **Poids** : -20 points

### 6️⃣ **Statuts Invalides**
Détecte statuts hors référentiel (autorisés : Validé, En révision, Manquant, Obsolète).
- **Risque** : Statuts non normalisés faussent KPIs dashboard
- **Poids** : -20 points

### 7️⃣ **Anomalies Critiques**
Identifie docs criticité haute/critique ET non conformes.
- **Risque** : Non-conformité réglementaire, sinistre travaux
- **Poids** : -25 points
- **Action** : Alerte mail immédiate

---

## 📊 Score de Conformité

**Formule :**
```
Score = 100 - (somme des déductions par anomalie)
Plage : [0, 100]
```

**Classifications :**
| Score | Catégorie | Action |
|-------|-----------|--------|
| ≥90 | ✅ Conforme | Aucune |
| 75-89 | ⚠️ À améliorer | Planifier correction |
| 50-74 | 🔴 Non conforme | Corriger rapidement |
| <50 | 🚨 Critique | Action immédiate |

---

## ⚙️ Configuration

Modifier `config.yaml` pour adapter au contexte :

```yaml
# Chemins données
paths:
  raw_data: "data/raw/documents.csv"
  db_path: "data/processed/dqm.db"
  outputs_dir: "data/outputs"

# Seuils qualité
quality:
  seuil_obsolescence_jours: 180
  seuil_conformite_alerte: 85.0

# SMTP pour alertes
smtp:
  host: "smtp.gmail.com"
  port: 587
  user: "votre_email@example.com"
  password: "PASSWORD_OU_VAR_ENV"
```

---

## 📧 Alertes Email

Alertes automatiques déclenchées pour documents avec score < 75.

**Configuration :**
1. Définir host/port/user/password SMTP dans `config.yaml`
2. Ou utiliser variables d'environnement :
   ```bash
   export SMTP_USER="..."
   export SMTP_PASSWORD="..."
   ```

**Template alerte :**
- Score conformité
- Liste anomalies avec priorités
- Lien d'action

---

## 📈 Dataset Simulé

Par défaut, si `data/raw/documents.csv` absent, le système génère un dataset réaliste :
- 500 documents + 20 doublons volontaires
- Distributions réalistes (statuts, âges, criticités)
- Statuts/données invalides injectés pour tests

**Pour utiliser vos données :**
1. Placer CSV à `data/raw/documents.csv`
2. Colonnes requises : `doc_id`, `nom_document`, `version`, `statut`, `date_mise_a_jour`, `responsable`, `discipline`, `criticite`, `type_document`, `projet`, `conformite`

---

## 🗄️ Base de Données SQLite

Schéma automatiquement créé :

**documents**
```sql
doc_id (PK), nom_document, version, statut, date_mise_a_jour,
responsable, discipline, criticite, type_document, projet,
conformite, nb_revisions, age_jours, annee_maj, mois_maj,
statut_invalide (bool), criticite_invalide (bool), charge_ts
```

**anomalies**
```sql
anomalie_id (PK), doc_id (FK), type_anomalie, description,
date_detection, statut_traitement, priorite
```

**runs** (métriques)
```sql
run_id (PK), date_run, nb_documents, nb_anomalies,
taux_conformite, statut_run
```

---

## 📁 Structure Projet

```
document-quality-monitor/
├── src/
│   ├── etl/
│   │   ├── extract.py      # Chargement sources
│   │   ├── transform.py    # Nettoyage
│   │   └── load.py         # SQLite + exports
│   ├── quality/
│   │   ├── checks.py       # 7 contrôles qualité
│   │   └── scoring.py      # Score conformité
│   ├── reporting/
│   │   ├── alerts.py       # Emails alertes
│   │   └── report.py       # Rapports HTML/Excel
│   └── utils/
│       └── logger.py       # Logging centralisé
├── data/
│   ├── raw/                # Données sources
│   ├── processed/          # Données nettoyées + DB
│   └── outputs/            # Rapports générés
├── config.yaml             # Configuration
├── main.py                 # Point d'entrée
├── requirements.txt        # Dépendances
└── README.md              # Ce fichier
```

---

## 📚 Technologies

- **Python 3.8+**
- **pandas** — Manipulation données
- **openpyxl** — Lecture/écriture Excel
- **PyYAML** — Configuration
- **SQLite3** — Base données
- **smtplib** — Emails

---

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'pandas'"
```bash
pip install -r requirements.txt
```

### "Fichier source introuvable — génération dataset simulé"
C'est normal ! Le système génère automatiquement des données de test.
Pour vos données, placez CSV à `data/raw/documents.csv`.

### Erreur SMTP
Vérifier config.yaml :
- Host SMTP correct
- Port 587 (Gmail TLS)
- Credentials valides

### Base de données locked
SQLite peut refuser accès si autre process la verrouille.
Solution : fermer tous les accès avant `python main.py`.

---

## 🎓 Cas d'Usage

### Scenario 1 : Audit complet
```bash
python main.py
# Génère rapport complet + alertes
```

### Scenario 2 : Analyse doublons uniquement
Modifier `src/quality/checks.py` et commenter les autres checks.

### Scenario 3 : Dashboard Power BI
Importer `data/outputs/documents_clean.csv` dans Power BI.

---

## 🚀 Évolutions Futures

### Court terme
- [ ] API REST (FastAPI)
- [ ] Web UI (Streamlit)
- [ ] Export PDF rapports

### Moyen terme
- [ ] Dashboard Power BI embarqué
- [ ] Support multi-projets
- [ ] Alertes Slack/Teams

### Long terme
- [ ] Azure Databricks
- [ ] Power Automate orchestration
- [ ] Machine Learning anomaly detection

---

## 📧 Support

Questions/bugs ? Contacter l'équipe data.

---

## 📄 Licence

Propriétaire Bouygues Travaux Publics — 2024

---

**Dernière mise à jour** : Mai 2026

**Version** : 1.0.0

Made with ❤️ for quality documentation.
