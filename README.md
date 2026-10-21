# Boréal Assurances : entrepôt, analyses et dashboard

Projet M2 Data Engineering & Data Analyse (binôme).

## Lancer le projet (5 commandes)

```bash
git clone <url-du-repo> && cd boreal-NOM1-NOM2
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt
make all
make dashboard
```

## Architecture

Sources -> raw (copie fidèle) -> prep -> core (étoile) -> marts -> dashboard

| Dossier | Contenu | Responsable |
|---|---|---|
| `ingestion/` | Chargement des sources dans `raw`, journal | A |
| `sql/prep/` | Typage, normalisation | A |
| `quality/` | Règles qualité, quarantaine | A |
| `sql/core/` | Schéma en étoile | A |
| `tests/` | Tests bloquants | A |
| `sql/marts/` | Tables pour le dashboard et le dossier | B |
| `analyses/` | Notebooks L3 / L4 | B |
| `dashboard/` | Application Streamlit | B |
| `docs/` | Contrat de données, catalogue, lignage, RGPD | A + B |

Définitions des indicateurs : voir `docs/contrat.md`.

## Règles Git

- Pas de push direct sur `main` : une branche par tâche (`feat/...`), puis pull request relue par l'autre.
- Commits courts : `feat(l1): ...`, `fix(l2): ...`, `docs: ...`.
- `boreal.duckdb` n'est pas versionné : il est régénéré par `make all`.
