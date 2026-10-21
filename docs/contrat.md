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
| `dim_client` | une version observée d’un client dédoublonné | `client_sk` | client_id_maitre, date_naissance, tranche_age, region, csp, consent_marketing, valid_from, valid_to, is_current, hash_attributs |
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
| Exposition | Durée de couverture du contrat sur l'année, en années (jours couverts / 365,25). Période bornée par les dates du contrat et la fin d’observation ; convention de bornes précisée ci-dessous. |
| Prime acquise | prime_annuelle x exposition |
| Montant payé | Somme des règlements du sinistre |
| Réserve restante | Sinistre OUVERT : max(reserve_initiale - montant payé, 0). Sinon 0. |
| Charge sinistre | Montant payé + réserve restante |
| Sinistre retenu | Statut différent de SANS_SUITE et de REJETE |
| Fréquence | Nombre de sinistres retenus / exposition |
| Coût moyen | Charge des sinistres retenus / nombre de sinistres retenus |
| Prime moyenne | Primes acquises / exposition |
| S/P | Charge des sinistres retenus / primes acquises |
| Taux de résiliation | Résiliations de l'année / exposition de l'année |
| Client actif à une date | Au moins un contrat en cours à cette date |
| Tranche d'âge | Âge au 2025-06-30 : 18-24, 25-34, 35-49, 50-64, 65+, inconnu ; âge < 18 ou > 100 traité par Q08 |

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

## Décisions retenues

- **Déduplication** : règle identique au script B `analyses/01_clients.py` :
  email_hash non vide identique, naissance connue, valide et identique, et absence
  de conflit sur région, CSP et consentement marketing. Le plus petit `client_id`
  devient `client_id_maitre`. Cette règle est déterministe ; elle ne prouve ni
  l’identité réelle ni l’ancienneté du client.
- **Résultat sur l’archive fournie** : 200 groupes d’emails partagés (400 lignes),
  dont 198 groupes rapprochés. Deux groupes, soit quatre clients, restent séparés
  faute de naissance exploitable. Résultat : **15 002 clients maîtres** à l’issue
  du rapprochement, avant les autres règles qualité. Le taux de lignes fusionnées
  est 198 / 15 200, soit **1,3026 %**.
- **Livraison B vers A** : `prep.client_mapping(client_id, client_id_maitre)`
  contient une ligne pour chacun des 15 200 clients source, y compris ceux non
  fusionnés. `clients_a_revoir.csv` trace les quatre cas laissés séparés.
  Les lignes source restent conservées dans raw ; les 198 identifiants absorbés
  sont exclus de la dimension des clients maîtres et tracés avec leur motif dans
  la quarantaine de déduplication. Ils restent présents dans le mapping.
- **Contrats** : A applique le mapping par jointure sur le `client_id` source et
  conserve tous les contrats admissibles après qualité. Sur l’archive fournie,
  aucun contrat ne porte un identifiant absorbé par la règle B : zéro contrat à
  réaffecter, mais la jointure reste obligatoire et testée.
- **Tranches d’âge** (âge au 2025-06-30) : 18-24, 25-34, 35-49, 50-64, 65+, inconnu.
  Âge < 18 ou > 100 : date mise à null dans la couche nettoyée et règle Q08 ;
  la valeur source reste intacte en raw. Pour le rapprochement, conserver la
  logique du script B sur les naissances source afin de reproduire le mapping.
- **Seuil S/P** : alerte orange à 70 %, rouge à 100 %. Les frais de 25-30 % des
  primes constituent une hypothèse paramétrable, pas un montant mesuré dans les
  sources.
- **Historique** : `dim_client` en SCD2 pour les changements observés à partir des
  livraisons disponibles ; `dim_contrat` en SCD1.

## SCD2 : clés, historique et jointures

- `client_sk` : clé technique unique d’une version de client. `client_id_maitre`
  identifie le client métier et peut apparaître dans plusieurs versions.
- Unicité supplémentaire sur (`client_id_maitre`, `valid_from`). Exactement une
  ligne `is_current = true` par client ; aucune période de versions ne se chevauche.
- Périodes de validité **[valid_from, valid_to[** ; `valid_to` à null pour la
  version courante. À la livraison initiale, `valid_from` est la date d’extraction
  **2025-06-30**. Les futurs changements de région, CSP ou consentement ferment
  l’ancienne version et en ouvrent une nouvelle. `hash_attributs` est calculé de
  manière stable sur ces trois attributs avec gestion explicite des nulls.
- Une seule extraction ne permet pas de reconstruire les changements de région,
  CSP ou consentement de 2020 à juin 2025 : ne pas inventer cet historique.
- **Convention des marts B pour cette étude** : utiliser le profil client observé
  au 2025-06-30, y compris pour les analyses des années antérieures, et documenter
  cette limite. A fournit la vue `core.v_client_analyse`, unique par
  `client_id_maitre`, contenant le profil de l’extraction initiale et les colonnes
  métier de `dim_client`. Elle reste figée sur cette observation et n’est pas
  remplacée par le profil courant lors d’une future livraison.
- B joint `core.dim_contrat.client_id_maitre` à
  `core.v_client_analyse.client_id_maitre`. Ne jamais joindre la dimension SCD2
  entière sur le seul identifiant métier : cela pourrait multiplier les lignes.
- Pour une future analyse réellement historique sur une période observée, utiliser
  une jointure temporelle avec `date_analyse >= valid_from` et
  (`date_analyse < valid_to` ou `valid_to IS NULL`). Les périodes antérieures à
  la première observation ne disposent pas d’un profil historique connu.

## Exposition annuelle et mensuelle : même convention

Le fait `core.fait_exposition` reste au grain contrat x année civile. Pour le
mart mensuel, B recalcule la couverture **par contrat et par mois** depuis les
contrats nettoyés de `core.dim_contrat` ; aucune division de l’exposition annuelle
par 12. La prime annuelle est celle disponible dans la source, faute d’historique
tarifaire.

Convention commune A/B, à appliquer dans le code annuel et mensuel :

- La date d’effet est incluse ; la date de résiliation est exclue. Il s’agit d’une
  convention de projet à documenter faute d’heure de résiliation.
- La fin d’observation du 30/06/2025 est incluse : sa borne exclusive est le
  **01/07/2025**.
- Pour une période [début_période, fin_période_exclusive[ :
  `début = max(date_effet, début_période)` et
  `fin = min(date_resiliation si renseignée sinon 2025-07-01,
  2025-07-01, fin_période_exclusive)`.
- `jours_couverts = max(0, datediff('day', début, fin))`.
- `exposition_annees = jours_couverts / 365.25` ;
  `prime_acquise = prime_annuelle * exposition_annees`.
- Les intersections sans jour couvert ne produisent pas de fait d’exposition.
  Une résiliation à date d’effet identique est signalée comme durée nulle.
- Une année bissextile entièrement couverte représente 366 / 365,25 années :
  ne pas imposer à tort une borne stricte d’exposition <= 1 dans les tests.
- Les résiliations sont comptées dans le mois et l’année de leur date, sur les
  contrats valides dont la résiliation est observée au plus tard le 30/06/2025.
  Si un groupe présente une résiliation mais zéro exposition, son taux reste null.
- Le nombre de contrats actifs en fin de mois est un stock :
  `date_effet <= date_fin_mois` et (`date_resiliation IS NULL` ou
  `date_resiliation > date_fin_mois`). Ne pas additionner les stocks mensuels
  pour obtenir un stock annuel.

### Contrôles d’intégration A/B

1. Somme des expositions mensuelles par contrat/année = exposition annuelle du
   cœur, à la tolérance numérique près ; même contrôle sur les primes acquises.
2. `prep.client_mapping` a une clé source unique, aucune clé maître absente du
   référentiel dédoublonné et le même contenu que le fichier accepté de B.
3. `core.v_client_analyse` contient une seule ligne par client maître ; sa jointure
   ne change ni le nombre de contrats ni les primes ou charges.
4. Agréger séparément exposition et sinistres au grain cible avant de les joindre,
   pour ne pas répéter les primes pour chaque sinistre ou règlement.

### Convention temporelle des indicateurs des marts

Les sinistres sont rattachés au mois/à l’année de **survenance**, les résiliations
à leur date de résiliation, et les primes/expositions à la période couverte. La
charge est évaluée au 30/06/2025 avec les règlements connus à cette date et la
réserve restante définie ci-dessus. Les paiements par date de paiement constituent
une analyse distincte de flux ; ne pas les mélanger avec la charge par survenance.
2025 est partielle et les années récentes peuvent encore recevoir des règlements.

Pour préserver l’identité S/P = fréquence x coût moyen / prime moyenne, le S/P
technique utilise **la charge des sinistres retenus**. Les paiements éventuels
sur SANS_SUITE ou REJETE restent conservés, contrôlés et présentés séparément ;
leur charge n’entre pas dans ce ratio technique. Tout ratio sur l’ensemble des
statuts doit être nommé distinctement. Un dénominateur nul donne un indicateur
null, pas zéro.
