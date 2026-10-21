-- =====================================================================
-- CŒUR v0 : vues posées directement sur la couche brute.
-- Objectif : donner à B des tables aux noms définitifs le plus tôt possible.
-- Déduplication branchée (prep.client_mapping). Quarantaine qualité : en v1.
-- Les noms et colonnes suivent docs/contrat.md et ne changeront plus.
-- =====================================================================
CREATE SCHEMA IF NOT EXISTS core;

-- ---------- dim_date
CREATE OR REPLACE VIEW core.dim_date AS
SELECT d::DATE AS date,
       year(d) AS annee,
       month(d) AS mois,
       strftime(d, '%Y-%m') AS annee_mois
FROM generate_series(DATE '2019-01-01', DATE '2025-12-31', INTERVAL 1 DAY) t(d);

-- ---------- client_mapping : produit par le script de B (quality/dedup_clients.py).
-- S'il n'a pas encore tourné, mapping identité pour que le cœur se construise quand même.
CREATE SCHEMA IF NOT EXISTS prep;
CREATE SCHEMA IF NOT EXISTS quarantine;
CREATE TABLE IF NOT EXISTS prep.client_mapping AS
SELECT TRY_CAST(client_id AS INTEGER) AS client_id, TRY_CAST(client_id AS INTEGER) AS client_id_maitre
FROM raw.clients;

-- Identifiants absorbés par la déduplication : tracés avec leur motif (jamais supprimés)
CREATE OR REPLACE TABLE quarantine.clients_dedup AS
SELECT m.client_id, m.client_id_maitre, 'DOUBLON_ABSORBE' AS motif, now() AS detecte_le
FROM prep.client_mapping m
WHERE m.client_id <> m.client_id_maitre;

-- ---------- dim_client : SCD2, une ligne par version d'un client maître
-- Livraison initiale : une seule version par client, valid_from = date d'extraction.
CREATE OR REPLACE VIEW core.dim_client AS
WITH c AS (
    SELECT TRY_CAST(client_id AS INTEGER) AS client_id,
           TRY_STRPTIME(date_naissance, '%d/%m/%Y')::DATE AS date_naissance,
           region, csp,
           TRY_CAST(consent_marketing AS INTEGER) = 1 AS consent_marketing
    FROM raw.clients
), a AS (
    SELECT c.*, date_diff('year', date_naissance, DATE '2025-06-30')
              - CASE WHEN strftime(date_naissance, '%m%d') > '0630' THEN 1 ELSE 0 END AS age
    FROM c
    JOIN prep.client_mapping m ON m.client_id = c.client_id AND m.client_id = m.client_id_maitre
)
SELECT md5(client_id::VARCHAR || '|2025-06-30') AS client_sk,
       client_id AS client_id_maitre,
       CASE WHEN age BETWEEN 18 AND 100 THEN date_naissance END AS date_naissance,
       CASE WHEN age BETWEEN 18 AND 100 THEN age END AS age,
       CASE WHEN age IS NULL OR age < 18 OR age > 100 THEN 'inconnu'
            WHEN age < 25 THEN '18-24'
            WHEN age < 35 THEN '25-34'
            WHEN age < 50 THEN '35-49'
            WHEN age < 65 THEN '50-64'
            ELSE '65+' END AS tranche_age,
       region, csp, consent_marketing,
       DATE '2025-06-30' AS valid_from,
       CAST(NULL AS DATE) AS valid_to,
       TRUE AS is_current,
       md5(coalesce(region, '<null>') || '|' || coalesce(csp, '<null>') || '|'
           || coalesce(consent_marketing::VARCHAR, '<null>')) AS hash_attributs
FROM a;

-- ---------- v_client_analyse : profil observé au 2025-06-30, une ligne par client maître.
-- C'est la SEULE vue à joindre dans les marts (jamais dim_client entière).
CREATE OR REPLACE VIEW core.v_client_analyse AS
SELECT client_id_maitre, client_sk, date_naissance, age, tranche_age, region, csp, consent_marketing
FROM core.dim_client
WHERE valid_from = DATE '2025-06-30';

-- ---------- dim_contrat
CREATE OR REPLACE VIEW core.dim_contrat AS
SELECT TRY_CAST(contrat_id AS INTEGER) AS contrat_id,
       TRY_CAST(c.client_id AS INTEGER) AS client_id,
       m.client_id_maitre,
       produit, formule, canal_distribution,
       TRY_CAST(zone_risque AS INTEGER) AS zone_risque,
       TRY_CAST(franchise AS INTEGER) AS franchise,
       TRY_CAST(bonus_malus AS DOUBLE) AS bonus_malus,
       TRY_CAST(puissance_cv AS DOUBLE) AS puissance_cv,
       TRY_CAST(surface_m2 AS DOUBLE) AS surface_m2,
       TRY_CAST(prime_annuelle AS DOUBLE) AS prime_annuelle,
       TRY_CAST(date_effet AS DATE) AS date_effet,
       TRY_CAST(date_resiliation AS DATE) AS date_resiliation,
       produit || '-Z' || zone_risque || '-' || formule || '-' || canal_distribution AS segment_id
FROM raw.contrats c
LEFT JOIN prep.client_mapping m ON m.client_id = TRY_CAST(c.client_id AS INTEGER);

-- ---------- dim_segment
CREATE OR REPLACE VIEW core.dim_segment AS
SELECT DISTINCT segment_id, produit, zone_risque, formule, canal_distribution
FROM core.dim_contrat;

-- ---------- dim_garantie
CREATE OR REPLACE VIEW core.dim_garantie AS
SELECT DISTINCT s.garantie, c.produit
FROM raw.sinistres s
JOIN core.dim_contrat c ON c.contrat_id = TRY_CAST(s.contrat_id AS INTEGER);

-- ---------- fait_reglement (v0 : doublons de paiement_id retirés, on garde la 1re livraison)
CREATE OR REPLACE VIEW core.fait_reglement AS
SELECT TRY_CAST(paiement_id AS INTEGER) AS paiement_id,
       TRY_CAST(sinistre_id AS INTEGER) AS sinistre_id,
       TRY_CAST(date_paiement AS DATE) AS date_paiement,
       TRY_CAST(montant AS DOUBLE) AS montant,
       _source_file
FROM raw.reglements
QUALIFY row_number() OVER (PARTITION BY paiement_id ORDER BY _source_file, _row_number) = 1;

-- ---------- fait_sinistre
CREATE OR REPLACE VIEW core.fait_sinistre AS
WITH s AS (
    SELECT TRY_CAST(sinistre_id AS INTEGER) AS sinistre_id,
           TRY_CAST(contrat_id AS INTEGER) AS contrat_id,
           TRY_CAST(date_survenance AS DATE) AS date_survenance,
           TRY_CAST(date_declaration AS DATE) AS date_declaration,
           garantie, statut,
           TRY_CAST(reserve_initiale AS DOUBLE) AS reserve_initiale
    FROM raw.sinistres
), p AS (
    SELECT sinistre_id, sum(montant) AS montant_paye, count(*) AS nb_paiements,
           min(date_paiement) AS date_premier_paiement, max(date_paiement) AS date_dernier_paiement
    FROM core.fait_reglement GROUP BY 1
), a AS (
    SELECT TRY_CAST(sinistre_id AS INTEGER) AS sinistre_id,
           TRY_CAST(date_audit AS DATE) AS date_audit,
           TRY_CAST(fraude_confirmee AS INTEGER) = 1 AS fraude_confirmee
    FROM raw.audits
)
SELECT s.*,
       coalesce(p.montant_paye, 0) AS montant_paye,
       coalesce(p.nb_paiements, 0) AS nb_paiements,
       p.date_premier_paiement, p.date_dernier_paiement,
       CASE WHEN s.statut = 'OUVERT'
            THEN greatest(s.reserve_initiale - coalesce(p.montant_paye, 0), 0) ELSE 0 END AS reserve_restante,
       coalesce(p.montant_paye, 0)
         + CASE WHEN s.statut = 'OUVERT'
                THEN greatest(s.reserve_initiale - coalesce(p.montant_paye, 0), 0) ELSE 0 END AS charge,
       s.statut NOT IN ('SANS_SUITE', 'REJETE') AS retenu,
       a.sinistre_id IS NOT NULL AS audite,
       a.date_audit,
       a.fraude_confirmee
FROM s
LEFT JOIN p USING (sinistre_id)
LEFT JOIN a USING (sinistre_id);

-- ---------- fait_exposition : une ligne par contrat x année civile
-- Couverture = [date_effet ; fin[ avec fin = date_resiliation, ou 2025-07-01 (fin d'observation incluse)
CREATE OR REPLACE VIEW core.fait_exposition AS
WITH c AS (
    SELECT contrat_id, client_id_maitre, segment_id, produit, prime_annuelle,
           date_effet, date_resiliation,
           least(coalesce(date_resiliation, DATE '2025-07-01'), DATE '2025-07-01') AS fin
    FROM core.dim_contrat
    WHERE date_effet IS NOT NULL
), y AS (
    SELECT c.*, an AS annee,
           greatest(date_effet, make_date(an, 1, 1)) AS debut_annee,
           least(fin, make_date(an + 1, 1, 1)) AS fin_annee
    FROM c, range(year(c.date_effet), year(c.fin) + 1) r(an)
)
SELECT contrat_id, annee, client_id_maitre, segment_id, produit,
       date_diff('day', debut_annee, fin_annee) / 365.25 AS exposition_annees,
       prime_annuelle * date_diff('day', debut_annee, fin_annee) / 365.25 AS prime_acquise,
       date_resiliation IS NOT NULL AND year(date_resiliation) = annee AS resilie_dans_annee  -- indicatif : compter les résiliations depuis dim_contrat (contrat §Exposition)
FROM y
WHERE date_diff('day', debut_annee, fin_annee) > 0;
