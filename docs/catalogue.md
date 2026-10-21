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

### `quarantine.clients_dedup` · 0 lignes

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

### `core.dim_client` · 15 200 lignes

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

### `marts.exploitation_runs` · 4 lignes

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

### `marts.exploitation_tests` · 35 lignes

Résultat des tests bloquants du dernier lancement.

| Colonne | Type | Définition |
|---|---|---|
| `module` | VARCHAR | Fichier de test |
| `test` | VARCHAR | Nom du test |
| `statut` | VARCHAR | PASSED, FAILED ou SKIPPED |
| `duree_s` | DOUBLE | Durée en secondes |
| `message` | VARCHAR | Message d'erreur ou commentaire |
| `horodatage` | TIMESTAMP | Date et heure de l'événement |

## Métadonnées d'exploitation (`meta`)

### `meta.ingestion_log` · 341 lignes

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

### `meta.pipeline_runs` · 24 lignes

Journal des étapes du pipeline, une ligne par étape et par lancement.

| Colonne | Type | Définition |
|---|---|---|
| `run_id` | VARCHAR | Identifiant d'un lancement du pipeline |
| `etape` | VARCHAR | Nom de l'étape (ingest, prep, dedup, quality, core, test, marts, docs) |
| `statut` | VARCHAR | OK ou FAILED |
| `duree_s` | DOUBLE | Durée en secondes |
| `message` | VARCHAR | Message d'erreur ou commentaire |
| `horodatage` | TIMESTAMP | Date et heure de l'événement |

### `meta.qualite_resultats` · 116 lignes

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

### `meta.test_results` · 35 lignes

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
