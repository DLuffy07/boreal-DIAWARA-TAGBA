CREATE OR REPLACE TABLE marts.mart_contrat_mois AS
WITH calendrier AS (
    SELECT m::DATE AS mois,(m+INTERVAL '1 month')::DATE fin_mois
    FROM generate_series(DATE '2020-01-01',DATE '2025-06-01',INTERVAL '1 month') t(m)
), couverture AS (
    SELECT c.contrat_id,m.mois,
       date_diff('day',greatest(c.date_effet,m.mois),
          least(coalesce(c.date_resiliation,DATE '2025-07-01'),DATE '2025-07-01',m.fin_mois)) jours,
       c.prime_annuelle,
       CASE WHEN c.date_effet<m.fin_mois AND
          (c.date_resiliation IS NULL OR c.date_resiliation>=m.fin_mois) THEN 1 ELSE 0 END actif_fin
    FROM core.dim_contrat c CROSS JOIN calendrier m
    WHERE greatest(c.date_effet,m.mois)<least(coalesce(c.date_resiliation,DATE '2025-07-01'),DATE '2025-07-01',m.fin_mois)
), contributions AS (
    SELECT contrat_id,mois,jours/365.25 exposition_annees,
           prime_annuelle*jours/365.25 primes_acquises,actif_fin contrats_actifs,
           0 nb_resiliations,0 nb_sinistres_retenus,0 nb_sans_suite,0 nb_rejetes,
           0.0 charge_retenue,0.0 montant_paye_retenu,0.0 reserve_restante_retenue,
           0.0 paiements_flux
    FROM couverture
    UNION ALL
    SELECT contrat_id,date_trunc('month',date_survenance)::DATE,0.0,0.0,0,0,
           CASE WHEN retenu THEN 1 ELSE 0 END,
           CASE WHEN statut='SANS_SUITE' THEN 1 ELSE 0 END,
           CASE WHEN statut='REJETE' THEN 1 ELSE 0 END,
           CASE WHEN retenu THEN charge ELSE 0 END,
           CASE WHEN retenu THEN montant_paye ELSE 0 END,
           CASE WHEN retenu THEN reserve_restante ELSE 0 END,0.0
    FROM core.fait_sinistre
    UNION ALL
    SELECT s.contrat_id,date_trunc('month',p.date_paiement)::DATE,0.0,0.0,0,0,0,0,0,0.0,0.0,0.0,p.montant
    FROM core.fait_reglement p JOIN core.fait_sinistre s USING(sinistre_id)
    UNION ALL
    SELECT contrat_id,date_trunc('month',date_resiliation)::DATE,0.0,0.0,0,1,0,0,0,0.0,0.0,0.0,0.0
    FROM core.dim_contrat WHERE date_resiliation BETWEEN DATE '2020-01-01' AND DATE '2025-06-30'
), ag AS (
    SELECT contrat_id,mois,sum(exposition_annees) exposition_annees,
       sum(primes_acquises) primes_acquises,sum(contrats_actifs)::BIGINT contrats_actifs,
       sum(nb_resiliations)::BIGINT nb_resiliations,sum(nb_sinistres_retenus)::BIGINT nb_sinistres_retenus,
       sum(nb_sans_suite)::BIGINT nb_sans_suite,sum(nb_rejetes)::BIGINT nb_rejetes,
       sum(charge_retenue) charge_retenue,sum(montant_paye_retenu) montant_paye_retenu,
       sum(reserve_restante_retenue) reserve_restante_retenue,sum(paiements_flux) paiements_flux
    FROM contributions GROUP BY 1,2
)
SELECT a.*,c.client_id_maitre,c.produit,c.formule,c.canal_distribution,c.zone_risque,c.segment_id,
       cl.region,cl.tranche_age
FROM ag a JOIN core.dim_contrat c USING(contrat_id)
JOIN core.v_client_analyse cl USING(client_id_maitre);

CREATE OR REPLACE TABLE marts.mart_portefeuille_mensuel AS
SELECT mois,produit,region,canal_distribution,zone_risque,formule,tranche_age,
       sum(exposition_annees) exposition_annees,sum(primes_acquises) primes_acquises,
       sum(contrats_actifs)::BIGINT contrats_actifs,sum(nb_resiliations)::BIGINT nb_resiliations,
       sum(nb_sinistres_retenus)::BIGINT nb_sinistres_retenus,
       sum(nb_sans_suite)::BIGINT nb_sans_suite,sum(nb_rejetes)::BIGINT nb_rejetes,
       sum(charge_retenue) charge_retenue,sum(montant_paye_retenu) montant_paye_retenu,
       sum(reserve_restante_retenue) reserve_restante_retenue,sum(paiements_flux) paiements_flux
FROM marts.mart_contrat_mois GROUP BY ALL;

CREATE OR REPLACE TABLE marts.mart_cohortes_dashboard AS
WITH initial AS (
    SELECT client_id_maitre,produit,canal_distribution,
           row_number() OVER(PARTITION BY client_id_maitre,produit ORDER BY date_effet,contrat_id) ordre
    FROM core.dim_contrat
)
SELECT r.*,cl.region,cl.tranche_age,i.canal_distribution
FROM marts.mart_retention_individuelle r
JOIN core.v_client_analyse cl USING(client_id_maitre)
JOIN initial i ON r.client_id_maitre=i.client_id_maitre AND r.produit=i.produit AND i.ordre=1;
