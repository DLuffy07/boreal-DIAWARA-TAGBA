# Orchestration et exploitation

## Ce qui déclenche le pipeline

| Déclencheur | Commande | Usage |
|---|---|---|
| Arrivée d'un nouveau fichier | `python orchestration/watch.py` | Surveillance continue de `data/sources/` (toutes les 30 s) |
| Planification mensuelle | `python orchestration/watch.py --once` | Lancée par le planificateur le 2 de chaque mois à 6 h |
| Manuel | `python pipeline.py all` | Reconstruction complète |
| Rechargement d'un mois | `python pipeline.py reload --month AAAA_MM` | Fichier corrigé relivré par la comptabilité |

`watch.py` compare l'empreinte SHA-256 de chaque fichier à celle enregistrée dans
`meta.ingestion_log`. Un fichier nouveau ou modifié déclenche `pipeline.py all` ; un fichier
déjà chargé à l'identique ne déclenche rien. Il attend aussi que la taille du fichier soit
stable (copie terminée) avant de lancer.

Le pipeline est idempotent : un déclenchement en trop ne modifie aucune donnée
(test `tests/test_idempotence.py`).

### Planification mensuelle

**Windows (Planificateur de tâches)**, depuis la racine du repo :

```
schtasks /Create /SC MONTHLY /D 2 /ST 06:00 /TN "Boreal pipeline" ^
  /TR "\"%CD%\.venv\Scripts\python.exe\" \"%CD%\orchestration\watch.py\" --once"
```

**Linux / macOS (cron)** :

```
0 6 2 * * cd /chemin/boreal-DIAWARA-TAGBA && .venv/bin/python orchestration/watch.py --once >> logs/cron.log 2>&1
```

## Enchaînement des étapes

```
ingest -> prep -> dedup -> quality -> core -> test -> marts -> docs
```

- Une étape en échec arrête la chaîne : les suivantes ne tournent pas.
- **Tests bloquants** : si un test échoue, les marts ne sont pas reconstruits ; le dashboard
  continue d'afficher la dernière version valide.
- Chaque étape est tracée dans `meta.pipeline_runs`, chaque fichier dans `meta.ingestion_log`,
  chaque règle dans `meta.qualite_resultats`, chaque test dans `meta.test_results`.

## Alertes

En cas d'échec :

1. une ligne est ajoutée dans `logs/alerts.log` (date, lancement, étape, message) ;
2. si la variable d'environnement `BOREAL_ALERT_WEBHOOK` contient l'URL d'un webhook
   entrant (Teams, Slack, Discord), un message y est envoyé ;
3. le processus sort avec le code 1, visible par le planificateur ;
4. la page Exploitation du dashboard affiche le lancement en échec en rouge.

```
set BOREAL_ALERT_WEBHOOK=https://...          (Windows)
export BOREAL_ALERT_WEBHOOK=https://...       (Linux / macOS)
```

## Démonstration en soutenance : fichier livré deux fois

```
python pipeline.py all                         # Résumé : {'SKIPPED': 68} -> rien n'est rechargé
python pipeline.py reload --month 2024_03      # Résumé : {'OK': 1} -> le mois est rejoué
python -m pytest -q tests/test_idempotence.py  # mêmes lignes et mêmes montants avant / après
```

Deux protections se cumulent :
- **même fichier, même contenu** : l'empreinte est déjà connue, le fichier est ignoré ;
- **même paiement dans deux fichiers** (relivraison dans le mois suivant) : la règle Q20 garde
  la première occurrence et met la seconde en quarantaine ; `core.fait_reglement` reste unique
  sur `paiement_id` (test bloquant).
