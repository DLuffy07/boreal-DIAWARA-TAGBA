# Boréal Assurances : entrepôt, analyses et dashboard

Projet M2 Data Engineering & Data Analyse, en binôme : Charles-Edouard TAGBA (A) et Madiouma DIAWARA (B).

Un entrepôt DuckDB alimenté par un pipeline reproductible et testé, construit à partir des 68 fichiers
sources de Boréal Assurances (extraction au 30/06/2025), une analyse descriptive du portefeuille auto
et habitation, et un dashboard Streamlit branché uniquement sur l'entrepôt.

## Prérequis

- Python 3.10 ou plus récent
- Git

Aucune base de données ni aucun serveur à installer : l'entrepôt est un fichier, `boreal.duckdb`,
créé par le pipeline.

## Lancer le projet (5 commandes)

Windows :

```bat
git clone https://github.com/DLuffy07/boreal-DIAWARA-TAGBA.git && cd boreal-DIAWARA-TAGBA
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python pipeline.py all
streamlit run dashboard/app.py
```

macOS / Linux : remplacer la 2e ligne par `python3 -m venv .venv && source .venv/bin/activate`.

**Résultat attendu** de `python pipeline.py all` (environ 30 secondes) : le tableau des 29 règles de
qualité, `61 passed`, puis `Pipeline OK`. Le dashboard s'ouvre ensuite dans le navigateur.

## Ce que fait `python pipeline.py all`

```
ingest -> prep -> dedup -> quality -> core -> test -> marts -> analyses -> docs
```

| Étape | Rôle |
|---|---|
| `ingest` | Charge les 68 fichiers dans la couche brute (`raw`), sans transformation, avec fichier d'origine et date de chargement sur chaque ligne |
| `prep` | Type et normalise les données, sans filtrer |
| `dedup` | Rapproche les clients en double (`prep.client_mapping`) |
| `quality` | Applique les 29 règles de qualité ; les lignes écartées vont en quarantaine avec leur motif |
| `core` | Construit le schéma en étoile (5 dimensions, 3 tables de faits) |
| `test` | Lance les 61 tests ; **un échec arrête la chaîne** |
| `marts` | Construit les tables d'analyse et d'exploitation |
| `analyses` | Calcule les indicateurs L3/L4 (intervalles de confiance, décomposition du S/P, cohortes...) et les exports CSV |
| `docs` | Régénère le catalogue des données |

Relancer le pipeline ne change rien : un fichier déjà chargé à l'identique est ignoré.

## Commandes utiles

```bash
python pipeline.py reload --month 2024_03   # rejoue un mois de règlements (idempotent)
python -m pytest -q tests                   # tests seuls
python orchestration/watch.py               # lance le pipeline à l'arrivée d'un nouveau fichier
python orchestration/watch.py --once        # une vérification, pour une planification mensuelle
```

Planification mensuelle (Planificateur de tâches Windows ou cron) et alertes : voir `docs/orchestration.md`.

## Où trouver quoi

| Dossier | Contenu | Auteur |
|---|---|---|
| `data/sources/` | Les 68 fichiers sources (CRM, contrats, sinistres, règlements, audits) | — |
| `ingestion/` | Chargement des sources dans `raw`, journal d'ingestion | A |
| `sql/prep/` | Typage et normalisation | A |
| `quality/` | 29 règles de qualité (`rules.yaml`), quarantaine ; déduplication des clients (`dedup_clients.py`) | A ; B pour la déduplication |
| `sql/core/` | Schéma en étoile, exposition, historique des clients (SCD2) | A |
| `sql/marts/` | Marts d'analyse et du dashboard (B), marts d'exploitation (`90_exploitation.sql`, A) | A + B |
| `analyses/` | Scripts Python des analyses L3/L4 | B |
| `dashboard/` | Application Streamlit (`app.py`) : pages Portefeuille, Technique et clients, Exploitation | B ; A pour les marts d'exploitation |
| `tests/` | 61 tests bloquants : `test_core.py`, `test_idempotence.py` (A), `test_*_b.py`, `test_mart_segments.py` (B) | A + B |
| `orchestration/` | Déclenchement automatique à l'arrivée d'un fichier | A |
| `pipeline.py` | Point d'entrée unique, journal des étapes, alertes | A |
| `docs/` | Contrat de données, catalogue, lignage du S/P, orchestration, RGPD | A + B |
| `outputs/` | Exports CSV des analyses (générés, non versionnés) | — |
| `logs/` | `alerts.log` en cas d'échec, résultats des tests (générés, non versionnés) | — |

## Documentation

| Fichier | Contenu |
|---|---|
| `docs/contrat.md` | Définition des tables et des indicateurs (exposition, prime acquise, S/P, fréquence...) |
| `docs/catalogue.md` | Chaque table et chaque colonne de l'entrepôt, régénéré à chaque lancement |
| `docs/lignage_sp.md` | Parcours du ratio S/P, du fichier source au graphique |
| `docs/orchestration.md` | Déclencheurs, planification, alertes, démonstration « fichier livré deux fois » |
| `docs/rgpd.md` | Données personnelles, pseudonymisation, conservation, droit à l'effacement |

Le dossier d'analyse est rendu à part : `DIAWARA_TAGBA_Boreal.pdf`.

## Où regarder dans l'entrepôt

| Besoin | Table |
|---|---|
| Fichiers chargés, lignes lues et rejetées | `meta.ingestion_log` |
| Étapes de chaque lancement | `meta.pipeline_runs` |
| Volume de chaque règle de qualité | `meta.qualite_resultats` |
| Lignes écartées et leur motif | `quarantine.anomalies`, `quarantine.lignes_exclues` |
| Résultat de chaque test | `meta.test_results` |

## Règles Git

- Pas de push direct sur `main` : une branche par tâche (`feat/...`, `fix/...`), puis une pull request relue par l'autre.
- Commits courts : `feat(l1): ...`, `fix(l2): ...`, `docs: ...`.
- `boreal.duckdb`, `outputs/` et `logs/` ne sont pas versionnés : ils sont régénérés par `python pipeline.py all`.
