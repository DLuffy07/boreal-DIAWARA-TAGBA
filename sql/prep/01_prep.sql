-- =====================================================================
-- COUCHE PREP : typage et normalisation, SANS filtrage.
-- Toutes les lignes brutes sont présentes ici (raw = prep en nombre de lignes).
-- Le tri entre valide / quarantaine est fait par quality/run_rules.py.
-- _row_key identifie une ligne source de façon unique : fichier#ligne.
-- =====================================================================
CREATE SCHEMA IF NOT EXISTS prep;

CREATE OR REPLACE TABLE prep.clients AS
SELECT _source_file || '#' || _row_number AS _row_key,
       client_id AS client_id_brut,
       TRY_CAST(client_id AS INTEGER) AS client_id,
       TRY_STRPTIME(trim(date_naissance), '%d/%m/%Y')::DATE AS date_naissance,
       upper(trim(region)) AS region,
       upper(trim(csp)) AS csp,
       TRY_CAST(consent_marketing AS INTEGER) AS consent_marketing,
       nullif(trim(email_hash), '') AS email_hash,
       _source_file, _row_number, _loaded_at
FROM raw.clients;

CREATE OR REPLACE TABLE prep.contrats AS
SELECT _source_file || '#' || _row_number AS _row_key,
       TRY_CAST(contrat_id AS INTEGER) AS contrat_id,
       TRY_CAST(client_id AS INTEGER) AS client_id,
       upper(trim(produit)) AS produit,
       TRY_CAST(date_effet AS DATE) AS date_effet,
       TRY_CAST(date_resiliation AS DATE) AS date_resiliation,
       upper(trim(formule)) AS formule,
       upper(trim(canal_distribution)) AS canal_distribution,
       TRY_CAST(zone_risque AS INTEGER) AS zone_risque,
       TRY_CAST(franchise AS INTEGER) AS franchise,
       TRY_CAST(bonus_malus AS DOUBLE) AS bonus_malus,
       TRY_CAST(puissance_cv AS DOUBLE) AS puissance_cv,
       TRY_CAST(surface_m2 AS DOUBLE) AS surface_m2,
       TRY_CAST(prime_annuelle AS DOUBLE) AS prime_annuelle,
       _source_file, _row_number, _loaded_at
FROM raw.contrats;

CREATE OR REPLACE TABLE prep.sinistres AS
SELECT _source_file || '#' || _row_number AS _row_key,
       TRY_CAST(sinistre_id AS INTEGER) AS sinistre_id,
       TRY_CAST(contrat_id AS INTEGER) AS contrat_id,
       TRY_CAST(date_survenance AS DATE) AS date_survenance,
       TRY_CAST(date_declaration AS DATE) AS date_declaration,
       upper(trim(garantie)) AS garantie,
       upper(trim(statut)) AS statut,
       TRY_CAST(reserve_initiale AS DOUBLE) AS reserve_initiale,
       _source_file, _row_number, _loaded_at
FROM raw.sinistres;

CREATE OR REPLACE TABLE prep.reglements AS
SELECT _source_file || '#' || _row_number AS _row_key,
       TRY_CAST(paiement_id AS INTEGER) AS paiement_id,
       TRY_CAST(sinistre_id AS INTEGER) AS sinistre_id,
       TRY_CAST(date_paiement AS DATE) AS date_paiement,
       TRY_CAST(montant AS DOUBLE) AS montant,
       -- mois annoncé par le nom du fichier (reglements_AAAA_MM.csv)
       strptime(regexp_extract(_source_file, '(\d{4}_\d{2})', 1), '%Y_%m')::DATE AS mois_fichier,
       _source_file, _row_number, _loaded_at
FROM raw.reglements;

CREATE OR REPLACE TABLE prep.audits AS
SELECT _source_file || '#' || _row_number AS _row_key,
       TRY_CAST(sinistre_id AS INTEGER) AS sinistre_id,
       TRY_CAST(date_audit AS DATE) AS date_audit,
       TRY_CAST(fraude_confirmee AS INTEGER) AS fraude_confirmee,
       _source_file, _row_number, _loaded_at
FROM raw.audits;
