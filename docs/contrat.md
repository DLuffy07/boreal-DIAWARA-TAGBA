# Contrat de données

Document de référence commun à A et B. Toute modification passe par une PR relue par les deux.

## Conventions

- Base : `boreal.duckdb`, schémas `raw`, `prep`, `quarantine`, `core`, `marts`, `meta`.
- Fin d'observation : **2025-06-30** (date d'extraction).
- Montants en euros, dates au format ISO (AAAA-MM-JJ).
- Colonnes techniques en couche raw : `_source_file`, `_loaded_at`, `_row_number`.

## Couche core (schéma en étoile)

| Table | Grain | Clé | Colonnes principales |
|---|---|---|---|
| `dim_client` | un client dédoublonné | `client_id_maitre` | date_naissance, tranche_age, region, csp, consent_marketing |
| `dim_contrat` | un contrat | `contrat_id` | client_id_maitre, produit, formule, canal_distribution, zone_risque, franchise, bonus_malus, puissance_cv, surface_m2, prime_annuelle, date_effet, date_resiliation |
| `dim_date` | un jour | `date` | annee, mois, annee_mois |
| `dim_garantie` | une garantie | `garantie` | produit |
| `dim_segment` | produit x zone x formule x canal | `segment_id` | produit, zone_risque, formule, canal_distribution |
| `fait_exposition` | **un contrat x une année civile** | (`contrat_id`, `annee`) | segment_id, exposition_annees, prime_acquise, resilie_dans_annee |
| `fait_sinistre` | un sinistre | `sinistre_id` | contrat_id, garantie, date_survenance, date_declaration, statut, reserve_initiale, montant_paye, reserve_restante, charge, audite, fraude_confirmee |
| `fait_reglement` | un paiement | `paiement_id` | sinistre_id, date_paiement, montant, _source_file |

## Définitions des indicateurs

| Indicateur | Définition |
|---|---|
| Exposition | Durée de couverture du contrat sur l'année, en années (jours couverts / 365,25). Fin = date de résiliation, ou 2025-06-30 si le contrat court encore. |
| Prime acquise | prime_annuelle x exposition |
| Montant payé | Somme des règlements du sinistre |
| Réserve restante | Sinistre OUVERT : max(reserve_initiale - montant payé, 0). Sinon 0. |
| Charge sinistre | Montant payé + réserve restante |
| Sinistre retenu | Statut différent de SANS_SUITE et de REJETE |
| Fréquence | Nombre de sinistres retenus / exposition |
| Coût moyen | Charge des sinistres retenus / nombre de sinistres retenus |
| Prime moyenne | Primes acquises / exposition |
| S/P | Charge / primes acquises |
| Taux de résiliation | Résiliations de l'année / exposition de l'année |
| Client actif à une date | Au moins un contrat en cours à cette date |
| Tranche d'âge | Âge au 2025-06-30 : <25, 25-34, 35-49, 50-64, 65+, inconnu |

## Marts (B)

| Mart | Grain | Usage |
|---|---|---|
| `mart_portefeuille_mensuel` | mois x produit x région x canal x zone | Page Portefeuille |
| `mart_segments` | année x segment x tranche d'âge | L3.1, page Technique |
| `mart_decomposition_sp` | année x segment | L3.2 |
| `mart_retention` | cohorte x produit x ancienneté | L4.1 |
| `mart_valeur_client` | client | L4.2 |
| `mart_delais` | sinistre | L4.3, page Exploitation |
| `exploitation` | source / règle / test | Page Exploitation (A) |
| `qualite_resultats` | règle x exécution | Page Exploitation (A) |

## Décisions à trancher ensemble

- [ ] Tranches d'âge définitives
- [ ] Seuil d'alerte du S/P (proposition : 70 %)
- [ ] SCD2 ou SCD1 pour dim_client
- [ ] Règle de survie de la déduplication
