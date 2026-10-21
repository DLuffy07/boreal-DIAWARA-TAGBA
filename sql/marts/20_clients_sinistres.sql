-- L4 : uniquement les contrats/sinistres du cœur validé, profil client de juin 2025.
CREATE OR REPLACE TABLE marts.mart_valeur_client AS
WITH primes AS (
    SELECT c.client_id_maitre,sum(e.prime_acquise) primes_acquises
    FROM core.fait_exposition e JOIN core.dim_contrat c USING(contrat_id) GROUP BY 1
), couts AS (
    SELECT c.client_id_maitre,sum(s.montant_paye) sinistres_payes,
           count(*) nb_sinistres_tous_statuts
    FROM core.fait_sinistre s JOIN core.dim_contrat c USING(contrat_id) GROUP BY 1
), contrats AS (
    SELECT client_id_maitre,count(*) nb_contrats,
           count(*) FILTER(WHERE date_effet<=DATE '2025-06-30' AND
             (date_resiliation IS NULL OR date_resiliation>DATE '2025-06-30')) nb_contrats_actifs,
           bool_or(produit='AUTO' AND date_effet<=DATE '2025-06-30' AND
             (date_resiliation IS NULL OR date_resiliation>DATE '2025-06-30')) auto_actif,
           bool_or(produit='HABITATION' AND date_effet<=DATE '2025-06-30' AND
             (date_resiliation IS NULL OR date_resiliation>DATE '2025-06-30')) habitation_active
    FROM core.dim_contrat GROUP BY 1
)
SELECT cl.client_id_maitre,cl.region,cl.tranche_age,cl.csp,
       coalesce(p.primes_acquises,0) primes_acquises,
       coalesce(s.sinistres_payes,0) sinistres_payes,
       coalesce(p.primes_acquises,0)-coalesce(s.sinistres_payes,0) valeur_observee,
       coalesce(s.nb_sinistres_tous_statuts,0) nb_sinistres_tous_statuts,
       coalesce(c.nb_contrats,0) nb_contrats,
       coalesce(c.nb_contrats_actifs,0) nb_contrats_actifs,
       coalesce(c.auto_actif,false) auto_actif,
       coalesce(c.habitation_active,false) habitation_active,
       coalesce(c.auto_actif AND c.habitation_active,false) multi_detenteur_actuel
FROM core.v_client_analyse cl
LEFT JOIN primes p USING(client_id_maitre)
LEFT JOIN couts s USING(client_id_maitre)
LEFT JOIN contrats c USING(client_id_maitre);

-- Population pour la rétention : première souscription par client maître et produit.
CREATE OR REPLACE TABLE marts.mart_retention_individuelle AS
WITH firsts AS (
    SELECT client_id_maitre,produit,min(date_effet) date_entree
    FROM core.dim_contrat GROUP BY ALL
), base AS (
    SELECT f.*,year(date_entree) cohorte,
       CASE WHEN EXISTS(SELECT 1 FROM core.dim_contrat x
         WHERE x.client_id_maitre=f.client_id_maitre AND x.produit<>f.produit
         AND x.date_effet<=f.date_entree AND
           (x.date_resiliation IS NULL OR x.date_resiliation>f.date_entree))
       THEN 'Multi à entrée' ELSE 'Mono à entrée' END detention_entree
    FROM firsts f
), anniversaries AS (
    SELECT b.*,a.anciennete,(date_entree+a.anciennete*INTERVAL '1 year')::DATE date_anniversaire,
           max((date_entree+a.anciennete*INTERVAL '1 year')::DATE)
             OVER(PARTITION BY cohorte,produit,a.anciennete)<=DATE '2025-06-30' AS observable
    FROM base b CROSS JOIN range(0,6) a(anciennete)
)
SELECT a.*,
       CASE WHEN observable THEN EXISTS(SELECT 1 FROM core.dim_contrat x
         WHERE x.client_id_maitre=a.client_id_maitre AND x.produit=a.produit
         AND x.date_effet<=a.date_anniversaire AND
           (x.date_resiliation IS NULL OR x.date_resiliation>a.date_anniversaire))
       ELSE NULL END AS retenu_anniversaire
FROM anniversaries a;

CREATE OR REPLACE TABLE marts.mart_retention AS
WITH expanded AS (
    SELECT * FROM marts.mart_retention_individuelle
    UNION ALL
    SELECT client_id_maitre,produit,date_entree,cohorte,'Tous',anciennete,date_anniversaire,
           observable,retenu_anniversaire FROM marts.mart_retention_individuelle
)
SELECT cohorte,produit,anciennete,detention_entree,observable,
       count(*)::BIGINT nb_clients_cohorte,
       CASE WHEN observable THEN count(*) FILTER(WHERE retenu_anniversaire) ELSE NULL END::BIGINT nb_retenus,
       CASE WHEN observable THEN count(*) FILTER(WHERE retenu_anniversaire)::DOUBLE/count(*) ELSE NULL END taux_retention
FROM expanded GROUP BY cohorte,produit,anciennete,detention_entree,observable;

-- Pareto uniquement sur les valeurs positives : les pertes sont analysées séparément.
CREATE OR REPLACE TABLE marts.mart_pareto_valeur AS
SELECT client_id_maitre,valeur_observee,
       row_number() OVER(ORDER BY valeur_observee DESC,client_id_maitre) rang,
       row_number() OVER(ORDER BY valeur_observee DESC,client_id_maitre)::DOUBLE/count(*) OVER() part_clients_positifs,
       sum(valeur_observee) OVER(ORDER BY valeur_observee DESC,client_id_maitre ROWS UNBOUNDED PRECEDING)/
         sum(valeur_observee) OVER() part_valeur_positive_cumulee
FROM marts.mart_valeur_client WHERE valeur_observee>0;

CREATE OR REPLACE TABLE marts.mart_delais AS
SELECT s.sinistre_id,s.contrat_id,c.client_id_maitre,c.produit,c.formule,c.canal_distribution,
       c.zone_risque,cl.region,cl.tranche_age,s.garantie,s.statut,s.date_survenance,
       s.date_declaration,s.date_premier_paiement,s.date_dernier_paiement,
       s.montant_paye,s.charge,s.audite,s.fraude_confirmee,s.date_audit,
       date_diff('day',s.date_survenance,s.date_declaration) delai_declaration_jours,
       CASE WHEN s.date_premier_paiement>=s.date_declaration
         THEN date_diff('day',s.date_declaration,s.date_premier_paiement) END delai_premier_reglement_jours,
       CASE WHEN s.statut='CLOTURE' AND s.date_dernier_paiement>=s.date_declaration
         THEN date_diff('day',s.date_declaration,s.date_dernier_paiement) END delai_dernier_reglement_clotures_jours,
       coalesce(s.date_premier_paiement<s.date_declaration,false) paiement_avant_declaration,
       CASE WHEN s.charge<1000 THEN '<1 000 €' WHEN s.charge<5000 THEN '1 000–4 999 €'
            WHEN s.charge<20000 THEN '5 000–19 999 €' ELSE '20 000 € et +' END tranche_charge,
       CASE WHEN date_diff('day',s.date_survenance,s.date_declaration)<=7 THEN '0–7 jours'
            WHEN date_diff('day',s.date_survenance,s.date_declaration)<=30 THEN '8–30 jours'
            ELSE '>30 jours' END tranche_delai_declaration
FROM core.fait_sinistre s JOIN core.dim_contrat c USING(contrat_id)
JOIN core.v_client_analyse cl USING(client_id_maitre);

CREATE OR REPLACE TABLE marts.mart_delais_garantie AS
SELECT garantie,count(*) nb_dossiers,
       count(*) FILTER(WHERE statut='OUVERT') nb_ouverts,
       count(delai_declaration_jours) nb_delais_declaration,
       count(delai_premier_reglement_jours) nb_delais_premier_reglement,
       count(delai_dernier_reglement_clotures_jours) nb_delais_dernier_reglement_clotures,
       count(*) FILTER(WHERE paiement_avant_declaration) nb_paiements_avant_declaration,
       median(delai_declaration_jours) declaration_mediane,
       quantile_cont(delai_declaration_jours,.75) declaration_p75,
       quantile_cont(delai_declaration_jours,.90) declaration_p90,
       median(delai_premier_reglement_jours) premier_reglement_mediane,
       quantile_cont(delai_premier_reglement_jours,.75) premier_reglement_p75,
       quantile_cont(delai_premier_reglement_jours,.90) premier_reglement_p90,
       median(delai_dernier_reglement_clotures_jours) dernier_reglement_clotures_mediane,
       quantile_cont(delai_dernier_reglement_clotures_jours,.75) dernier_reglement_clotures_p75,
       quantile_cont(delai_dernier_reglement_clotures_jours,.90) dernier_reglement_clotures_p90
FROM marts.mart_delais GROUP BY 1;

CREATE OR REPLACE TABLE marts.mart_audits AS
WITH audites AS (SELECT * FROM marts.mart_delais WHERE audite),
long AS (
    SELECT 'garantie' axe,garantie groupe,charge,montant_paye,fraude_confirmee FROM audites
    UNION ALL SELECT 'tranche_charge',tranche_charge,charge,montant_paye,fraude_confirmee FROM audites
    UNION ALL SELECT 'delai_declaration',tranche_delai_declaration,charge,montant_paye,fraude_confirmee FROM audites
    UNION ALL SELECT 'global','Tous',charge,montant_paye,fraude_confirmee FROM audites
)
SELECT axe,groupe,count(*)::BIGINT nb_audits,
       count(*) FILTER(WHERE fraude_confirmee)::BIGINT nb_fraudes_confirmees,
       count(*) FILTER(WHERE fraude_confirmee)::DOUBLE/count(*) taux_confirmation,
       sum(charge) charge_auditee,
       sum(charge) FILTER(WHERE fraude_confirmee) charge_dossiers_confirmes,
       sum(montant_paye) FILTER(WHERE fraude_confirmee) paye_dossiers_confirmes
FROM long GROUP BY ALL;
