# KBO Hôtellerie — Pipeline Big Data

Pipeline de données Big Data pour l'analyse financière du secteur hôtelier belge, à partir des données KBO Open Data, des dépôts financiers NBB/CBSO et des statuts notariés.

## Architecture

Bronze (MongoDB brut) → Silver (nettoyé/enrichi) → Gold (ratios financiers)
↓ ↑
Scraping NBB/STAPOR → HDFS → Spark (calcul ratios) ─┘
↓
Orchestration Airflow
↓
API FastAPI → Frontend React

## Stack technique

| Composant                    | Rôle                                                    |
| ---------------------------- | ------------------------------------------------------- |
| MongoDB                      | Stockage Bronze/Silver/Gold, State DB                   |
| HDFS (namenode/datanode)     | Stockage des fichiers bruts (PDF/CSV)                   |
| Apache Spark                 | Calcul des ratios financiers (couche Gold)              |
| Apache Airflow               | Orchestration des pipelines de scraping                 |
| FastAPI                      | API backend (recherche, fiches entreprise, SSE statuts) |
| React + Vite + Redux Toolkit | Frontend                                                |
| Playwright                   | Contournement anti-bot pour le scraping STAPOR          |

## Prérequis

- Docker Desktop
- Python 3.11+ avec un environnement virtuel (`.venv`)
- Node.js 18+ (pour le frontend)

## Installation

### 1. Cloner le dépôt

```bash
git clone <url-du-repo>
cd jour1
```

### 2. Configurer l'environnement Python

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Lancer l'infrastructure Docker

```bash
docker compose up -d
```

Services démarrés :

- MongoDB : `localhost:27017`
- Mongo Express : `http://localhost:8081`
- HDFS NameNode UI : `http://localhost:9870`
- Airflow UI : `http://localhost:8080` (admin/admin)
- Backend FastAPI : `http://localhost:8000/docs`

### 4. Lancer le frontend

```bash
cd frontend
npm install
npm run dev
```

Accessible sur `http://localhost:5173`.

## Pipeline de données

### Jour 1 — Ingestion Bronze

1. Import des CSV KBO Open Data → MongoDB (`import_kbo.py`)
2. Indexation des collections (`create_indexes.py`)
3. Jointure entreprise + établissements + adresses + activités → `entreprises_full` (`build_entreprises_full.py`)
4. Initialisation de la State DB pour le tracking idempotent (`init_state_db.py`, `state_manager.py`)
5. Scraping NBB (comptes annuels) et STAPOR (statuts notariés) (`consult.py`, `stapor.py`)

### Jour 2 — Silver + ciblage sectoriel

1. Nettoyage et enrichissement → `enterprise_silver` (`build_enterprise_silver.py`) : normalisation des dates, déduplication des activités, adresse unique, labels décodés
2. Filtrage du secteur hôtelier (9 codes NACE) → `entreprises_hotellerie` (`filter_hotellerie.py`)
3. Seeding de la State DB avec les entreprises ciblées (`seed_state_hotellerie.py`)
4. Scraping NBB ciblé (dépôts ≥ 2021) avec upload HDFS Bronze (`consult.py::run_hotellerie_scraping`)

### Jour 3 — Gold + API + Frontend

1. Job Spark : lecture des CSV PCMN depuis HDFS, calcul des ratios financiers, consolidation par entreprise → `hotel_gold` (`spark_jobs/spark_gold_job.py`)
2. API FastAPI : recherche, fiche entreprise, streaming SSE des statuts notariés (`backend/`)
3. Frontend React : recherche, fiche entreprise avec tableau de ratios

## Structure du projet

├── docker-compose.yml
├── hadoop.env
├── Dockerfile.airflow
├── Dockerfile.spark
├── Dockerfile.backend
│
├── import_kbo.py # Import CSV KBO → MongoDB
├── create_indexes.py # Indexation MongoDB
├── build_entreprises_full.py # Jointure Bronze
├── build_enterprise_silver.py # Nettoyage Silver
├── filter_hotellerie.py # Filtrage secteur hôtelier
├── inspect_schema.py # Utilitaire d'inspection MongoDB
│
├── init_state_db.py # Init State DB
├── seed_state_hotellerie.py # Seeding State DB hôtellerie
├── state_manager.py # Fonctions de tracking (pending/done/error)
├── state_report.py # Rapport d'avancement
│
├── mongo_utils.py # Connexion MongoDB partagée
├── hdfs_utils.py # Upload HDFS partagé
│
├── consult.py # Scraper NBB/CBSO (comptes annuels)
├── stapor.py # Scraper STAPOR (statuts notariés)
│
├── spark_jobs/
│ └── spark_gold_job.py # Calcul ratios financiers (Gold)
│
├── dags/
│ └── kbo_hotellerie_dag.py # DAG Airflow
│
├── backend/
│ ├── main.py # App FastAPI
│ ├── database.py # Connexion MongoDB backend
│ ├── schemas.py # Modèles Pydantic
│ └── routers/
│ ├── entreprises.py # Recherche + fiche entreprise
│ └── statuts.py # Streaming SSE statuts notariés
│
└── frontend/
└── src/
├── app/store.js
├── features/
│ ├── search/SearchPage.jsx
│ └── entreprise/
│ ├── EntreprisePage.jsx
│ └── entrepriseSlice.js
└── App.jsx

## Collections MongoDB

| Collection                                                                                                | Couche | Contenu                                                       |
| --------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------- |
| `enterprise`, `establishment`, `address`, `activity`, `denomination`, `branch`, `contact`, `code`, `meta` | Bronze | Import brut KBO Open Data                                     |
| `entreprises_full`                                                                                        | Bronze | Jointure consolidée par entreprise                            |
| `enterprise_silver`                                                                                       | Silver | Données nettoyées, dates normalisées, labels décodés          |
| `entreprises_hotellerie`                                                                                  | Silver | Sous-ensemble filtré secteur hôtelier                         |
| `download_state`                                                                                          | Meta   | Tracking des téléchargements (pending/in_progress/done/error) |
| `hotel_gold`                                                                                              | Gold   | Ratios financiers consolidés par entreprise                   |

## Structure HDFS

## Collections MongoDB

| Collection                                                                                                | Couche | Contenu                                                       |
| --------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------- |
| `enterprise`, `establishment`, `address`, `activity`, `denomination`, `branch`, `contact`, `code`, `meta` | Bronze | Import brut KBO Open Data                                     |
| `entreprises_full`                                                                                        | Bronze | Jointure consolidée par entreprise                            |
| `enterprise_silver`                                                                                       | Silver | Données nettoyées, dates normalisées, labels décodés          |
| `entreprises_hotellerie`                                                                                  | Silver | Sous-ensemble filtré secteur hôtelier                         |
| `download_state`                                                                                          | Meta   | Tracking des téléchargements (pending/in_progress/done/error) |
| `hotel_gold`                                                                                              | Gold   | Ratios financiers consolidés par entreprise                   |

## Structure HDFS

/bronze/nbb/{bce}/ # Comptes annuels génériques
/bronze/stapor/{bce}/ # Statuts notariés
/bronze/hotellerie/{bce}/{year}/{ref}.csv # Comptes annuels secteur hôtelier

## Commandes utiles

```bash
# Suivi de l'avancement du scraping
python state_report.py

# Relancer le scraping hôtellerie (reprend automatiquement où il s'est arrêté)
python consult.py

# Recalculer la couche Gold
docker exec -it spark-job python /app/spark_gold_job.py

# Vérifier le contenu HDFS
docker exec -it namenode hdfs dfs -ls -R /bronze

# Accéder à mongosh
docker exec -it mongodb mongosh -u admin -p motdepasse --authenticationDatabase admin
```

## Notes

- Le pipeline de scraping est **idempotent** : chaque script vérifie la State DB avant de retélécharger un document déjà traité.
- Le scraping NBB et STAPOR gère les rate-limits (429) avec backoff automatique.
- Les identifiants MongoDB utilisés dans ce projet (`admin`/`motdepasse`) sont à usage de développement local uniquement.
