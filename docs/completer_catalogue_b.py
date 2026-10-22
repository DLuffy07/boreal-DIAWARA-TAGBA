"""Complète le catalogue existant sans supprimer les définitions de A."""
import argparse
from pathlib import Path
import duckdb
import yaml

TABLES={
 'quarantine.clients_a_revoir':'Clients laissés séparés par la déduplication, une ligne par client à examiner.',
 'marts.mart_segments':'Indicateurs techniques au grain année × segment × tranche d’âge.',
 'marts.mart_contrats_analyse':'Une ligne par contrat valide : exposition et mesures cumulées observées, profil client de juin 2025.',
 'marts.mart_sinistres_analyse':'Une ligne par sinistre valide avec charge et profil du contrat/client ; tous statuts.',
 'marts.mart_ic':'Une ligne par axe × groupe × indicateur : estimation et intervalle de confiance à 95 %.',
 'marts.mart_tests_statistiques':'Deux comparaisons prévues ; p-values brutes et correction de Holm.',
 'marts.mart_queue_couts':'Synthèse de la queue de charge des sinistres retenus et sensibilité au maximum.',
 'marts.mart_decomposition_sp':'Variation annuelle globale du S/P expliquée par trois effets Shapley ; 2025 partielle.',
 'marts.mart_contributions_segments':'Contribution comptable de chaque segment à la variation annuelle du S/P global.'
}
DEFS={
 'tranche_age':'Tranche d’âge au 30/06/2025 ; inconnu si date absente ou âge invalide.',
 'exposition_annees':'Durée totale observée en années-polices, jours couverts / 365,25.',
 'primes_acquises':'Somme des primes annuelles proratisées à la durée couverte, en euros.',
 'nb_resiliations':'Résiliations à leur date réelle, parmi les contrats valides de la période observée.',
 'nb_contrats_exposes':'Nombre de contrats-années avec exposition positive ; non additif entre années comme nombre unique de contrats.',
 'nb_sinistres_retenus':'Nombre de sinistres hors SANS_SUITE et REJETE.',
 'nb_sans_suite':'Nombre de sinistres au statut SANS_SUITE.',
 'nb_rejetes':'Nombre de sinistres au statut REJETE.',
 'montant_paye_retenu':'Somme des paiements des sinistres retenus, en euros.',
 'reserve_restante_retenue':'Somme des réserves restantes conventionnelles des sinistres retenus, en euros.',
 'charge_retenue':'Somme payé + réserve restante des sinistres retenus, en euros.',
 'montant_paye_tous_statuts':'Somme des paiements de tous les statuts, en euros.',
 'frequence':'Sinistres retenus / exposition, en sinistres par année-police ; null si exposition nulle.',
 'cout_moyen':'Charge retenue / nombre de sinistres retenus, en euros ; null sans sinistre.',
 'prime_moyenne':'Primes acquises / exposition, en euros par année-police.',
 'ratio_sp':'Charge retenue / primes acquises ; ratio brut (0,70 = 70 %), null si prime nulle.',
 'taux_resiliation':'Résiliations / exposition, par année-police ; pas une proportion de clients.',
 'annee_partielle':'Vrai pour 2025, limitée à janvier-juin.',
 'retenu':'Vrai si le statut est différent de SANS_SUITE et REJETE.',
 'montant_paye':'Paiements cumulés du sinistre connus à la date d’extraction, en euros.',
 'reserve_restante':'Réserve conventionnelle encore ouverte, en euros.',
 'charge':'Montant payé + réserve restante, en euros.',
 'axe':'Dimension de regroupement ; global signifie tout le portefeuille.',
 'groupe':'Modalité de la dimension de regroupement.',
 'indicateur':'Nom de la mesure estimée.',
 'estimation':'Valeur ponctuelle de l’indicateur, dans son unité brute.',
 'ic_bas':'Borne inférieure de l’intervalle de confiance, même unité que l’estimation.',
 'ic_haut':'Borne supérieure de l’intervalle de confiance, même unité que l’estimation.',
 'niveau_confiance':'Niveau nominal de confiance, 0,95 pour 95 %.',
 'methode':'Méthode statistique ou de décomposition employée.',
 'nb_clients_blocs':'Nombre de clients uniques, unités de rééchantillonnage du bootstrap.',
 'repetitions':'Nombre de réplications du bootstrap ; zéro pour un intervalle analytique.',
 'graine':'Graine du générateur pseudo-aléatoire, pour reproductibilité.',
 'comparaison':'Population et groupes de la comparaison prévue.',
 'test':'Nom du test statistique utilisé.',
 'statistique':'Rapport de taux pour Poisson ; statistique U pour Mann-Whitney.',
 'p_value':'P-value bilatérale brute ; ne mesure ni la taille de l’effet ni sa causalité.',
 'p_value_holm':'P-value ajustée de Holm sur les deux comparaisons prévues.',
 'n_groupe_1':'Nombre de sinistres du premier groupe.',
 'n_groupe_2':'Nombre de sinistres du deuxième groupe.',
 'mesure_1':'Fréquence zone 1 pour Poisson ; médiane de charge AGENT pour Mann-Whitney.',
 'mesure_2':'Fréquence zone 5 pour Poisson ; médiane de charge WEB pour Mann-Whitney.',
 'interpretation':'Périmètre, mesure et limites du test.',
 'nb_sinistres':'Nombre de sinistres retenus dans la distribution analysée.',
 'mediane':'Quantile 50 % de la charge par sinistre retenu, en euros.',
 'p90':'Quantile 90 % de la charge par sinistre retenu, en euros.',
 'p95':'Quantile 95 % de la charge par sinistre retenu, en euros.',
 'p99':'Quantile 99 % de la charge par sinistre retenu, en euros.',
 'maximum':'Charge maximale d’un sinistre retenu, en euros.',
 'nb_top_1pct':'Nombre de dossiers composant le premier centile le plus coûteux, arrondi supérieur.',
 'part_charge_top_1pct':'Part de la charge portée par ces dossiers ; ratio brut.',
 'charge_totale':'Charge totale des sinistres retenus, en euros.',
 'cout_moyen_sans_max':'Coût moyen après retrait du seul dossier maximum, sensibilité non officielle.',
 'ratio_sp_sans_max':'S/P après retrait du dossier maximum de la charge, primes inchangées ; sensibilité.',
 'annee_precedente':'Année civile servant de référence de comparaison.',
 'sp_precedent':'S/P technique de l’année précédente, ratio brut.',
 'sp_courant':'S/P technique de l’année courante, ratio brut.',
 'variation_sp':'S/P courant moins S/P précédent, ratio brut ; multiplier par 100 pour des points de pourcentage.',
 'effet_frequence':'Contribution Shapley de la fréquence à la variation du S/P, ratio brut.',
 'effet_cout_moyen':'Contribution Shapley du coût moyen à la variation du S/P, ratio brut.',
 'effet_prime_moyenne':'Contribution Shapley de la prime moyenne à la variation du S/P, ratio brut.',
 'effet_volume_sur_ratio':'Zéro par identité algébrique ; l’exposition se simplifie dans le ratio.',
 'exposition_precedente':'Exposition de l’année précédente, en années-polices.',
 'exposition_courante':'Exposition de l’année courante, en années-polices.',
 'charge_precedente':'Charge retenue de l’année précédente, en euros.',
 'charge_courante':'Charge retenue de l’année courante, en euros.',
 'primes_precedentes':'Primes acquises de l’année précédente, en euros.',
 'primes_courantes':'Primes acquises de l’année courante, en euros.',
 'contribution_sp':'Charge du segment / primes globales de l’année, ratio brut.',
 'precedent':'Contribution du même segment à l’année précédente, ratio brut.',
 'variation_contribution_sp':'Variation de la contribution comptable du segment au S/P ; ratio brut.'
}


TABLES.update({
 'marts.mart_valeur_client':'Une ligne par client maître : primes acquises moins sinistres payés sur la période observée, hors frais et réserves.',
 'marts.mart_retention_individuelle':'Une ligne par client, produit et ancienneté : présence au même produit à l’anniversaire ; observabilité de la cohorte entière.',
 'marts.mart_retention':'Proportion de clients retenus par cohorte, produit, ancienneté et groupe fixé à l’entrée ; IC Wilson ajoutés par le script 05.',
 'marts.mart_pareto_valeur':'Classement et concentration des seules valeurs client strictement positives ; pertes exclues et analysées séparément.',
 'marts.mart_delais':'Une ligne par sinistre : délais observés, statut et audit ; dernier paiement des clôturés comme approximation explicitement distincte.',
 'marts.mart_delais_garantie':'Quantiles des délais disponibles et effectifs par garantie.',
 'marts.mart_audits':'Taux de confirmation et montants des seuls dossiers audités valides, par garantie, tranche de charge et délai ; IC Wilson ajoutés par le script 05.'
})
DEFS.update({
 'valeur_observee':'Primes acquises cumulées moins sinistres payés cumulés ; euros, sans frais ni réserves.',
 'sinistres_payes':'Paiements cumulés sur les sinistres valides du client, tous statuts, euros.',
 'nb_sinistres_tous_statuts':'Nombre de sinistres valides du client, tous statuts confondus.',
 'nb_contrats':'Nombre de contrats valides du client sur l’ensemble de la période.',
 'nb_contrats_actifs':'Nombre de contrats du client actifs au 30/06/2025, résiliation exclue.',
 'auto_actif':'Au moins un contrat AUTO actif au 30/06/2025.',
 'habitation_active':'Au moins un contrat HABITATION actif au 30/06/2025.',
 'multi_detenteur_actuel':'Au moins un contrat de chaque produit actif au 30/06/2025.',
 'date_entree':'Date de première souscription valide du client au produit.',
 'cohorte':'Année de première souscription valide du client au produit.',
 'anciennete':'Nombre entier d’années écoulées depuis la première souscription au produit.',
 'date_anniversaire':'Date d’entrée décalée du nombre d’années d’ancienneté.',
 'detention_entree':'Mono/Multi mesuré à la première souscription au produit ; Tous agrège les groupes.',
 'observable':'Tous les anniversaires de la cohorte-produit-ancienneté sont au plus tard le 30/06/2025.',
 'retenu_anniversaire':'Au moins un contrat du même produit actif à l’anniversaire ; null si cohorte non entièrement observable.',
 'nb_clients_cohorte':'Nombre de clients distincts de la cohorte, du produit et du groupe fixé à l’entrée.',
 'nb_retenus':'Clients présents au même produit à l’anniversaire ; null si période inobservable.',
 'taux_retention':'Clients retenus / clients de cohorte ; proportion brute, null pour une case non observable.',
 'rang':'Rang décroissant de valeur parmi les clients à valeur positive, départagé par identifiant.',
 'part_clients_positifs':'Rang / nombre de clients à valeur strictement positive.',
 'part_valeur_positive_cumulee':'Somme des valeurs positives jusqu’au rang / total des valeurs positives.',
 'date_premier_paiement':'Date minimale des paiements du sinistre ; null sans paiement.',
 'date_dernier_paiement':'Date maximale des paiements enregistrés ; ce n’est pas une date de clôture.',
 'delai_declaration_jours':'Déclaration moins survenance en jours.',
 'delai_premier_reglement_jours':'Premier paiement moins déclaration en jours ; null si absent ou négatif.',
 'delai_dernier_reglement_clotures_jours':'Dernier paiement moins déclaration, uniquement pour les dossiers CLOTURE ; approximation distincte du délai réel de clôture.',
 'paiement_avant_declaration':'Premier paiement antérieur à la déclaration ; anomalie signalée.',
 'audite':'Dossier ayant un audit valide dans le cœur.',
 'tranche_charge':'Charge observée à l’extraction : <1000, 1000-4999, 5000-19999 ou >=20000 euros.',
 'tranche_delai_declaration':'Déclaration dans les 0-7 jours, 8-30 jours ou au-delà de 30 jours.',
 'nb_dossiers':'Nombre de sinistres valides de la garantie.',
 'nb_ouverts':'Nombre de sinistres encore au statut OUVERT.',
 'nb_delais_declaration':'Nombre de délais de déclaration renseignés.',
 'nb_delais_premier_reglement':'Nombre de premiers paiements observés et non antérieurs à la déclaration.',
 'nb_delais_dernier_reglement_clotures':'Nombre de dossiers CLOTURE avec dernier paiement observé après déclaration.',
 'nb_paiements_avant_declaration':'Nombre de sinistres dont le premier paiement précède la déclaration.',
 'nb_audits':'Nombre de dossiers audités valides dans le groupe.',
 'nb_fraudes_confirmees':'Nombre de confirmations de fraude parmi les dossiers audités du groupe.',
 'taux_confirmation':'Fraudes confirmées / audits valides du groupe ; ne s’applique pas aux non-audités.',
 'charge_auditee':'Somme des charges observées des dossiers audités, euros.',
 'charge_dossiers_confirmes':'Charge des dossiers audités à fraude confirmée, euros ; pas une économie prouvée.',
 'paye_dossiers_confirmes':'Paiements des dossiers audités à fraude confirmée, euros ; pas un montant récupéré.'
})
for prefix,label in [('declaration','Déclaration moins survenance'),('premier_reglement','Premier paiement moins déclaration'),('dernier_reglement_clotures','Dernier paiement moins déclaration des seuls dossiers CLOTURE (approximation)')]:
    for suffix,quantile in [('mediane','Médiane'),('p75','Quantile 75 %'),('p90','Quantile 90 %')]:
        DEFS[prefix+'_'+suffix]=quantile+' du délai : '+label+', jours ; calcul sur les valeurs observées non nulles.'



TABLES.update({
 'marts.mart_contrat_mois':'Une ligne par contrat valide et mois avec couverture, sinistre, paiement ou résiliation ; détail filtrable commun au dashboard.',
 'marts.mart_portefeuille_mensuel':'Mois × produit × région × canal × zone × formule × âge ; totaux mensuels et stock de contrats actifs en fin de mois.',
 'marts.mart_cohortes_dashboard':'Détail de rétention enrichi du profil régional de juin 2025 et du canal de première souscription au produit, pour filtres dashboard.'
})
DEFS.update({
 'mois':'Premier jour du mois civil observé ; observation bornée à janvier 2020-juin 2025 dans les marts dashboard.',
 'contrats_actifs':'Stock de contrats actifs au dernier jour du mois : date d’effet incluse et résiliation exclue ; ne pas sommer entre mois.',
 'paiements_flux':'Paiements effectivement datés du mois, tous statuts ; distincts des paiements des sinistres survenus dans le mois.',
})


def run(database,catalogue):
    catalogue=Path(catalogue)
    cat=yaml.safe_load(catalogue.read_text(encoding='utf-8'))
    tables=cat.setdefault('tables',{});common=cat.get('communes',{})
    with duckdb.connect(str(database),read_only=True) as db:
        for name,description in TABLES.items():
            schema,table=name.split('.')
            columns=db.execute('SELECT column_name FROM information_schema.columns WHERE table_schema=? AND table_name=? ORDER BY ordinal_position',[schema,table]).fetchall()
            if not columns: continue
            entry=tables.setdefault(name,{})
            entry['description']=description
            defs=entry.setdefault('colonnes',{})
            for (column,) in columns:
                if column in DEFS: defs[column]=DEFS[column]
                elif column in common or column in defs: continue
                else: raise ValueError(f'Définition manquante : {name}.{column}')
    catalogue.write_text(yaml.safe_dump(cat,allow_unicode=True,sort_keys=False,width=110),encoding='utf-8')
    print('Catalogue B complété sans suppression des autres tables.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',default='boreal.duckdb')
    p.add_argument('--catalogue',default='docs/catalogue.yaml')
    a=p.parse_args()
    run(a.database,a.catalogue)
