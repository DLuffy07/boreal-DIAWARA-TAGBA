"""Exporter L3.1 exclusivement depuis marts.mart_segments."""
import argparse
from pathlib import Path
import duckdb

MEASURES='''sum(exposition_annees) AS exposition_annees,
sum(primes_acquises) AS primes_acquises,
sum(nb_sinistres_retenus) AS nb_sinistres_retenus,
sum(charge_retenue) AS charge_retenue,
sum(nb_resiliations) AS nb_resiliations,
sum(montant_paye_retenu) AS montant_paye_retenu,
sum(reserve_restante_retenue) AS reserve_restante_retenue,
sum(nb_sinistres_retenus)/nullif(sum(exposition_annees),0) AS frequence,
sum(charge_retenue)/nullif(sum(nb_sinistres_retenus),0) AS cout_moyen,
sum(primes_acquises)/nullif(sum(exposition_annees),0) AS prime_moyenne,
sum(charge_retenue)/nullif(sum(primes_acquises),0) AS ratio_sp,
sum(nb_resiliations)/nullif(sum(exposition_annees),0) AS taux_resiliation'''

def run(database,output):
    if not Path(database).is_file(): raise FileNotFoundError(database)
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    with duckdb.connect(str(database),read_only=True) as db:
        global_values=db.execute('SELECT '+MEASURES+' FROM marts.mart_segments').df()
        global_values.to_csv(output/'indicateurs_globaux.csv',index=False)
        for name,cols in {'annee':['annee'],'produit':['produit'],'zone':['zone_risque'],
            'formule':['produit','formule'],'canal':['canal_distribution'],
            'age':['tranche_age'],'annee_produit':['annee','produit']}.items():
            prefix=','.join(cols)
            df=db.execute('SELECT '+prefix+','+MEASURES+' FROM marts.mart_segments GROUP BY '+prefix+' ORDER BY '+prefix).df()
            df.to_csv(output/f'indicateurs_{name}.csv',index=False)
        row=global_values.iloc[0]
        report=f'''# Premiers résultats L3.1 — Boréal

Source unique : marts.mart_segments, construit depuis le cœur nettoyé.
Période : janvier 2020 à juin 2025. Charge évaluée à l'extraction, selon la réserve conventionnelle du contrat.

- Exposition : {row.exposition_annees:,.2f} années-polices.
- Primes acquises : {row.primes_acquises:,.2f} euros.
- Sinistres retenus : {int(row.nb_sinistres_retenus)}.
- Charge retenue : {row.charge_retenue:,.2f} euros.
- Ratio S/P technique : {100*row.ratio_sp:.2f} %.
- Fréquence : {100*row.frequence:.2f} sinistres pour 100 années-polices.
- Coût moyen : {row.cout_moyen:,.2f} euros.
- Résiliations observées dans les contrats valides : {int(row.nb_resiliations)}.

## Lecture et limites

Ces résultats sont descriptifs, sans frais de gestion ni résultat financier : le S/P ne mesure pas à lui seul la rentabilité nette. Les réserves sont une approximation imposée par le contrat à partir de la réserve initiale, pas une estimation actuarielle des provisions. 2025 couvre six mois ; les années récentes sont encore susceptibles de règlements futurs. Les caractéristiques client sont observées en juin 2025. Les intervalles de confiance et les comparaisons statistiques ne sont pas encore livrés dans cette étape.

## Traçabilité

La déduplication a été exécutée sur raw.clients avec quality/dedup_clients.py ; le cœur a été reconstruit avec le SQL de A. Le mart et les exports utilisent ensuite les mêmes données. La déduplication conserve 15 002 clients maîtres et laisse quatre clients à examiner. Les indicateurs ne sont pas calculés à partir des fichiers sources.

Les résiliations sont comptées à la date réelle depuis core.dim_contrat : le drapeau de fait_exposition omet les résiliations au début d'une année sans exposition cette année-là. Le contrôle réconcilie désormais le nombre du mart avec les contrats valides résiliés.
'''
        (output/'premiers_resultats.md').write_text(report,encoding='utf-8')
        print(report)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',default='boreal.duckdb')
    p.add_argument('--output',default='outputs')
    a=p.parse_args()
    run(a.database,a.output)
