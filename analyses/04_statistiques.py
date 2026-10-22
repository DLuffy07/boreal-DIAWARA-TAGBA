"""L3.2/L3.3 : crée deux marts de détail depuis core, puis calcule IC et comparaisons depuis les marts."""
import argparse
import itertools
import json
import math
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from scipy.stats import binomtest, chi2, mannwhitneyu


def poisson_interval(count, exposure, alpha=0.05):
    if exposure<=0: return (float('nan'),float('nan'))
    low=0.0 if count==0 else chi2.ppf(alpha/2,2*count)/2/exposure
    high=chi2.ppf(1-alpha/2,2*(count+1))/2/exposure
    return float(low),float(high)


def safe_ratio(a,b): return a/b if b else float('nan')


def shapley(old,new):
    """Décomposition exacte et symétrique du ratio f*c/p en trois effets."""
    old=np.array(old,dtype=float)
    new=np.array(new,dtype=float)
    if not (np.isfinite(old).all() and np.isfinite(new).all() and old[2]>0 and new[2]>0):
        return np.full(3,np.nan)
    effects=np.zeros(3)
    value=lambda x:x[0]*x[1]/x[2]
    for order in itertools.permutations(range(3)):
        x=old.copy()
        for i in order:
            before=value(x)
            x[i]=new[i]
            effects[i]+=(value(x)-before)/6
    return effects


def ci_group(frame,axis,label,rng,iterations):
    # Bloc de bootstrap = client, tous ses contrats du groupe sont resamplés ensemble.
    a=frame.groupby('client_id_maitre',sort=True)[['exposition_annees','primes_acquises','nb_sinistres_retenus','charge_retenue','nb_resiliations']].sum().to_numpy(dtype=float)
    e,p,n,c,r=a.sum(axis=0)
    obs={'frequence':safe_ratio(n,e),'cout_moyen':safe_ratio(c,n),
         'prime_moyenne':safe_ratio(p,e),'ratio_sp':safe_ratio(c,p),'taux_resiliation':safe_ratio(r,e)}
    boots={'cout_moyen':[],'prime_moyenne':[],'ratio_sp':[]}
    for start in range(0,iterations,32):
        idx=rng.integers(0,len(a),size=(min(32,iterations-start),len(a)))
        totals=a[idx].sum(axis=1)
        for name,num,den in [('cout_moyen',3,2),('prime_moyenne',1,0),('ratio_sp',3,1)]:
            values=np.divide(totals[:,num],totals[:,den],out=np.full(len(totals),np.nan),where=totals[:,den]!=0)
            boots[name].extend(values)
    rows=[]
    for name,estimate in obs.items():
        if name in boots:
            values=np.asarray(boots[name]);values=values[np.isfinite(values)]
            lo,hi=np.quantile(values,[0.025,0.975]) if len(values) else [np.nan,np.nan]
            method='Bootstrap percentile par client'
            repetitions=iterations
        else:
            lo,hi=poisson_interval(int(n if name=='frequence' else r),e)
            method='Poisson exact (hypothèse de comptage Poisson)'
            repetitions=0
        rows.append({'axe':axis,'groupe':str(label),'indicateur':name,'estimation':estimate,
                     'ic_bas':lo,'ic_haut':hi,'niveau_confiance':0.95,
                     'methode':method,'nb_clients_blocs':len(a),'repetitions':repetitions})
    return rows


def run(database,output,iterations=2000,seed=20261021):
    if not Path(database).is_file(): raise FileNotFoundError(database)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with duckdb.connect(str(database)) as db:
        # Marts de détail communs à l'analyse statistique et au futur dashboard.
        db.execute('''CREATE OR REPLACE TABLE marts.mart_contrats_analyse AS
            WITH e AS (SELECT contrat_id,sum(exposition_annees) exposition_annees,
                       sum(prime_acquise) primes_acquises FROM core.fait_exposition GROUP BY 1),
            s AS (SELECT contrat_id,count(*) FILTER(WHERE retenu) nb_sinistres_retenus,
                       sum(charge) FILTER(WHERE retenu) charge_retenue FROM core.fait_sinistre GROUP BY 1)
            SELECT c.contrat_id,c.client_id_maitre,c.produit,c.formule,c.zone_risque,
                   c.canal_distribution,cl.region,cl.tranche_age,
                   coalesce(e.exposition_annees,0) exposition_annees,
                   coalesce(e.primes_acquises,0) primes_acquises,
                   coalesce(s.nb_sinistres_retenus,0)::BIGINT nb_sinistres_retenus,
                   coalesce(s.charge_retenue,0) charge_retenue,
                   CASE WHEN c.date_resiliation BETWEEN DATE '2020-01-01' AND DATE '2025-06-30' THEN 1 ELSE 0 END::BIGINT nb_resiliations
            FROM core.dim_contrat c JOIN core.v_client_analyse cl USING(client_id_maitre)
            LEFT JOIN e USING(contrat_id) LEFT JOIN s USING(contrat_id)''')
        db.execute('''CREATE OR REPLACE TABLE marts.mart_sinistres_analyse AS
            SELECT s.sinistre_id,s.contrat_id,c.client_id_maitre,c.produit,c.formule,
                   c.zone_risque,c.canal_distribution,cl.region,cl.tranche_age,
                   s.garantie,s.date_survenance,s.statut,s.retenu,
                   s.montant_paye,s.reserve_restante,s.charge
            FROM core.fait_sinistre s JOIN core.dim_contrat c USING(contrat_id)
            JOIN core.v_client_analyse cl USING(client_id_maitre)''')
        contracts=db.sql('SELECT * FROM marts.mart_contrats_analyse ORDER BY contrat_id').df()
        claims=db.sql('SELECT * FROM marts.mart_sinistres_analyse WHERE retenu ORDER BY sinistre_id').df()
        # Garantir le même périmètre avant les traitements statistiques.
        for own,ref in [('exposition_annees','exposition_annees'),('primes_acquises','primes_acquises'),('nb_sinistres_retenus','nb_sinistres_retenus'),('charge_retenue','charge_retenue'),('nb_resiliations','nb_resiliations')]:
            expected=db.execute(f'SELECT sum({ref}) FROM marts.mart_segments').fetchone()[0]
            if not math.isclose(float(contracts[own].sum()),float(expected),rel_tol=1e-10,abs_tol=0.01):
                raise ValueError(f'Périmètre incohérent avec mart_segments : {own}')
        rng=np.random.default_rng(seed)
        cis=ci_group(contracts,'global','Tous',rng,iterations)
        for axis in ['produit','zone_risque','canal_distribution','tranche_age','formule']:
            for label,group in contracts.groupby(axis,sort=True,dropna=False):
                cis+=ci_group(group,axis,label,rng,iterations)
        ci=pd.DataFrame(cis);ci['graine']=seed
        # Comparaison de deux taux Poisson, exacte par conditionnement sur le nombre total.
        zone=contracts[contracts.zone_risque.isin([1,5])].groupby('zone_risque')[['exposition_annees','nb_sinistres_retenus']].sum()
        e1,e5=float(zone.loc[1,'exposition_annees']),float(zone.loc[5,'exposition_annees'])
        n1,n5=int(zone.loc[1,'nb_sinistres_retenus']),int(zone.loc[5,'nb_sinistres_retenus'])
        test_rate=binomtest(n1,n1+n5,e1/(e1+e5))
        a=claims.loc[claims.canal_distribution=='AGENT','charge'].to_numpy()
        w=claims.loc[claims.canal_distribution=='WEB','charge'].to_numpy()
        mw=mannwhitneyu(a,w,alternative='two-sided',method='asymptotic')
        tests=pd.DataFrame([
            {'comparaison':'Fréquence zone 1 vs zone 5','test':'Poisson conditionnel exact bilatéral',
             'statistique':safe_ratio(n1/e1,n5/e5),'p_value':float(test_rate.pvalue),
             'n_groupe_1':n1,'n_groupe_2':n5,'mesure_1':n1/e1,'mesure_2':n5/e5,
             'interpretation':'Rapport de taux ; hypothèse de comptages Poisson indépendants. Différence descriptive, sans causalité.'},
            {'comparaison':'Charge des sinistres retenus AGENT vs WEB','test':'Mann-Whitney bilatéral asymptotique avec correction des ex aequo',
             'statistique':float(mw.statistic),'p_value':float(mw.pvalue),'n_groupe_1':len(a),'n_groupe_2':len(w),
             'mesure_1':float(np.median(a)),'mesure_2':float(np.median(w)),
             'interpretation':'Mesures affichées = médianes. Le test porte sur les distributions/rangs, pas directement sur la différence des moyennes. Indépendance des sinistres supposée.'}])
        # Correction de Holm des deux comparaisons prévues.
        order=np.argsort(tests.p_value.to_numpy());adjusted=np.zeros(2);running=0
        for rank,idx in enumerate(order):
            running=max(running,min(1.0,(2-rank)*tests.loc[idx,'p_value']))
            adjusted[idx]=running
        tests['p_value_holm']=adjusted
        values=claims.charge.to_numpy();descending=np.sort(values)[::-1]
        k=max(1,math.ceil(len(values)*0.01))
        tail=pd.DataFrame([{'nb_sinistres':len(values),'mediane':float(np.median(values)),
            'p90':float(np.quantile(values,.90)),'p95':float(np.quantile(values,.95)),
            'p99':float(np.quantile(values,.99)),'maximum':float(values.max()),
            'nb_top_1pct':k,'part_charge_top_1pct':float(descending[:k].sum()/values.sum()),
            'charge_totale':float(values.sum()),'cout_moyen':float(values.mean()),
            'cout_moyen_sans_max':float((values.sum()-values.max())/(len(values)-1)),
            'ratio_sp':float(values.sum()/contracts.primes_acquises.sum()),
            'ratio_sp_sans_max':float((values.sum()-values.max())/contracts.primes_acquises.sum())}])
        annual=db.sql('''SELECT annee,sum(exposition_annees) exposition,sum(primes_acquises) primes,
            sum(nb_sinistres_retenus) nb,sum(charge_retenue) charge
            FROM marts.mart_segments GROUP BY 1 ORDER BY 1''').df()
        effects=[]
        for i in range(1,len(annual)):
            old,new=annual.iloc[i-1],annual.iloc[i]
            before=[old.nb/old.exposition,old.charge/old.nb,old.primes/old.exposition]
            after=[new.nb/new.exposition,new.charge/new.nb,new.primes/new.exposition]
            parts=shapley(before,after)
            effects.append({'annee':int(new.annee),'annee_precedente':int(old.annee),
                'sp_precedent':old.charge/old.primes,'sp_courant':new.charge/new.primes,
                'variation_sp':new.charge/new.primes-old.charge/old.primes,
                'effet_frequence':parts[0],'effet_cout_moyen':parts[1],'effet_prime_moyenne':parts[2],
                'effet_volume_sur_ratio':0.0,'exposition_precedente':old.exposition,'exposition_courante':new.exposition,
                'charge_precedente':old.charge,'charge_courante':new.charge,
                'primes_precedentes':old.primes,'primes_courantes':new.primes,
                'annee_partielle':int(new.annee)==2025,
                'methode':'Shapley exact, moyenne des 6 ordres ; volume neutralisé dans le ratio'})
        decomposition=pd.DataFrame(effects)
        if not np.allclose(decomposition[['effet_frequence','effet_cout_moyen','effet_prime_moyenne']].sum(axis=1),decomposition.variation_sp,rtol=1e-10,atol=1e-10):
            raise ValueError('Décomposition non réconciliée')
        contribution=db.sql('''WITH s AS (SELECT annee,segment_id,sum(charge_retenue) charge FROM marts.mart_segments GROUP BY ALL),
            p AS (SELECT annee,sum(primes_acquises) primes FROM marts.mart_segments GROUP BY 1),
            years AS (SELECT DISTINCT annee FROM s),segments AS (SELECT DISTINCT segment_id FROM s),
            grid AS (SELECT y.annee,g.segment_id,coalesce(s.charge,0)/nullif(p.primes,0) contribution_sp
              FROM years y CROSS JOIN segments g JOIN p USING(annee) LEFT JOIN s USING(annee,segment_id)),
            l AS (SELECT *,lag(contribution_sp) OVER(PARTITION BY segment_id ORDER BY annee) precedent FROM grid)
            SELECT annee,segment_id,contribution_sp,precedent,
                   contribution_sp-precedent AS variation_contribution_sp,
                   annee=2025 AS annee_partielle
            FROM l WHERE precedent IS NOT NULL ORDER BY annee,variation_contribution_sp DESC''').df()
        for year,group in contribution.groupby('annee'):
            target=decomposition.loc[decomposition.annee==year,'variation_sp'].iloc[0]
            if not np.isclose(group.variation_contribution_sp.sum(),target,atol=1e-10):
                raise ValueError('Contributions des segments non réconciliées')
        # Publication des résultats du même calcul pour le dossier et le dashboard.
        for name,frame in [('mart_ic',ci),('mart_tests_statistiques',tests),('mart_queue_couts',tail),
                           ('mart_decomposition_sp',decomposition),('mart_contributions_segments',contribution)]:
            db.register('publication_df',frame)
            db.execute(f'CREATE OR REPLACE TABLE marts.{name} AS SELECT * FROM publication_df')
            frame.to_csv(output/f'{name}.csv',index=False)
        t=tail.iloc[0]
        glob=ci[ci.axe=='global'].set_index('indicateur')
        sp=glob.loc['ratio_sp']
        report=f'''# Analyse technique — compléments L3.2/L3.3

## Incertitude

S/P global : {100*sp.estimation:.2f} %, intervalle bootstrap à 95 % [{100*sp.ic_bas:.2f} % ; {100*sp.ic_haut:.2f} %].
Les intervalles des autres indicateurs et groupes sont dans mart_ic.csv.
Bootstrap : {iterations} répétitions, graine {seed}, blocs clients. L'exposition, la prime et la charge d'un client restent regroupées. Fréquence et résiliation : intervalles exacts de Poisson, conditionnels aux expositions observées ; hypothèse d'homogénéité/indépendance à discuter.

Ces IC décrivent l'incertitude d'échantillonnage selon ces modèles, pas les erreurs de données, de provision ou les sinistres futurs. Le portefeuille observé peut être exhaustif : l'inférence concerne une population de risques sous-jacente hypothétique, pas la précision arithmétique du total extrait.

## Queue des coûts

Sur {int(t.nb_sinistres)} sinistres retenus : médiane {t.mediane:.2f} euros, P90 {t.p90:.2f}, P95 {t.p95:.2f}, P99 {t.p99:.2f}. Les {int(t.nb_top_1pct)} dossiers les plus chers (arrondi supérieur de 1 %) portent {100*t.part_charge_top_1pct:.2f} % de la charge. Le maximum est {t.maximum:.2f} euros.
Le S/P passe de {100*t.ratio_sp:.2f} % à {100*t.ratio_sp_sans_max:.2f} % lorsque l'on retire uniquement ce dossier de la charge, en gardant toutes les primes. C'est une sensibilité, pas une correction : le dossier reste dans les résultats officiels.

## Tests de comparaison

Deux comparaisons prédéfinies, seuil 5 %, p-values brutes et ajustées de Holm dans mart_tests_statistiques.csv. Le test de fréquence compare zone 1 à zone 5 conditionnellement au nombre de dossiers ; Mann-Whitney compare les distributions de charge AGENT/WEB, et non les moyennes directement. Les différences ne démontrent pas de causalité ; produit, âge, risque et exposition peuvent expliquer une partie de l'écart. Les sinistres multiples d'un même client peuvent violer l'indépendance supposée par les tests.

## Décomposition

S/P = fréquence × coût moyen / prime moyenne. Les trois effets de Shapley s'additionnent exactement à la variation annuelle. Le volume d'exposition agit sur les montants totaux mais se simplifie dans ce ratio ; ses niveaux et les montants annuels sont fournis séparément. Un changement de composition des risques peut toutefois modifier les trois facteurs et le ratio.
Les contributions des segments sont des variations de charge du segment / primes globales. Elles se somment exactement à la variation globale ; ce sont des contributions comptables, pas des effets causaux indépendants des primes.

**2025 est partielle : ne pas interpréter sa comparaison aux années pleines comme une évolution annuelle homogène.** Les sinistres récents sont moins développés, la réserve est conventionnelle et les profils clients sont observés en juin 2025.
'''
        (output/'analyse_technique_statistiques.md').write_text(report,encoding='utf-8')
        print(report)
        print('Tests :',tests[['comparaison','p_value','p_value_holm']].to_dict('records'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',default='boreal.duckdb')
    p.add_argument('--output',default='outputs')
    p.add_argument('--iterations',type=int,default=2000)
    p.add_argument('--seed',type=int,default=20261021)
    a=p.parse_args()
    if a.iterations<200: p.error('Au moins 200 répétitions ; 2000 recommandées pour le rendu.')
    run(a.database,a.output,a.iterations,a.seed)
