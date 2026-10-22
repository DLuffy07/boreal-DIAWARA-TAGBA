# Catalogue des données

Généré automatiquement par `docs/gen_catalogue.py` à chaque lancement du pipeline (structure lue dans la base, définitions dans `docs/catalogue.yaml`).

## Couche brute (`raw`)

### `raw.audits` · 372 lignes

Copie fidèle de antifraude/audits.csv (dossiers audités uniquement).

| Colonne | Type | Définition |
|---|---|---|
| `sinistre_id` | VARCHAR | Identifiant du sinistre |
| `date_audit` | VARCHAR | Date du contrôle antifraude |
| `fraude_confirmee` | VARCHAR | Résultat de l'audit (1/true = fraude confirmée) |
| `_source_file` | VARCHAR | Fichier source d'où provient la ligne (chemin relatif à data/sources) |
| `_row_number` | INTEGER | Numéro de ligne dans le fichier source (en-tête exclu) |
| `_loaded_at` | TIMESTAMP | Horodatage du chargement en couche brute |

### `raw.clients` · 15 200 lignes

Copie fidèle de crm/clients.csv (latin-1, séparateur ;). Toutes les valeurs en texte.

| Colonne | Type | Définition |
|---|---|---|
| `client_id` | VARCHAR | Identifiant client tel que fourni par le CRM |
| `date_naissance` | VARCHAR | Date de naissance du client |
| `region` | VARCHAR | Région de résidence (code à 2-4 lettres, ex. IDF) |
| `csp` | VARCHAR | Catégorie socio-professionnelle |
| `consent_marketing` | VARCHAR | Consentement à la prospection commerciale (1/true = oui) |
| `email_hash` | VARCHAR | Empreinte pseudonymisée de l'adresse e-mail (pas de l'e-mail en clair) |
| `_source_file` | VARCHAR | Fichier source d'où provient la ligne (chemin relatif à data/sources) |
| `_row_number` | INTEGER | Numéro de ligne dans le fichier source (en-tête exclu) |
| `_loaded_at` | TIMESTAMP | Horodatage du chargement en couche brute |

### `raw.contrats` · 20 264 lignes

Copie fidèle de contrats/contrats.csv. Toutes les valeurs en texte.

| Colonne | Type | Définition |
|---|---|---|
| `contrat_id` | VARCHAR | Identifiant du contrat |
| `client_id` | VARCHAR | Identifiant client tel que fourni par le CRM |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `date_effet` | VARCHAR | Date de début de couverture (incluse) |
| `date_resiliation` | VARCHAR | Date de fin de couverture (exclue) ; vide si le contrat court encore |
| `formule` | VARCHAR | ESSENTIELLE, CONFORT ou PREMIUM |
| `canal_distribution` | VARCHAR | Canal de souscription (AGENT, COURTIER, WEB) |
| `zone_risque` | VARCHAR | Zone tarifaire de risque, de 1 (faible) à 5 (élevé) |
| `franchise` | VARCHAR | Franchise contractuelle en euros |
| `bonus_malus` | VARCHAR | Coefficient de réduction-majoration (auto uniquement) |
| `puissance_cv` | VARCHAR | Puissance fiscale du véhicule (auto uniquement) |
| `surface_m2` | VARCHAR | Surface du logement en m² (habitation uniquement) |
| `prime_annuelle` | VARCHAR | Prime annuelle du contrat en euros |
| `_source_file` | VARCHAR | Fichier source d'où provient la ligne (chemin relatif à data/sources) |
| `_row_number` | INTEGER | Numéro de ligne dans le fichier source (en-tête exclu) |
| `_loaded_at` | TIMESTAMP | Horodatage du chargement en couche brute |

### `raw.reglements` · 3 207 lignes

Copie fidèle des 64 fichiers mensuels reglements_AAAA_MM.csv, colonnes alignées par nom (montant_eur -> montant).

| Colonne | Type | Définition |
|---|---|---|
| `paiement_id` | VARCHAR | Identifiant du paiement |
| `sinistre_id` | VARCHAR | Identifiant du sinistre |
| `date_paiement` | VARCHAR | Date du paiement |
| `montant` | VARCHAR | Montant payé en euros |
| `_source_file` | VARCHAR | Fichier source d'où provient la ligne (chemin relatif à data/sources) |
| `_row_number` | INTEGER | Numéro de ligne dans le fichier source (en-tête exclu) |
| `_loaded_at` | TIMESTAMP | Horodatage du chargement en couche brute |

### `raw.sinistres` · 2 805 lignes

Copie fidèle de sinistres/sinistres.jsonl, une ligne par enregistrement JSON.

| Colonne | Type | Définition |
|---|---|---|
| `sinistre_id` | VARCHAR | Identifiant du sinistre |
| `contrat_id` | VARCHAR | Identifiant du contrat |
| `date_survenance` | VARCHAR | Date à laquelle le sinistre s'est produit |
| `date_declaration` | VARCHAR | Date à laquelle le sinistre a été déclaré à l'assureur |
| `garantie` | VARCHAR | Garantie mise en jeu (COLLISION, VOL, DEGAT_EAUX...) |
| `statut` | VARCHAR | Statut du sinistre (OUVERT, CLOTURE, SANS_SUITE, REJETE) |
| `reserve_initiale` | VARCHAR | Montant provisionné à l'ouverture du dossier, en euros |
| `_source_file` | VARCHAR | Fichier source d'où provient la ligne (chemin relatif à data/sources) |
| `_row_number` | INTEGER | Numéro de ligne dans le fichier source (en-tête exclu) |
| `_loaded_at` | TIMESTAMP | Horodatage du chargement en couche brute |

## Préparation (`prep`)

### `prep.audits` · 372 lignes

Audits typés, sans filtrage.

| Colonne | Type | Définition |
|---|---|---|
| `_row_key` | VARCHAR | Identifiant unique d'une ligne source, fichier#ligne ; clé de traçabilité vers la quarantaine |
| `sinistre_id` | INTEGER | Identifiant du sinistre |
| `date_audit` | DATE | Date du contrôle antifraude |
| `fraude_confirmee` | INTEGER | Résultat de l'audit (1/true = fraude confirmée) |
| `_source_file` | VARCHAR | Fichier source d'où provient la ligne (chemin relatif à data/sources) |
| `_row_number` | INTEGER | Numéro de ligne dans le fichier source (en-tête exclu) |
| `_loaded_at` | TIMESTAMP | Horodatage du chargement en couche brute |

### `prep.client_mapping` · 15 200 lignes

Résultat de la déduplication (script quality/dedup_clients.py) — un client source vers son client maître.

| Colonne | Type | Définition |
|---|---|---|
| `client_id` | INTEGER | Identifiant client tel que fourni par le CRM |
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |

### `prep.clients` · 15 200 lignes

Clients typés et normalisés, sans filtrage (autant de lignes qu'en raw).

| Colonne | Type | Définition |
|---|---|---|
| `_row_key` | VARCHAR | Identifiant unique d'une ligne source, fichier#ligne ; clé de traçabilité vers la quarantaine |
| `client_id_brut` | VARCHAR | Identifiant client tel que lu, avant conversion en entier |
| `client_id` | INTEGER | Identifiant client tel que fourni par le CRM |
| `date_naissance` | DATE | Date de naissance du client |
| `region` | VARCHAR | Région de résidence (code à 2-4 lettres, ex. IDF) |
| `csp` | VARCHAR | Catégorie socio-professionnelle |
| `consent_marketing` | INTEGER | Consentement à la prospection commerciale (1/true = oui) |
| `email_hash` | VARCHAR | Empreinte pseudonymisée de l'adresse e-mail (pas de l'e-mail en clair) |
| `_source_file` | VARCHAR | Fichier source d'où provient la ligne (chemin relatif à data/sources) |
| `_row_number` | INTEGER | Numéro de ligne dans le fichier source (en-tête exclu) |
| `_loaded_at` | TIMESTAMP | Horodatage du chargement en couche brute |

### `prep.contrats` · 20 264 lignes

Contrats typés et normalisés, sans filtrage.

| Colonne | Type | Définition |
|---|---|---|
| `_row_key` | VARCHAR | Identifiant unique d'une ligne source, fichier#ligne ; clé de traçabilité vers la quarantaine |
| `contrat_id` | INTEGER | Identifiant du contrat |
| `client_id` | INTEGER | Identifiant client tel que fourni par le CRM |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `date_effet` | DATE | Date de début de couverture (incluse) |
| `date_resiliation` | DATE | Date de fin de couverture (exclue) ; vide si le contrat court encore |
| `formule` | VARCHAR | ESSENTIELLE, CONFORT ou PREMIUM |
| `canal_distribution` | VARCHAR | Canal de souscription (AGENT, COURTIER, WEB) |
| `zone_risque` | INTEGER | Zone tarifaire de risque, de 1 (faible) à 5 (élevé) |
| `franchise` | INTEGER | Franchise contractuelle en euros |
| `bonus_malus` | DOUBLE | Coefficient de réduction-majoration (auto uniquement) |
| `puissance_cv` | DOUBLE | Puissance fiscale du véhicule (auto uniquement) |
| `surface_m2` | DOUBLE | Surface du logement en m² (habitation uniquement) |
| `prime_annuelle` | DOUBLE | Prime annuelle du contrat en euros |
| `_source_file` | VARCHAR | Fichier source d'où provient la ligne (chemin relatif à data/sources) |
| `_row_number` | INTEGER | Numéro de ligne dans le fichier source (en-tête exclu) |
| `_loaded_at` | TIMESTAMP | Horodatage du chargement en couche brute |

### `prep.reglements` · 3 207 lignes

Règlements typés, sans filtrage ; les doublons de livraison y sont encore présents.

| Colonne | Type | Définition |
|---|---|---|
| `_row_key` | VARCHAR | Identifiant unique d'une ligne source, fichier#ligne ; clé de traçabilité vers la quarantaine |
| `paiement_id` | INTEGER | Identifiant du paiement |
| `sinistre_id` | INTEGER | Identifiant du sinistre |
| `date_paiement` | DATE | Date du paiement |
| `montant` | DOUBLE | Montant payé en euros |
| `mois_fichier` | DATE | Mois annoncé par le nom du fichier (sert à détecter les livraisons tardives, règle Q21) |
| `_source_file` | VARCHAR | Fichier source d'où provient la ligne (chemin relatif à data/sources) |
| `_row_number` | INTEGER | Numéro de ligne dans le fichier source (en-tête exclu) |
| `_loaded_at` | TIMESTAMP | Horodatage du chargement en couche brute |

### `prep.sinistres` · 2 805 lignes

Sinistres typés et normalisés, sans filtrage.

| Colonne | Type | Définition |
|---|---|---|
| `_row_key` | VARCHAR | Identifiant unique d'une ligne source, fichier#ligne ; clé de traçabilité vers la quarantaine |
| `sinistre_id` | INTEGER | Identifiant du sinistre |
| `contrat_id` | INTEGER | Identifiant du contrat |
| `date_survenance` | DATE | Date à laquelle le sinistre s'est produit |
| `date_declaration` | DATE | Date à laquelle le sinistre a été déclaré à l'assureur |
| `garantie` | VARCHAR | Garantie mise en jeu (COLLISION, VOL, DEGAT_EAUX...) |
| `statut` | VARCHAR | Statut du sinistre (OUVERT, CLOTURE, SANS_SUITE, REJETE) |
| `reserve_initiale` | DOUBLE | Montant provisionné à l'ouverture du dossier, en euros |
| `_source_file` | VARCHAR | Fichier source d'où provient la ligne (chemin relatif à data/sources) |
| `_row_number` | INTEGER | Numéro de ligne dans le fichier source (en-tête exclu) |
| `_loaded_at` | TIMESTAMP | Horodatage du chargement en couche brute |

## Quarantaine (`quarantine`)

### `quarantine.anomalies` · 878 lignes

Une ligne par couple (règle, ligne source en anomalie). Rien n'est supprimé.

| Colonne | Type | Définition |
|---|---|---|
| `rule_id` | VARCHAR | Identifiant de la règle de qualité (voir quality/rules.yaml) |
| `table_source` | VARCHAR | Table prep concernée par la règle |
| `_row_key` | VARCHAR | Identifiant unique d'une ligne source, fichier#ligne ; clé de traçabilité vers la quarantaine |
| `motif` | VARCHAR | Raison de la mise en quarantaine |
| `dimension` | VARCHAR | Dimension qualité (complétude, unicité, validité, cohérence inter-tables, cohérence temporelle) |
| `gravite` | VARCHAR | bloquante, majeure ou mineure |
| `traitement` | VARCHAR | exclure (hors du cœur), corriger (valeur corrigée), signaler (tracé seulement) |
| `detecte_le` | TIMESTAMP | Horodatage de la détection |

### `quarantine.clients_a_revoir` · 4 lignes

Clients laissés séparés par la déduplication, une ligne par client à examiner.

| Colonne | Type | Définition |
|---|---|---|
| `client_id` | INTEGER | Identifiant client tel que fourni par le CRM |
| `email_hash` | VARCHAR | Empreinte pseudonymisée de l'adresse e-mail (pas de l'e-mail en clair) |
| `motif` | VARCHAR | Raison de la mise en quarantaine |

### `quarantine.clients_dedup` · 198 lignes

Identifiants clients absorbés par la déduplication, avec leur client maître.

| Colonne | Type | Définition |
|---|---|---|
| `client_id` | INTEGER | Identifiant client tel que fourni par le CRM |
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |
| `motif` | VARCHAR | Raison de la mise en quarantaine |
| `detecte_le` | TIMESTAMP WITH TIME ZONE | Horodatage de la détection |

### `quarantine.lignes_exclues` · vue

Vue — lignes écartées du cœur (traitement « exclure »), tous motifs concaténés.

| Colonne | Type | Définition |
|---|---|---|
| `table_source` | VARCHAR | Table prep concernée par la règle |
| `_row_key` | VARCHAR | Identifiant unique d'une ligne source, fichier#ligne ; clé de traçabilité vers la quarantaine |
| `motifs` | VARCHAR | Liste des règles et motifs ayant conduit à l'exclusion |

### `quarantine.raw_rejets` · 0 lignes

Lignes illisibles à l'ingestion (nombre de champs incorrect, JSON invalide).

| Colonne | Type | Définition |
|---|---|---|
| `fichier` | VARCHAR | Fichier source |
| `ligne` | INTEGER | Numéro de ligne |
| `contenu` | VARCHAR | Contenu brut de la ligne rejetée |
| `motif` | VARCHAR | Raison de la mise en quarantaine |
| `_loaded_at` | TIMESTAMP | Horodatage du chargement en couche brute |

## Cœur (schéma en étoile) (`core`)

### `core.dim_client` · 15 002 lignes

Dimension client en SCD2, une ligne par version d'un client maître.

| Colonne | Type | Définition |
|---|---|---|
| `client_sk` | VARCHAR | Clé technique d'une version de client (md5 de l'identifiant et de valid_from) |
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |
| `date_naissance` | DATE | Date de naissance (mise à null si âge hors [18;100], règle Q08) |
| `age` | BIGINT | Âge au 30/06/2025 |
| `tranche_age` | VARCHAR | 18-24, 25-34, 35-49, 50-64, 65+ ou inconnu |
| `region` | VARCHAR | Région de résidence (code à 2-4 lettres, ex. IDF) |
| `csp` | VARCHAR | Catégorie socio-professionnelle |
| `consent_marketing` | BOOLEAN | Consentement à la prospection commerciale (1/true = oui) |
| `valid_from` | DATE | Début de validité de la version (incluse) |
| `valid_to` | DATE | Fin de validité (exclue), vide pour la version courante |
| `is_current` | BOOLEAN | Vrai pour la version en vigueur |
| `hash_attributs` | VARCHAR | Empreinte de région + CSP + consentement, sert à détecter un changement |

### `core.dim_contrat` · 20 213 lignes

Contrats valides (hors quarantaine), rattachés à leur client maître.

| Colonne | Type | Définition |
|---|---|---|
| `contrat_id` | INTEGER | Identifiant du contrat |
| `client_id` | INTEGER | Identifiant client tel que fourni par le CRM |
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `formule` | VARCHAR | ESSENTIELLE, CONFORT ou PREMIUM |
| `canal_distribution` | VARCHAR | Canal de souscription (AGENT, COURTIER, WEB) |
| `zone_risque` | INTEGER | Zone tarifaire de risque, de 1 (faible) à 5 (élevé) |
| `franchise` | INTEGER | Franchise contractuelle en euros |
| `bonus_malus` | DOUBLE | Coefficient de réduction-majoration (auto uniquement) |
| `puissance_cv` | DOUBLE | Puissance fiscale du véhicule (auto uniquement) |
| `surface_m2` | DOUBLE | Surface du logement en m² (habitation uniquement) |
| `prime_annuelle` | DOUBLE | Prime annuelle du contrat en euros |
| `date_effet` | DATE | Date de début de couverture (incluse) |
| `date_resiliation` | DATE | Date de fin de couverture (exclue) ; vide si le contrat court encore |
| `segment_id` | VARCHAR | Segment de risque = produit-zone-formule-canal |

### `core.dim_date` · 2 557 lignes

Calendrier, une ligne par jour de 2019 à 2025.

| Colonne | Type | Définition |
|---|---|---|
| `date` | DATE | Jour |
| `annee` | BIGINT | Année civile |
| `mois` | BIGINT | Mois (1-12) ou premier jour du mois selon la table |
| `annee_mois` | VARCHAR | Mois au format AAAA-MM |

### `core.dim_garantie` · 8 lignes

Référentiel des garanties et du produit auquel elles s'appliquent.

| Colonne | Type | Définition |
|---|---|---|
| `garantie` | VARCHAR | Garantie mise en jeu (COLLISION, VOL, DEGAT_EAUX...) |
| `produit` | VARCHAR | AUTO ou HABITATION |

### `core.dim_segment` · 90 lignes

Segments de risque produit × zone × formule × canal présents dans le portefeuille.

| Colonne | Type | Définition |
|---|---|---|
| `segment_id` | VARCHAR | Segment de risque = produit-zone-formule-canal |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `zone_risque` | INTEGER | Zone tarifaire de risque, de 1 (faible) à 5 (élevé) |
| `formule` | VARCHAR | ESSENTIELLE, CONFORT ou PREMIUM |
| `canal_distribution` | VARCHAR | Canal de souscription (AGENT, COURTIER, WEB) |

### `core.fait_exposition` · 65 081 lignes

Grain contrat × année civile. Base de toute fréquence et de toute prime acquise.

| Colonne | Type | Définition |
|---|---|---|
| `contrat_id` | INTEGER | Identifiant du contrat |
| `annee` | BIGINT | Année civile |
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |
| `segment_id` | VARCHAR | Segment de risque = produit-zone-formule-canal |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `exposition_annees` | DOUBLE | Jours couverts dans l'année / 365,25 (effet inclus, résiliation exclue, fin d'observation 30/06/2025 incluse) |
| `prime_acquise` | DOUBLE | prime_annuelle × exposition_annees, en euros |
| `resilie_dans_annee` | BOOLEAN | Vrai si la date de résiliation tombe dans l'année (indicatif ; compter les résiliations depuis dim_contrat) |

### `core.fait_reglement` · 3 130 lignes

Grain paiement. Règlements valides, doublons de livraison exclus.

| Colonne | Type | Définition |
|---|---|---|
| `paiement_id` | INTEGER | Identifiant du paiement |
| `sinistre_id` | INTEGER | Identifiant du sinistre |
| `date_paiement` | DATE | Date du paiement |
| `montant` | DOUBLE | Montant payé en euros |
| `_source_file` | VARCHAR | Fichier source d'où provient la ligne (chemin relatif à data/sources) |

### `core.fait_sinistre` · 2 769 lignes

Grain sinistre. Charge évaluée au 30/06/2025.

| Colonne | Type | Définition |
|---|---|---|
| `sinistre_id` | INTEGER | Identifiant du sinistre |
| `contrat_id` | INTEGER | Identifiant du contrat |
| `date_survenance` | DATE | Date à laquelle le sinistre s'est produit |
| `date_declaration` | DATE | Date à laquelle le sinistre a été déclaré à l'assureur |
| `garantie` | VARCHAR | Garantie mise en jeu (COLLISION, VOL, DEGAT_EAUX...) |
| `statut` | VARCHAR | Statut du sinistre (OUVERT, CLOTURE, SANS_SUITE, REJETE) |
| `reserve_initiale` | DOUBLE | Montant provisionné à l'ouverture du dossier, en euros |
| `montant_paye` | DOUBLE | Somme des règlements valides du sinistre |
| `nb_paiements` | BIGINT | Nombre de règlements valides |
| `date_premier_paiement` | DATE | Date du premier règlement |
| `date_dernier_paiement` | DATE | Date du dernier règlement (sert de date de clôture approchée) |
| `reserve_restante` | DOUBLE | Pour un sinistre OUVERT, max(réserve initiale − payé, 0) ; sinon 0 |
| `charge` | DOUBLE | montant_paye + reserve_restante |
| `retenu` | BOOLEAN | Vrai si statut hors SANS_SUITE et REJETE ; seuls les retenus entrent dans fréquence, coût moyen et S/P |
| `audite` | BOOLEAN | Vrai si le dossier a été contrôlé par l'antifraude |
| `date_audit` | DATE | Date du contrôle antifraude |
| `fraude_confirmee` | BOOLEAN | Résultat de l'audit (1/true = fraude confirmée) |

### `core.v_client_analyse` · vue

Vue — profil client observé au 30/06/2025, une ligne par client maître. Seule vue client à joindre dans les marts.

| Colonne | Type | Définition |
|---|---|---|
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |
| `client_sk` | VARCHAR | Clé de la version utilisée |
| `date_naissance` | DATE | Date de naissance du client |
| `age` | BIGINT | Âge au 30/06/2025 |
| `tranche_age` | VARCHAR | 18-24, 25-34, 35-49, 50-64, 65+ ou inconnu |
| `region` | VARCHAR | Région de résidence (code à 2-4 lettres, ex. IDF) |
| `csp` | VARCHAR | Catégorie socio-professionnelle |
| `consent_marketing` | BOOLEAN | Consentement à la prospection commerciale (1/true = oui) |

## Marts (`marts`)

### `marts.exploitation_ingestion` · 69 lignes

Journal d'ingestion hors fichiers ignorés car inchangés.

| Colonne | Type | Définition |
|---|---|---|
| `horodatage` | TIMESTAMP | Date et heure de l'événement |
| `source` | VARCHAR | Table brute alimentée |
| `fichier` | VARCHAR | Fichier traité |
| `statut` | VARCHAR | OK ou FAILED |
| `lignes_lues` | INTEGER | Lignes lues |
| `lignes_chargees` | INTEGER | Lignes chargées |
| `lignes_rejetees` | INTEGER | Lignes rejetées |
| `duree_s` | DOUBLE | Durée en secondes |
| `message` | VARCHAR | Message d'erreur ou commentaire |

### `marts.exploitation_qualite` · 29 lignes

Résultat de chaque règle de qualité à la dernière exécution.

| Colonne | Type | Définition |
|---|---|---|
| `rule_id` | VARCHAR | Identifiant de la règle de qualité (voir quality/rules.yaml) |
| `table_source` | VARCHAR | Table prep concernée par la règle |
| `libelle` | VARCHAR | Description de la règle |
| `dimension` | VARCHAR | Dimension qualité (complétude, unicité, validité, cohérence inter-tables, cohérence temporelle) |
| `gravite` | VARCHAR | bloquante, majeure ou mineure |
| `traitement` | VARCHAR | exclure (hors du cœur), corriger (valeur corrigée), signaler (tracé seulement) |
| `correction` | VARCHAR | Correction appliquée quand le traitement est « corriger » ou précision sur le traitement |
| `volume` | INTEGER | Nombre de lignes concernées |
| `lignes_table` | INTEGER | Nombre de lignes de la table contrôlée |
| `pct_lignes` | DOUBLE | Part des lignes concernées, en % |
| `run_at` | TIMESTAMP | Horodatage de l'exécution |

### `marts.exploitation_runs` · 6 lignes

Historique des lancements du pipeline.

| Colonne | Type | Définition |
|---|---|---|
| `run_id` | VARCHAR | Identifiant d'un lancement du pipeline |
| `debut` | TIMESTAMP | Début du lancement |
| `duree_totale_s` | DOUBLE | Durée totale en secondes |
| `statut` | VARCHAR | OK ou FAILED |
| `etapes` | VARCHAR | Étapes exécutées dans l'ordre |
| `erreur` | VARCHAR | Message de l'étape en échec |

### `marts.exploitation_sources` · 5 lignes

État de chaque source (dernier chargement, volumes, lignes exclues, fraîcheur).

| Colonne | Type | Définition |
|---|---|---|
| `source` | VARCHAR | Source de données |
| `dernier_chargement` | TIMESTAMP | Dernier chargement réussi |
| `dernier_fichier` | VARCHAR | Dernier fichier connu |
| `nb_fichiers` | BIGINT | Nombre de fichiers chargés |
| `lignes_brutes` | BIGINT | Lignes en couche brute |
| `lignes_exclues` | BIGINT | Lignes écartées du cœur |
| `pct_exclues` | DOUBLE | Part des lignes exclues, en % |
| `donnee_la_plus_recente` | DATE | Date métier la plus récente |
| `jours_avant_extraction` | BIGINT | Écart en jours avec l'extraction du 30/06/2025 |
| `nb_echecs_historiques` | BIGINT | Nombre de chargements en échec depuis l'origine |

### `marts.exploitation_tests` · 61 lignes

Résultat des tests bloquants du dernier lancement.

| Colonne | Type | Définition |
|---|---|---|
| `module` | VARCHAR | Fichier de test |
| `test` | VARCHAR | Nom du test |
| `statut` | VARCHAR | PASSED, FAILED ou SKIPPED |
| `duree_s` | DOUBLE | Durée en secondes |
| `message` | VARCHAR | Message d'erreur ou commentaire |
| `horodatage` | TIMESTAMP | Date et heure de l'événement |

### `marts.mart_audits` · 15 lignes

Taux de confirmation et montants des seuls dossiers audités valides, par garantie, tranche de charge et délai ; IC Wilson ajoutés par le script 05.

| Colonne | Type | Définition |
|---|---|---|
| `axe` | VARCHAR | Dimension de regroupement ; global signifie tout le portefeuille. |
| `groupe` | VARCHAR | Modalité de la dimension de regroupement. |
| `nb_audits` | BIGINT | Nombre de dossiers audités valides dans le groupe. |
| `nb_fraudes_confirmees` | BIGINT | Nombre de confirmations de fraude parmi les dossiers audités du groupe. |
| `taux_confirmation` | DOUBLE | Fraudes confirmées / audits valides du groupe ; ne s’applique pas aux non-audités. |
| `charge_auditee` | DOUBLE | Somme des charges observées des dossiers audités, euros. |
| `charge_dossiers_confirmes` | DOUBLE | Charge des dossiers audités à fraude confirmée, euros ; pas une économie prouvée. |
| `paye_dossiers_confirmes` | DOUBLE | Paiements des dossiers audités à fraude confirmée, euros ; pas un montant récupéré. |
| `ic_bas` | DOUBLE | Borne inférieure de l’intervalle de confiance, même unité que l’estimation. |
| `ic_haut` | DOUBLE | Borne supérieure de l’intervalle de confiance, même unité que l’estimation. |

### `marts.mart_cohortes_dashboard` · 121 278 lignes

Détail de rétention enrichi du profil régional de juin 2025 et du canal de première souscription au produit, pour filtres dashboard.

| Colonne | Type | Définition |
|---|---|---|
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `date_entree` | DATE | Date de première souscription valide du client au produit. |
| `cohorte` | BIGINT | Année de première souscription valide du client au produit. |
| `detention_entree` | VARCHAR | Mono/Multi mesuré à la première souscription au produit ; Tous agrège les groupes. |
| `anciennete` | BIGINT | Nombre entier d’années écoulées depuis la première souscription au produit. |
| `date_anniversaire` | DATE | Date d’entrée décalée du nombre d’années d’ancienneté. |
| `observable` | BOOLEAN | Tous les anniversaires de la cohorte-produit-ancienneté sont au plus tard le 30/06/2025. |
| `retenu_anniversaire` | BOOLEAN | Au moins un contrat du même produit actif à l’anniversaire ; null si cohorte non entièrement observable. |
| `region` | VARCHAR | Région de résidence (code à 2-4 lettres, ex. IDF) |
| `tranche_age` | VARCHAR | Tranche d’âge au 30/06/2025 ; inconnu si date absente ou âge invalide. |
| `canal_distribution` | VARCHAR | Canal de souscription (AGENT, COURTIER, WEB) |

### `marts.mart_contrat_mois` · 555 850 lignes

Une ligne par contrat valide et mois avec couverture, sinistre, paiement ou résiliation ; détail filtrable commun au dashboard.

| Colonne | Type | Définition |
|---|---|---|
| `contrat_id` | INTEGER | Identifiant du contrat |
| `mois` | DATE | Premier jour du mois civil observé ; observation bornée à janvier 2020-juin 2025 dans les marts dashboard. |
| `exposition_annees` | DOUBLE | Durée totale observée en années-polices, jours couverts / 365,25. |
| `primes_acquises` | DOUBLE | Somme des primes annuelles proratisées à la durée couverte, en euros. |
| `contrats_actifs` | BIGINT | Stock de contrats actifs au dernier jour du mois : date d’effet incluse et résiliation exclue ; ne pas sommer entre mois. |
| `nb_resiliations` | BIGINT | Résiliations à leur date réelle, parmi les contrats valides de la période observée. |
| `nb_sinistres_retenus` | BIGINT | Nombre de sinistres hors SANS_SUITE et REJETE. |
| `nb_sans_suite` | BIGINT | Nombre de sinistres au statut SANS_SUITE. |
| `nb_rejetes` | BIGINT | Nombre de sinistres au statut REJETE. |
| `charge_retenue` | DOUBLE | Somme payé + réserve restante des sinistres retenus, en euros. |
| `montant_paye_retenu` | DOUBLE | Somme des paiements des sinistres retenus, en euros. |
| `reserve_restante_retenue` | DOUBLE | Somme des réserves restantes conventionnelles des sinistres retenus, en euros. |
| `paiements_flux` | DOUBLE | Paiements effectivement datés du mois, tous statuts ; distincts des paiements des sinistres survenus dans le mois. |
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `formule` | VARCHAR | ESSENTIELLE, CONFORT ou PREMIUM |
| `canal_distribution` | VARCHAR | Canal de souscription (AGENT, COURTIER, WEB) |
| `zone_risque` | INTEGER | Zone tarifaire de risque, de 1 (faible) à 5 (élevé) |
| `segment_id` | VARCHAR | Segment de risque = produit-zone-formule-canal |
| `region` | VARCHAR | Région de résidence (code à 2-4 lettres, ex. IDF) |
| `tranche_age` | VARCHAR | Tranche d’âge au 30/06/2025 ; inconnu si date absente ou âge invalide. |

### `marts.mart_contrats_analyse` · 20 213 lignes

Une ligne par contrat valide : exposition et mesures cumulées observées, profil client de juin 2025.

| Colonne | Type | Définition |
|---|---|---|
| `contrat_id` | INTEGER | Identifiant du contrat |
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `formule` | VARCHAR | ESSENTIELLE, CONFORT ou PREMIUM |
| `zone_risque` | INTEGER | Zone tarifaire de risque, de 1 (faible) à 5 (élevé) |
| `canal_distribution` | VARCHAR | Canal de souscription (AGENT, COURTIER, WEB) |
| `region` | VARCHAR | Région de résidence (code à 2-4 lettres, ex. IDF) |
| `tranche_age` | VARCHAR | Tranche d’âge au 30/06/2025 ; inconnu si date absente ou âge invalide. |
| `exposition_annees` | DOUBLE | Durée totale observée en années-polices, jours couverts / 365,25. |
| `primes_acquises` | DOUBLE | Somme des primes annuelles proratisées à la durée couverte, en euros. |
| `nb_sinistres_retenus` | BIGINT | Nombre de sinistres hors SANS_SUITE et REJETE. |
| `charge_retenue` | DOUBLE | Somme payé + réserve restante des sinistres retenus, en euros. |
| `nb_resiliations` | BIGINT | Résiliations à leur date réelle, parmi les contrats valides de la période observée. |

### `marts.mart_contributions_segments` · 450 lignes

Contribution comptable de chaque segment à la variation annuelle du S/P global.

| Colonne | Type | Définition |
|---|---|---|
| `annee` | BIGINT | Année civile |
| `segment_id` | VARCHAR | Segment de risque = produit-zone-formule-canal |
| `contribution_sp` | DOUBLE | Charge du segment / primes globales de l’année, ratio brut. |
| `precedent` | DOUBLE | Contribution du même segment à l’année précédente, ratio brut. |
| `variation_contribution_sp` | DOUBLE | Variation de la contribution comptable du segment au S/P ; ratio brut. |
| `annee_partielle` | BOOLEAN | Vrai pour 2025, limitée à janvier-juin. |

### `marts.mart_decomposition_sp` · 5 lignes

Variation annuelle globale du S/P expliquée par trois effets Shapley ; 2025 partielle.

| Colonne | Type | Définition |
|---|---|---|
| `annee` | BIGINT | Année civile |
| `annee_precedente` | BIGINT | Année civile servant de référence de comparaison. |
| `sp_precedent` | DOUBLE | S/P technique de l’année précédente, ratio brut. |
| `sp_courant` | DOUBLE | S/P technique de l’année courante, ratio brut. |
| `variation_sp` | DOUBLE | S/P courant moins S/P précédent, ratio brut ; multiplier par 100 pour des points de pourcentage. |
| `effet_frequence` | DOUBLE | Contribution Shapley de la fréquence à la variation du S/P, ratio brut. |
| `effet_cout_moyen` | DOUBLE | Contribution Shapley du coût moyen à la variation du S/P, ratio brut. |
| `effet_prime_moyenne` | DOUBLE | Contribution Shapley de la prime moyenne à la variation du S/P, ratio brut. |
| `effet_volume_sur_ratio` | DOUBLE | Zéro par identité algébrique ; l’exposition se simplifie dans le ratio. |
| `exposition_precedente` | DOUBLE | Exposition de l’année précédente, en années-polices. |
| `exposition_courante` | DOUBLE | Exposition de l’année courante, en années-polices. |
| `charge_precedente` | DOUBLE | Charge retenue de l’année précédente, en euros. |
| `charge_courante` | DOUBLE | Charge retenue de l’année courante, en euros. |
| `primes_precedentes` | DOUBLE | Primes acquises de l’année précédente, en euros. |
| `primes_courantes` | DOUBLE | Primes acquises de l’année courante, en euros. |
| `annee_partielle` | BOOLEAN | Vrai pour 2025, limitée à janvier-juin. |
| `methode` | VARCHAR | Méthode statistique ou de décomposition employée. |

### `marts.mart_delais` · 2 769 lignes

Une ligne par sinistre : délais observés, statut et audit ; dernier paiement des clôturés comme approximation explicitement distincte.

| Colonne | Type | Définition |
|---|---|---|
| `sinistre_id` | INTEGER | Identifiant du sinistre |
| `contrat_id` | INTEGER | Identifiant du contrat |
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `formule` | VARCHAR | ESSENTIELLE, CONFORT ou PREMIUM |
| `canal_distribution` | VARCHAR | Canal de souscription (AGENT, COURTIER, WEB) |
| `zone_risque` | INTEGER | Zone tarifaire de risque, de 1 (faible) à 5 (élevé) |
| `region` | VARCHAR | Région de résidence (code à 2-4 lettres, ex. IDF) |
| `tranche_age` | VARCHAR | Tranche d’âge au 30/06/2025 ; inconnu si date absente ou âge invalide. |
| `garantie` | VARCHAR | Garantie mise en jeu (COLLISION, VOL, DEGAT_EAUX...) |
| `statut` | VARCHAR | Statut du sinistre (OUVERT, CLOTURE, SANS_SUITE, REJETE) |
| `date_survenance` | DATE | Date à laquelle le sinistre s'est produit |
| `date_declaration` | DATE | Date à laquelle le sinistre a été déclaré à l'assureur |
| `date_premier_paiement` | DATE | Date minimale des paiements du sinistre ; null sans paiement. |
| `date_dernier_paiement` | DATE | Date maximale des paiements enregistrés ; ce n’est pas une date de clôture. |
| `montant_paye` | DOUBLE | Paiements cumulés du sinistre connus à la date d’extraction, en euros. |
| `charge` | DOUBLE | Montant payé + réserve restante, en euros. |
| `audite` | BOOLEAN | Dossier ayant un audit valide dans le cœur. |
| `fraude_confirmee` | BOOLEAN | Résultat de l'audit (1/true = fraude confirmée) |
| `date_audit` | DATE | Date du contrôle antifraude |
| `delai_declaration_jours` | BIGINT | Déclaration moins survenance en jours. |
| `delai_premier_reglement_jours` | BIGINT | Premier paiement moins déclaration en jours ; null si absent ou négatif. |
| `delai_dernier_reglement_clotures_jours` | BIGINT | Dernier paiement moins déclaration, uniquement pour les dossiers CLOTURE ; approximation distincte du délai réel de clôture. |
| `paiement_avant_declaration` | BOOLEAN | Premier paiement antérieur à la déclaration ; anomalie signalée. |
| `tranche_charge` | VARCHAR | Charge observée à l’extraction : <1000, 1000-4999, 5000-19999 ou >=20000 euros. |
| `tranche_delai_declaration` | VARCHAR | Déclaration dans les 0-7 jours, 8-30 jours ou au-delà de 30 jours. |

### `marts.mart_delais_garantie` · 7 lignes

Quantiles des délais disponibles et effectifs par garantie.

| Colonne | Type | Définition |
|---|---|---|
| `garantie` | VARCHAR | Garantie mise en jeu (COLLISION, VOL, DEGAT_EAUX...) |
| `nb_dossiers` | BIGINT | Nombre de sinistres valides de la garantie. |
| `nb_ouverts` | BIGINT | Nombre de sinistres encore au statut OUVERT. |
| `nb_delais_declaration` | BIGINT | Nombre de délais de déclaration renseignés. |
| `nb_delais_premier_reglement` | BIGINT | Nombre de premiers paiements observés et non antérieurs à la déclaration. |
| `nb_delais_dernier_reglement_clotures` | BIGINT | Nombre de dossiers CLOTURE avec dernier paiement observé après déclaration. |
| `nb_paiements_avant_declaration` | BIGINT | Nombre de sinistres dont le premier paiement précède la déclaration. |
| `declaration_mediane` | DOUBLE | Médiane du délai : Déclaration moins survenance, jours ; calcul sur les valeurs observées non nulles. |
| `declaration_p75` | DOUBLE | Quantile 75 % du délai : Déclaration moins survenance, jours ; calcul sur les valeurs observées non nulles. |
| `declaration_p90` | DOUBLE | Quantile 90 % du délai : Déclaration moins survenance, jours ; calcul sur les valeurs observées non nulles. |
| `premier_reglement_mediane` | DOUBLE | Médiane du délai : Premier paiement moins déclaration, jours ; calcul sur les valeurs observées non nulles. |
| `premier_reglement_p75` | DOUBLE | Quantile 75 % du délai : Premier paiement moins déclaration, jours ; calcul sur les valeurs observées non nulles. |
| `premier_reglement_p90` | DOUBLE | Quantile 90 % du délai : Premier paiement moins déclaration, jours ; calcul sur les valeurs observées non nulles. |
| `dernier_reglement_clotures_mediane` | DOUBLE | Médiane du délai : Dernier paiement moins déclaration des seuls dossiers CLOTURE (approximation), jours ; calcul sur les valeurs observées non nulles. |
| `dernier_reglement_clotures_p75` | DOUBLE | Quantile 75 % du délai : Dernier paiement moins déclaration des seuls dossiers CLOTURE (approximation), jours ; calcul sur les valeurs observées non nulles. |
| `dernier_reglement_clotures_p90` | DOUBLE | Quantile 90 % du délai : Dernier paiement moins déclaration des seuls dossiers CLOTURE (approximation), jours ; calcul sur les valeurs observées non nulles. |

### `marts.mart_ic` · 100 lignes

Une ligne par axe × groupe × indicateur : estimation et intervalle de confiance à 95 %.

| Colonne | Type | Définition |
|---|---|---|
| `axe` | VARCHAR | Dimension de regroupement ; global signifie tout le portefeuille. |
| `groupe` | VARCHAR | Modalité de la dimension de regroupement. |
| `indicateur` | VARCHAR | Nom de la mesure estimée. |
| `estimation` | DOUBLE | Valeur ponctuelle de l’indicateur, dans son unité brute. |
| `ic_bas` | DOUBLE | Borne inférieure de l’intervalle de confiance, même unité que l’estimation. |
| `ic_haut` | DOUBLE | Borne supérieure de l’intervalle de confiance, même unité que l’estimation. |
| `niveau_confiance` | DOUBLE | Niveau nominal de confiance, 0,95 pour 95 %. |
| `methode` | VARCHAR | Méthode statistique ou de décomposition employée. |
| `nb_clients_blocs` | BIGINT | Nombre de clients uniques, unités de rééchantillonnage du bootstrap. |
| `repetitions` | BIGINT | Nombre de réplications du bootstrap ; zéro pour un intervalle analytique. |
| `graine` | BIGINT | Graine du générateur pseudo-aléatoire, pour reproductibilité. |

### `marts.mart_pareto_valeur` · 13 976 lignes

Classement et concentration des seules valeurs client strictement positives ; pertes exclues et analysées séparément.

| Colonne | Type | Définition |
|---|---|---|
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |
| `valeur_observee` | DOUBLE | Primes acquises cumulées moins sinistres payés cumulés ; euros, sans frais ni réserves. |
| `rang` | BIGINT | Rang décroissant de valeur parmi les clients à valeur positive, départagé par identifiant. |
| `part_clients_positifs` | DOUBLE | Rang / nombre de clients à valeur strictement positive. |
| `part_valeur_positive_cumulee` | DOUBLE | Somme des valeurs positives jusqu’au rang / total des valeurs positives. |

### `marts.mart_portefeuille_mensuel` · 217 100 lignes

Mois × produit × région × canal × zone × formule × âge ; totaux mensuels et stock de contrats actifs en fin de mois.

| Colonne | Type | Définition |
|---|---|---|
| `mois` | DATE | Premier jour du mois civil observé ; observation bornée à janvier 2020-juin 2025 dans les marts dashboard. |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `region` | VARCHAR | Région de résidence (code à 2-4 lettres, ex. IDF) |
| `canal_distribution` | VARCHAR | Canal de souscription (AGENT, COURTIER, WEB) |
| `zone_risque` | INTEGER | Zone tarifaire de risque, de 1 (faible) à 5 (élevé) |
| `formule` | VARCHAR | ESSENTIELLE, CONFORT ou PREMIUM |
| `tranche_age` | VARCHAR | Tranche d’âge au 30/06/2025 ; inconnu si date absente ou âge invalide. |
| `exposition_annees` | DOUBLE | Durée totale observée en années-polices, jours couverts / 365,25. |
| `primes_acquises` | DOUBLE | Somme des primes annuelles proratisées à la durée couverte, en euros. |
| `contrats_actifs` | BIGINT | Stock de contrats actifs au dernier jour du mois : date d’effet incluse et résiliation exclue ; ne pas sommer entre mois. |
| `nb_resiliations` | BIGINT | Résiliations à leur date réelle, parmi les contrats valides de la période observée. |
| `nb_sinistres_retenus` | BIGINT | Nombre de sinistres hors SANS_SUITE et REJETE. |
| `nb_sans_suite` | BIGINT | Nombre de sinistres au statut SANS_SUITE. |
| `nb_rejetes` | BIGINT | Nombre de sinistres au statut REJETE. |
| `charge_retenue` | DOUBLE | Somme payé + réserve restante des sinistres retenus, en euros. |
| `montant_paye_retenu` | DOUBLE | Somme des paiements des sinistres retenus, en euros. |
| `reserve_restante_retenue` | DOUBLE | Somme des réserves restantes conventionnelles des sinistres retenus, en euros. |
| `paiements_flux` | DOUBLE | Paiements effectivement datés du mois, tous statuts ; distincts des paiements des sinistres survenus dans le mois. |

### `marts.mart_queue_couts` · 1 lignes

Synthèse de la queue de charge des sinistres retenus et sensibilité au maximum.

| Colonne | Type | Définition |
|---|---|---|
| `nb_sinistres` | BIGINT | Nombre de sinistres retenus dans la distribution analysée. |
| `mediane` | DOUBLE | Quantile 50 % de la charge par sinistre retenu, en euros. |
| `p90` | DOUBLE | Quantile 90 % de la charge par sinistre retenu, en euros. |
| `p95` | DOUBLE | Quantile 95 % de la charge par sinistre retenu, en euros. |
| `p99` | DOUBLE | Quantile 99 % de la charge par sinistre retenu, en euros. |
| `maximum` | DOUBLE | Charge maximale d’un sinistre retenu, en euros. |
| `nb_top_1pct` | BIGINT | Nombre de dossiers composant le premier centile le plus coûteux, arrondi supérieur. |
| `part_charge_top_1pct` | DOUBLE | Part de la charge portée par ces dossiers ; ratio brut. |
| `charge_totale` | DOUBLE | Charge totale des sinistres retenus, en euros. |
| `cout_moyen` | DOUBLE | Charge retenue / nombre de sinistres retenus, en euros ; null sans sinistre. |
| `cout_moyen_sans_max` | DOUBLE | Coût moyen après retrait du seul dossier maximum, sensibilité non officielle. |
| `ratio_sp` | DOUBLE | Charge retenue / primes acquises ; ratio brut (0,70 = 70 %), null si prime nulle. |
| `ratio_sp_sans_max` | DOUBLE | S/P après retrait du dossier maximum de la charge, primes inchangées ; sensibilité. |

### `marts.mart_retention` · 216 lignes

Proportion de clients retenus par cohorte, produit, ancienneté et groupe fixé à l’entrée ; IC Wilson ajoutés par le script 05.

| Colonne | Type | Définition |
|---|---|---|
| `cohorte` | BIGINT | Année de première souscription valide du client au produit. |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `anciennete` | BIGINT | Nombre entier d’années écoulées depuis la première souscription au produit. |
| `detention_entree` | VARCHAR | Mono/Multi mesuré à la première souscription au produit ; Tous agrège les groupes. |
| `observable` | BOOLEAN | Tous les anniversaires de la cohorte-produit-ancienneté sont au plus tard le 30/06/2025. |
| `nb_clients_cohorte` | BIGINT | Nombre de clients distincts de la cohorte, du produit et du groupe fixé à l’entrée. |
| `nb_retenus` | BIGINT | Clients présents au même produit à l’anniversaire ; null si période inobservable. |
| `taux_retention` | DOUBLE | Clients retenus / clients de cohorte ; proportion brute, null pour une case non observable. |
| `ic_bas` | DOUBLE | Borne inférieure de l’intervalle de confiance, même unité que l’estimation. |
| `ic_haut` | DOUBLE | Borne supérieure de l’intervalle de confiance, même unité que l’estimation. |

### `marts.mart_retention_individuelle` · 121 278 lignes

Une ligne par client, produit et ancienneté : présence au même produit à l’anniversaire ; observabilité de la cohorte entière.

| Colonne | Type | Définition |
|---|---|---|
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `date_entree` | DATE | Date de première souscription valide du client au produit. |
| `cohorte` | BIGINT | Année de première souscription valide du client au produit. |
| `detention_entree` | VARCHAR | Mono/Multi mesuré à la première souscription au produit ; Tous agrège les groupes. |
| `anciennete` | BIGINT | Nombre entier d’années écoulées depuis la première souscription au produit. |
| `date_anniversaire` | DATE | Date d’entrée décalée du nombre d’années d’ancienneté. |
| `observable` | BOOLEAN | Tous les anniversaires de la cohorte-produit-ancienneté sont au plus tard le 30/06/2025. |
| `retenu_anniversaire` | BOOLEAN | Au moins un contrat du même produit actif à l’anniversaire ; null si cohorte non entièrement observable. |

### `marts.mart_segments` · 3 103 lignes

Indicateurs techniques au grain année × segment × tranche d’âge.

| Colonne | Type | Définition |
|---|---|---|
| `annee` | BIGINT | Année civile |
| `segment_id` | VARCHAR | Segment de risque = produit-zone-formule-canal |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `zone_risque` | INTEGER | Zone tarifaire de risque, de 1 (faible) à 5 (élevé) |
| `formule` | VARCHAR | ESSENTIELLE, CONFORT ou PREMIUM |
| `canal_distribution` | VARCHAR | Canal de souscription (AGENT, COURTIER, WEB) |
| `tranche_age` | VARCHAR | Tranche d’âge au 30/06/2025 ; inconnu si date absente ou âge invalide. |
| `exposition_annees` | DOUBLE | Durée totale observée en années-polices, jours couverts / 365,25. |
| `primes_acquises` | DOUBLE | Somme des primes annuelles proratisées à la durée couverte, en euros. |
| `nb_resiliations` | BIGINT | Résiliations à leur date réelle, parmi les contrats valides de la période observée. |
| `nb_contrats_exposes` | BIGINT | Nombre de contrats-années avec exposition positive ; non additif entre années comme nombre unique de contrats. |
| `nb_sinistres_retenus` | BIGINT | Nombre de sinistres hors SANS_SUITE et REJETE. |
| `nb_sans_suite` | BIGINT | Nombre de sinistres au statut SANS_SUITE. |
| `nb_rejetes` | BIGINT | Nombre de sinistres au statut REJETE. |
| `montant_paye_retenu` | DOUBLE | Somme des paiements des sinistres retenus, en euros. |
| `reserve_restante_retenue` | DOUBLE | Somme des réserves restantes conventionnelles des sinistres retenus, en euros. |
| `charge_retenue` | DOUBLE | Somme payé + réserve restante des sinistres retenus, en euros. |
| `montant_paye_tous_statuts` | DOUBLE | Somme des paiements de tous les statuts, en euros. |
| `frequence` | DOUBLE | Sinistres retenus / exposition, en sinistres par année-police ; null si exposition nulle. |
| `cout_moyen` | DOUBLE | Charge retenue / nombre de sinistres retenus, en euros ; null sans sinistre. |
| `prime_moyenne` | DOUBLE | Primes acquises / exposition, en euros par année-police. |
| `ratio_sp` | DOUBLE | Charge retenue / primes acquises ; ratio brut (0,70 = 70 %), null si prime nulle. |
| `taux_resiliation` | DOUBLE | Résiliations / exposition, par année-police ; pas une proportion de clients. |
| `annee_partielle` | BOOLEAN | Vrai pour 2025, limitée à janvier-juin. |

### `marts.mart_sinistres_analyse` · 2 769 lignes

Une ligne par sinistre valide avec charge et profil du contrat/client ; tous statuts.

| Colonne | Type | Définition |
|---|---|---|
| `sinistre_id` | INTEGER | Identifiant du sinistre |
| `contrat_id` | INTEGER | Identifiant du contrat |
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |
| `produit` | VARCHAR | AUTO ou HABITATION |
| `formule` | VARCHAR | ESSENTIELLE, CONFORT ou PREMIUM |
| `zone_risque` | INTEGER | Zone tarifaire de risque, de 1 (faible) à 5 (élevé) |
| `canal_distribution` | VARCHAR | Canal de souscription (AGENT, COURTIER, WEB) |
| `region` | VARCHAR | Région de résidence (code à 2-4 lettres, ex. IDF) |
| `tranche_age` | VARCHAR | Tranche d’âge au 30/06/2025 ; inconnu si date absente ou âge invalide. |
| `garantie` | VARCHAR | Garantie mise en jeu (COLLISION, VOL, DEGAT_EAUX...) |
| `date_survenance` | DATE | Date à laquelle le sinistre s'est produit |
| `statut` | VARCHAR | Statut du sinistre (OUVERT, CLOTURE, SANS_SUITE, REJETE) |
| `retenu` | BOOLEAN | Vrai si le statut est différent de SANS_SUITE et REJETE. |
| `montant_paye` | DOUBLE | Paiements cumulés du sinistre connus à la date d’extraction, en euros. |
| `reserve_restante` | DOUBLE | Réserve conventionnelle encore ouverte, en euros. |
| `charge` | DOUBLE | Montant payé + réserve restante, en euros. |

### `marts.mart_tests_statistiques` · 2 lignes

Deux comparaisons prévues ; p-values brutes et correction de Holm.

| Colonne | Type | Définition |
|---|---|---|
| `comparaison` | VARCHAR | Population et groupes de la comparaison prévue. |
| `test` | VARCHAR | Nom du test statistique utilisé. |
| `statistique` | DOUBLE | Rapport de taux pour Poisson ; statistique U pour Mann-Whitney. |
| `p_value` | DOUBLE | P-value bilatérale brute ; ne mesure ni la taille de l’effet ni sa causalité. |
| `n_groupe_1` | BIGINT | Nombre de sinistres du premier groupe. |
| `n_groupe_2` | BIGINT | Nombre de sinistres du deuxième groupe. |
| `mesure_1` | DOUBLE | Fréquence zone 1 pour Poisson ; médiane de charge AGENT pour Mann-Whitney. |
| `mesure_2` | DOUBLE | Fréquence zone 5 pour Poisson ; médiane de charge WEB pour Mann-Whitney. |
| `interpretation` | VARCHAR | Périmètre, mesure et limites du test. |
| `p_value_holm` | DOUBLE | P-value ajustée de Holm sur les deux comparaisons prévues. |

### `marts.mart_valeur_client` · 15 002 lignes

Une ligne par client maître : primes acquises moins sinistres payés sur la période observée, hors frais et réserves.

| Colonne | Type | Définition |
|---|---|---|
| `client_id_maitre` | INTEGER | Identifiant du client après déduplication (voir prep.client_mapping) |
| `region` | VARCHAR | Région de résidence (code à 2-4 lettres, ex. IDF) |
| `tranche_age` | VARCHAR | Tranche d’âge au 30/06/2025 ; inconnu si date absente ou âge invalide. |
| `csp` | VARCHAR | Catégorie socio-professionnelle |
| `primes_acquises` | DOUBLE | Somme des primes annuelles proratisées à la durée couverte, en euros. |
| `sinistres_payes` | DOUBLE | Paiements cumulés sur les sinistres valides du client, tous statuts, euros. |
| `valeur_observee` | DOUBLE | Primes acquises cumulées moins sinistres payés cumulés ; euros, sans frais ni réserves. |
| `nb_sinistres_tous_statuts` | BIGINT | Nombre de sinistres valides du client, tous statuts confondus. |
| `nb_contrats` | BIGINT | Nombre de contrats valides du client sur l’ensemble de la période. |
| `nb_contrats_actifs` | BIGINT | Nombre de contrats du client actifs au 30/06/2025, résiliation exclue. |
| `auto_actif` | BOOLEAN | Au moins un contrat AUTO actif au 30/06/2025. |
| `habitation_active` | BOOLEAN | Au moins un contrat HABITATION actif au 30/06/2025. |
| `multi_detenteur_actuel` | BOOLEAN | Au moins un contrat de chaque produit actif au 30/06/2025. |

## Métadonnées d'exploitation (`meta`)

### `meta.ingestion_log` · 477 lignes

Journal d'ingestion, une ligne par fichier et par lancement.

| Colonne | Type | Définition |
|---|---|---|
| `run_id` | VARCHAR | Identifiant d'un lancement du pipeline |
| `source` | VARCHAR | Table brute alimentée |
| `fichier` | VARCHAR | Fichier traité |
| `hash` | VARCHAR | Empreinte SHA-256 du fichier (détecte une relivraison identique) |
| `lignes_lues` | INTEGER | Lignes lues dans le fichier |
| `lignes_chargees` | INTEGER | Lignes insérées en couche brute |
| `lignes_rejetees` | INTEGER | Lignes illisibles envoyées dans quarantine.raw_rejets |
| `duree_s` | DOUBLE | Durée en secondes |
| `statut` | VARCHAR | OK, SKIPPED (fichier déjà chargé à l'identique) ou FAILED |
| `message` | VARCHAR | Message d'erreur ou commentaire |
| `horodatage` | TIMESTAMP | Date et heure de l'événement |

### `meta.pipeline_runs` · 41 lignes

Journal des étapes du pipeline, une ligne par étape et par lancement.

| Colonne | Type | Définition |
|---|---|---|
| `run_id` | VARCHAR | Identifiant d'un lancement du pipeline |
| `etape` | VARCHAR | Nom de l'étape (ingest, prep, dedup, quality, core, test, marts, docs) |
| `statut` | VARCHAR | OK ou FAILED |
| `duree_s` | DOUBLE | Durée en secondes |
| `message` | VARCHAR | Message d'erreur ou commentaire |
| `horodatage` | TIMESTAMP | Date et heure de l'événement |

### `meta.qualite_resultats` · 174 lignes

Historique du volume de chaque règle de qualité à chaque exécution.

| Colonne | Type | Définition |
|---|---|---|
| `run_at` | TIMESTAMP | Horodatage de l'exécution des règles |
| `rule_id` | VARCHAR | Identifiant de la règle de qualité (voir quality/rules.yaml) |
| `table_source` | VARCHAR | Table prep concernée par la règle |
| `libelle` | VARCHAR | Description de la règle |
| `dimension` | VARCHAR | Dimension qualité (complétude, unicité, validité, cohérence inter-tables, cohérence temporelle) |
| `gravite` | VARCHAR | bloquante, majeure ou mineure |
| `traitement` | VARCHAR | exclure (hors du cœur), corriger (valeur corrigée), signaler (tracé seulement) |
| `correction` | VARCHAR | Correction appliquée quand le traitement est « corriger » ou précision sur le traitement |
| `volume` | INTEGER | Nombre de lignes concernées |
| `lignes_table` | INTEGER | Nombre de lignes de la table contrôlée |
| `taux` | DOUBLE | volume / lignes_table |

### `meta.test_results` · 131 lignes

Résultat de chaque test bloquant à chaque lancement.

| Colonne | Type | Définition |
|---|---|---|
| `run_id` | VARCHAR | Identifiant d'un lancement du pipeline |
| `module` | VARCHAR | Fichier de test |
| `test` | VARCHAR | Nom du test |
| `statut` | VARCHAR | PASSED, FAILED ou SKIPPED |
| `duree_s` | DOUBLE | Durée en secondes |
| `message` | VARCHAR | Message d'erreur ou commentaire |
| `horodatage` | TIMESTAMP | Date et heure de l'événement |
