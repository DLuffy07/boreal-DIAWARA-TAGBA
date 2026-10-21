-- =====================================================================
-- CŒUR v1 : schéma en étoile matérialisé en tables.
-- Source : couche prep, privée des lignes en quarantaine (traitement = exclure).
-- Noms et colonnes : docs/contrat.md (inchangés depuis le v0).
-- =====================================================================
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS quarantine;

-- Lignes valides de chaque table prep
CREATE OR REPLACE TEMP VIEW ok_clients AS
SELECT * FROM prep.clients WHERE _row_key NOT IN (SELECT _row_key FROM quarantine.lignes_exclues);
CREATE OR REPLACE TEMP VIEW ok_contrats AS
SELECT * FROM prep.contrats WHERE _row_key NOT IN (SELECT _row_key FROM quarantine.lignes_exclues);
CREATE OR REPLACE TEMP VIEW ok_sinistres AS
SELECT * FROM prep.sinistres WHERE _row_key NOT IN (SELECT _row_key FROM quarantine.lignes_exclues);
CREATE OR REPLACE TEMP VIEW ok_reglements AS
SELECT * FROM prep.reglements WHERE _row_key NOT IN (SELECT _row_key FROM quarantine.lignes_exclues);
CREATE OR REPLACE TEMP VIEW ok_audits AS
SELECT * FROM prep.audits WHERE _row_key NOT IN (SELECT _row_key FROM quarantine.lignes_exclues);

-- ---------- dim_date
CREATE OR REPLACE TABLE core.dim_date AS
SELECT d::DATE AS date, year(d) AS annee, month(d) AS mois, strftime(d, '%Y-%m') AS annee_mois
FROM generate_series(DATE '2019-01-01', DATE '2025-12-31', INTERVAL 1 DAY) t(d);

-- ---------- identifiants absorbés par la déduplication (tracés, jamais supprimés)
CREATE OR REPLACE TABLE quarantine.clients_dedup AS
SELECT m.client_id, m.client_id_maitre, 'DOUBLON_ABSORBE' AS motif, now() AS detecte_le
FROM prep.client_mapping m
WHERE m.client_id <> m.client_id_maitre;

-- ---------- dim_client : SCD2, une ligne par version d'un client maître
-- Livraison initiale : une version par client, valid_from = date d'extraction.
-- Q08 (âge hors [18;100]) : date de naissance mise à null ici, valeur intacte en raw.
CREATE OR REPLACE TABLE core.dim_client AS
WITH a AS (
    SELECT c.*,
           date_diff('year', date_naissance, DATE '2025-06-30')
             - CASE WHEN strftime(date_naissance, '%m%d') > '0630' THEN 1 ELSE 0 END AS age_brut
    FROM ok_clients c
    JOIN prep.client_mapping m ON m.client_id = c.client_id AND m.client_id = m.client_id_maitre
)
SELECT md5(client_id::VARCHAR || '|2025-06-30') AS client_sk,
       client_id AS client_id_maitre,
       CASE WHEN age_brut BETWEEN 18 AND 100 THEN date_naissance END AS date_naissance,
       CASE WHEN age_brut BETWEEN 18 AND 100 THEN age_brut END AS age,
       CASE WHEN age_brut IS NULL OR age_brut < 18 OR age_brut > 100 THEN 'inconnu'
            WHEN age_brut < 25 THEN '18-24'
            WHEN age_brut < 35 THEN '25-34'
            WHEN age_brut < 50 THEN '35-49'
            WHEN age_brut < 65 THEN '50-64'
            ELSE '65+' END AS tranche_age,
       region, csp, consent_marketing = 1 AS consent_marketing,
       DATE '2025-06-30' AS valid_from,
       CAST(NULL AS DATE) AS valid_to,
       TRUE AS is_current,
       md5(coalesce(region, '<null>') || '|' || coalesce(csp, '<null>') || '|'
           || coalesce(consent_marketing::VARCHAR, '<null>')) AS hash_attributs
FROM a;

-- Profil observé au 2025-06-30 : une ligne par client maître. Seule vue à joindre dans les marts.
CREATE OR REPLACE VIEW core.v_client_analyse AS
SELECT client_id_maitre, client_sk, date_naissance, age, tranche_age, region, csp, consent_marketing
FROM core.dim_client
WHERE valid_from = DATE '2025-06-30';

-- ---------- dim_contrat
CREATE OR REPLACE TABLE core.dim_contrat AS
SELECT c.contrat_id, c.client_id, m.client_id_maitre,
       c.produit, c.formule, c.canal_distribution, c.zone_risque, c.franchise, c.bonus_malus,
       c.puissance_cv, c.surface_m2, c.prime_annuelle, c.date_effet, c.date_resiliation,
       c.produit || '-Z' || c.zone_risque || '-' || c.formule || '-' || c.canal_distribution AS segment_id
FROM ok_contrats c
JOIN prep.client_mapping m ON m.client_id = c.client_id;

-- ---------- dim_segment
CREATE OR REPLACE TABLE core.dim_segment AS
SELECT DISTINCT segment_id, produit, zone_risque, formule, canal_distribution FROM core.dim_contrat;

-- ---------- dim_garantie (référentiel)
CREATE OR REPLACE TABLE core.dim_garantie AS
SELECT * FROM (VALUES
    ('BRIS_GLACE', 'AUTO'), ('COLLISION', 'AUTO'), ('RC', 'AUTO'), ('VOL', 'AUTO'),
    ('DEGAT_EAUX', 'HABITATION'), ('INCENDIE', 'HABITATION'), ('TEMPETE', 'HABITATION'),
    ('VOL', 'HABITATION')) t(garantie, produit);

-- ---------- fait_reglement
CREATE OR REPLACE TABLE core.fait_reglement AS
SELECT paiement_id, sinistre_id, date_paiement, montant, _source_file
FROM ok_reglements;

-- ---------- fait_sinistre
CREATE OR REPLACE TABLE core.fait_sinistre AS
WITH p AS (
    SELECT sinistre_id, sum(montant) AS montant_paye, count(*) AS nb_paiements,
           min(date_paiement) AS date_premier_paiement, max(date_paiement) AS date_dernier_paiement
    FROM core.fait_reglement GROUP BY 1
)
SELECT s.sinistre_id, s.contrat_id, s.date_survenance, s.date_declaration, s.garantie, s.statut,
       s.reserve_initiale,
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
       a.fraude_confirmee = 1 AS fraude_confirmee
FROM ok_sinistres s
LEFT JOIN p USING (sinistre_id)
LEFT JOIN ok_audits a USING (sinistre_id);

-- ---------- fait_exposition : une ligne par contrat x année civile
-- Bornes (contrat §Exposition) : effet inclus, résiliation exclue, fin d'observation 30/06/2025 incluse.
CREATE OR REPLACE TABLE core.fait_exposition AS
WITH c AS (
    SELECT contrat_id, client_id_maitre, segment_id, produit, prime_annuelle, date_effet, date_resiliation,
           least(coalesce(date_resiliation, DATE '2025-07-01'), DATE '2025-07-01') AS fin
    FROM core.dim_contrat
), y AS (
    SELECT c.*, an AS annee,
           greatest(date_effet, make_date(an, 1, 1)) AS debut_annee,
           least(fin, make_date(an + 1, 1, 1)) AS fin_annee
    FROM c, range(year(c.date_effet), year(c.fin) + 1) r(an)
)
SELECT contrat_id, annee, client_id_maitre, segment_id, produit,
       date_diff('day', debut_annee, fin_annee) / 365.25 AS exposition_annees,
       prime_annuelle * date_diff('day', debut_annee, fin_annee) / 365.25 AS prime_acquise,
       -- indicatif : les résiliations se comptent depuis dim_contrat (contrat §Exposition)
       date_resiliation IS NOT NULL AND year(date_resiliation) = annee AS resilie_dans_annee
FROM y
WHERE date_diff('day', debut_annee, fin_annee) > 0;
