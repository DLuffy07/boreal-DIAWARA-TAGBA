"""L4 : construit les marts, les valide puis exporte les résultats reproductibles."""
import argparse
import math
from pathlib import Path
import duckdb
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def wilson(success,total,z=1.959963984540054):
    success=np.asarray(success,dtype=float);total=np.asarray(total,dtype=float)
    with np.errstate(divide='ignore',invalid='ignore'):
        p=success/total
        center=(p+z*z/(2*total))/(1+z*z/total)
        half=z*np.sqrt(p*(1-p)/total+z*z/(4*total*total))/(1+z*z/total)
    return np.where(total>0,np.maximum(0,center-half),np.nan),np.where(total>0,np.minimum(1,center+half),np.nan)


def validate(db):
    checks=[
      ('''SELECT count(*) FROM (SELECT client_id_maitre FROM marts.mart_valeur_client GROUP BY 1 HAVING count(*)>1)''','Valeur client non unique'),
      ('''SELECT count(*) FROM marts.mart_retention WHERE (NOT observable AND taux_retention IS NOT NULL) OR nb_retenus>nb_clients_cohorte OR taux_retention<0 OR taux_retention>1''','Rétention invalide ou non observable remplie'),
      ('''SELECT count(*) FROM marts.mart_delais WHERE delai_declaration_jours<0 OR delai_premier_reglement_jours<0 OR delai_dernier_reglement_clotures_jours<0''','Délais négatifs'),
      ('''SELECT count(*) FROM (SELECT sinistre_id FROM marts.mart_delais GROUP BY 1 HAVING count(*)>1)''','Sinistres dupliqués'),
      ('''SELECT abs((SELECT count(*) FROM marts.mart_delais)-(SELECT count(*) FROM core.fait_sinistre))''','Délais : dossiers perdus'),
      ('''SELECT abs((SELECT count(*) FROM marts.mart_valeur_client)-(SELECT count(*) FROM core.v_client_analyse))''','Valeur : clients perdus'),
      ('''SELECT count(*) FROM marts.mart_audits WHERE nb_fraudes_confirmees>nb_audits OR taux_confirmation NOT BETWEEN 0 AND 1''','Audits incohérents')]
    for query,label in checks:
        if db.execute(query).fetchone()[0]: raise ValueError(label)
    for query,label in [
      ('''SELECT (SELECT coalesce(sum(primes_acquises),0) FROM marts.mart_valeur_client)-(SELECT coalesce(sum(prime_acquise),0) FROM core.fait_exposition)''','Primes valeur client'),
      ('''SELECT (SELECT coalesce(sum(sinistres_payes),0) FROM marts.mart_valeur_client)-(SELECT coalesce(sum(montant_paye),0) FROM core.fait_sinistre)''','Paiements valeur client')]:
        if abs(db.execute(query).fetchone()[0])>.01: raise ValueError(label)


def run(database,output):
    if not Path(database).is_file(): raise FileNotFoundError(database)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with duckdb.connect(str(database)) as db:
        db.execute('BEGIN TRANSACTION')
        try:
            db.execute((ROOT/'sql/marts/20_clients_sinistres.sql').read_text(encoding='utf-8'))
            validate(db)
            # Wilson s'applique ici aux proportions de clients retenus et d'audits confirmés.
            for table,success,total in [('mart_retention','nb_retenus','nb_clients_cohorte'),('mart_audits','nb_fraudes_confirmees','nb_audits')]:
                df=db.sql('SELECT * FROM marts.'+table).df()
                df['ic_bas'],df['ic_haut']=wilson(df[success].to_numpy(dtype=float,na_value=np.nan),df[total].to_numpy(dtype=float,na_value=np.nan))
                db.register('enriched',df)
                db.execute('CREATE OR REPLACE TABLE marts.'+table+' AS SELECT * FROM enriched')
            db.execute('COMMIT')
        except Exception:
            db.execute('ROLLBACK');raise
        tables=['mart_retention','mart_valeur_client','mart_pareto_valeur','mart_delais','mart_delais_garantie','mart_audits']
        for table in tables:
            db.sql('SELECT * FROM marts.'+table).df().to_csv(output/(table+'.csv'),index=False)
        nclient,nactive,nmulti,pos,neg,net=db.execute('''SELECT count(*),count(*) FILTER(WHERE nb_contrats_actifs>0),
            count(*) FILTER(WHERE multi_detenteur_actuel),
            sum(greatest(valeur_observee,0)),sum(least(valeur_observee,0)),sum(valeur_observee)
            FROM marts.mart_valeur_client''').fetchone()
        audits=db.sql("SELECT * FROM marts.mart_audits WHERE axe='global'").df().iloc[0]
        top=db.sql('''SELECT client_id_maitre,region,tranche_age,csp,nb_contrats,valeur_observee
            FROM marts.mart_valeur_client ORDER BY valeur_observee DESC,client_id_maitre LIMIT 20''').df()
        bottom=db.sql('''SELECT client_id_maitre,region,tranche_age,csp,nb_contrats,valeur_observee
            FROM marts.mart_valeur_client ORDER BY valeur_observee,client_id_maitre LIMIT 20''').df()
        top.to_csv(output/'profils_top20.csv',index=False);bottom.to_csv(output/'profils_bottom20.csv',index=False)
        # Comparer la rétention à 1 an à cohorte/produit fixés, pas seulement un agrégat biaisé.
        comparison=db.sql("""SELECT * FROM marts.mart_retention WHERE anciennete=1 AND observable AND detention_entree<>'Tous' ORDER BY cohorte,produit,detention_entree""").df()
        comparison.to_csv(output/'retention_comparaison_1an.csv',index=False)
        missing=db.execute("SELECT count(*) FILTER(WHERE date_premier_paiement IS NULL),count(*) FILTER(WHERE paiement_avant_declaration) FROM marts.mart_delais").fetchone()
        pareto20=db.execute('''SELECT coalesce(sum(valeur_observee),0) FROM marts.mart_pareto_valeur
             WHERE rang<=ceil((SELECT count(*) FROM marts.mart_pareto_valeur)*.2)''').fetchone()[0]/pos
        text=f'''# L4 — Clients et gestion des sinistres

## Multi-détention au 30/06/2025

{nactive} clients ont au moins un contrat actif. Parmi eux, {nmulti} ont simultanément auto et habitation, soit {100*nmulti/nactive:.2f} %. Dénominateur : clients actifs, pas tous les {nclient} clients maîtres.

## Rétention

Une cohorte est l'année de première souscription valide d'un client à un produit. La rétention est la présence d'au moins un contrat du même produit à chaque anniversaire de cette première souscription. C'est une présence à une date, pas une survie sans interruption : une réactivation peut compter comme retenue.
Une case n'est remplie que si TOUS les anniversaires de la cohorte-produit sont observables au 30/06/2025. Les autres cases restent null. Mono/multi est mesuré à l'entrée du client dans ce produit : ne pas utiliser le statut de juin 2025 pour expliquer rétrospectivement la rétention. La comparaison à 1 an est exportée par cohorte et produit pour limiter le biais de composition. Les clients initialement mono peuvent devenir multi plus tard ; il s'agit de groupes fixés au départ, sans interprétation causale.

## Valeur observée

Primes acquises moins paiements sur la période : {net:,.2f} euros au total, dont {pos:,.2f} euros de valeurs positives et {neg:,.2f} euros de valeurs négatives. La valeur n'intègre ni frais ni réserves ; elle ne prédit pas la valeur future et dépend de la durée d'observation de chaque client.
Les 20 % de clients à valeur positive les plus contributeurs représentent {100*pareto20:.2f} % du total des valeurs positives. Le Pareto est explicitement calculé sur les seules valeurs positives ; les pertes sont présentées séparément, sans normaliser une courbe sur un total signé. Les profils extrêmes sont exportés dans profils_top20.csv et profils_bottom20.csv ; le profil est celui observé en juin 2025.

## Délais

Déclaration : déclaration moins survenance. Premier règlement : premier paiement moins déclaration, parmi les dossiers déjà réglés. Aucun paiement : délai inconnu, jamais zéro. {missing[0]} sinistres n’ont aucun paiement enregistré ; {missing[1]} présentent un paiement antérieur à la déclaration et sont signalés séparément (délai négatif non utilisé).
**Aucune date de clôture n'est disponible.** Le délai au dernier règlement des seuls dossiers CLOTURE est fourni comme approximation séparée, jamais nommé date réelle de clôture. Les dossiers ouverts, non réglés ou sans dernier paiement ne font pas partie de cette approximation. Les quantiles portent sur les délais observés ; ils peuvent sous-estimer les délais futurs des dossiers encore ouverts. Les effectifs disponibles accompagnent chaque garantie.

## Audits

{int(audits.nb_fraudes_confirmees)} fraudes confirmées parmi {int(audits.nb_audits)} dossiers audités valides : {100*audits.taux_confirmation:.2f} %, IC Wilson à 95 % [{100*audits.ic_bas:.2f} % ; {100*audits.ic_haut:.2f} %]. Ce taux s'applique UNIQUEMENT aux dossiers audités et conservés après qualité ; ce n'est pas une prévalence dans tout le portefeuille.
Les montants des dossiers confirmés ou audités indiquent les enjeux financiers, pas les économies réalisées grâce aux audits. Sans coût d'audit ni montant effectivement évité/récupéré, aucun retour sur investissement causal ne peut être calculé. Les résultats selon garantie, tranche de charge et délai de déclaration sont dans mart_audits.csv. Les critères et montants observés à l'extraction peuvent différer des informations disponibles à la date de décision d'audit.

## Traçabilité

Tous les résultats proviennent des marts créés depuis core. La déduplication est déjà intégrée en amont. Les exclusions qualité expliquent la différence avec les effectifs bruts du sujet (372 audits et 37 fraudes annoncés avant contrôle). Le script réconcilie primes, paiements, nombre de clients et dossiers et vérifie les périodes observables.
'''
        (output/'analyse_clients_sinistres.md').write_text(text,encoding='utf-8')
        print(text)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',default='boreal.duckdb')
    p.add_argument('--output',default='outputs')
    a=p.parse_args();run(a.database,a.output)
