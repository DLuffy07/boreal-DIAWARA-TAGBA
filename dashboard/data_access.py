"""Requêtes du dashboard : lecture seule et schéma marts uniquement."""
import itertools
import duckdb
import numpy as np
import pandas as pd

MEASURES=['exposition_annees','primes_acquises','nb_sinistres_retenus','charge_retenue',
          'montant_paye_retenu','reserve_restante_retenue','nb_resiliations','paiements_flux','nb_sans_suite','nb_rejetes']
ALLOWED_AXES={'produit','region','canal_distribution','zone_risque','formule','tranche_age','annee','mois'}


def query(path,sql,params=()):
    with duckdb.connect(str(path),read_only=True) as db:
        return db.execute(sql,list(params)).df()


def where(filters,date_column='mois',include_period=True):
    # Le nom de date est une constante de l'application, jamais une saisie utilisateur.
    if date_column not in {'mois',"date_trunc('month',date_survenance)","date_trunc('month',date_entree)"}:
        raise ValueError('Date non autorisée')
    clauses=[];params=[]
    if include_period:
        clauses.append(f'{date_column} BETWEEN ? AND ?');params.extend([filters['debut'],filters['fin']])
    for column,key in [('produit','produits'),('region','regions'),('canal_distribution','canaux')]:
        values=filters[key]
        if not values: clauses.append('FALSE')
        else:
            clauses.append(column+' IN ('+','.join(['?']*len(values))+')');params.extend(values)
    return ' AND '.join(clauses) or 'TRUE',params


def aggregate_sql(axis,condition):
    if axis not in ALLOWED_AXES:raise ValueError('Axe non autorisé')
    expr="year(mois)" if axis=='annee' else axis
    return 'SELECT '+expr+' AS '+axis+','+','.join('sum('+c+') AS '+c for c in MEASURES)+' FROM marts.mart_portefeuille_mensuel WHERE '+condition+' GROUP BY 1 ORDER BY 1'


def ratios(frame):
    f=frame.copy()
    for name,num,den in [('frequence','nb_sinistres_retenus','exposition_annees'),
        ('cout_moyen','charge_retenue','nb_sinistres_retenus'),
        ('prime_moyenne','primes_acquises','exposition_annees'),
        ('ratio_sp','charge_retenue','primes_acquises'),('taux_resiliation','nb_resiliations','exposition_annees')]:
        f[name]=f[num]/f[den].replace(0,np.nan)
    return f


def compare_previous_year(current,history):
    """Aligne chaque mois sélectionné avec son mois N-1 ; aucune somme de stocks."""
    cur=ratios(current);prev=ratios(history)
    prev=prev[['mois','primes_acquises','ratio_sp']].copy()
    prev['mois']=pd.to_datetime(prev.mois)+pd.DateOffset(years=1)
    prev=prev.rename(columns={'primes_acquises':'primes_n_1','ratio_sp':'sp_n_1'})
    cur['mois']=pd.to_datetime(cur.mois)
    return cur.merge(prev,on='mois',how='left',validate='one_to_one')


def shapley(before,after):
    before=np.asarray(before,dtype=float);after=np.asarray(after,dtype=float)
    if not np.isfinite(before).all() or not np.isfinite(after).all() or before[2]<=0 or after[2]<=0:
        return np.full(3,np.nan)
    result=np.zeros(3)
    for order in itertools.permutations(range(3)):
        x=before.copy()
        for i in order:
            old=x[0]*x[1]/x[2]
            x[i]=after[i]
            result[i]+=(x[0]*x[1]/x[2]-old)/6
    return result
