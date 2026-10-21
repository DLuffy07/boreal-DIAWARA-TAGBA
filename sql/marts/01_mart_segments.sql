-- Grain : année x segment x tranche d'âge (profil observé au 30/06/2025).
-- Addition de contributions séparées : aucune jointure faits/faits.
CREATE OR REPLACE TABLE marts.mart_segments AS
WITH contrats AS (
    SELECT c.contrat_id, c.date_resiliation, s.segment_id, s.produit, s.zone_risque,
           s.formule, s.canal_distribution,
           COALESCE(cl.tranche_age, 'inconnu') AS tranche_age
    FROM core.dim_contrat c
    JOIN core.dim_segment s
      ON c.produit = s.produit AND c.zone_risque = s.zone_risque
     AND c.formule = s.formule AND c.canal_distribution = s.canal_distribution
    JOIN core.v_client_analyse cl USING (client_id_maitre)
), contributions AS (
    SELECT e.annee, c.segment_id, c.produit, c.zone_risque, c.formule,
           c.canal_distribution, c.tranche_age,
           e.exposition_annees, e.prime_acquise,
           0 AS nb_resiliations,
           1 AS nb_contrats_exposes,
           0 AS nb_sinistres_retenus, 0 AS nb_sans_suite, 0 AS nb_rejetes,
           0.0 AS montant_paye_retenu, 0.0 AS reserve_restante_retenue,
           0.0 AS charge_retenue, 0.0 AS montant_paye_tous_statuts
    FROM core.fait_exposition e JOIN contrats c USING (contrat_id)
    UNION ALL
    SELECT year(f.date_survenance)::INTEGER, c.segment_id, c.produit,
           c.zone_risque, c.formule, c.canal_distribution, c.tranche_age,
           0.0, 0.0, 0, 0,
           CASE WHEN f.statut NOT IN ('SANS_SUITE','REJETE') THEN 1 ELSE 0 END,
           CASE WHEN f.statut = 'SANS_SUITE' THEN 1 ELSE 0 END,
           CASE WHEN f.statut = 'REJETE' THEN 1 ELSE 0 END,
           CASE WHEN f.statut NOT IN ('SANS_SUITE','REJETE') THEN f.montant_paye ELSE 0 END,
           CASE WHEN f.statut NOT IN ('SANS_SUITE','REJETE') THEN f.reserve_restante ELSE 0 END,
           CASE WHEN f.statut NOT IN ('SANS_SUITE','REJETE') THEN f.charge ELSE 0 END,
           f.montant_paye
    FROM core.fait_sinistre f JOIN contrats c USING (contrat_id)
    UNION ALL
    -- La date réelle décide du mois/année, même sans exposition dans cette période.
    SELECT year(c.date_resiliation)::INTEGER, c.segment_id, c.produit,
           c.zone_risque, c.formule, c.canal_distribution, c.tranche_age,
           0.0, 0.0, 1, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0
    FROM contrats c
    WHERE c.date_resiliation BETWEEN DATE '2020-01-01' AND DATE '2025-06-30'
), total AS (
    SELECT annee, segment_id, produit, zone_risque, formule,
           canal_distribution, tranche_age,
           SUM(exposition_annees) AS exposition_annees,
           SUM(prime_acquise) AS primes_acquises,
           SUM(nb_resiliations)::BIGINT AS nb_resiliations,
           SUM(nb_contrats_exposes)::BIGINT AS nb_contrats_exposes,
           SUM(nb_sinistres_retenus)::BIGINT AS nb_sinistres_retenus,
           SUM(nb_sans_suite)::BIGINT AS nb_sans_suite,
           SUM(nb_rejetes)::BIGINT AS nb_rejetes,
           SUM(montant_paye_retenu) AS montant_paye_retenu,
           SUM(reserve_restante_retenue) AS reserve_restante_retenue,
           SUM(charge_retenue) AS charge_retenue,
           SUM(montant_paye_tous_statuts) AS montant_paye_tous_statuts
    FROM contributions GROUP BY ALL
)
SELECT *, nb_sinistres_retenus / NULLIF(exposition_annees, 0) AS frequence,
       charge_retenue / NULLIF(nb_sinistres_retenus, 0) AS cout_moyen,
       primes_acquises / NULLIF(exposition_annees, 0) AS prime_moyenne,
       charge_retenue / NULLIF(primes_acquises, 0) AS ratio_sp,
       nb_resiliations / NULLIF(exposition_annees, 0) AS taux_resiliation,
       annee = 2025 AS annee_partielle
FROM total;
