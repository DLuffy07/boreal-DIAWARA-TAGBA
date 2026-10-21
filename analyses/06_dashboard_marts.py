"""Marts mensuels et contrôles bloquants avant dashboard."""
import argparse
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1]

def run(database):
    if not Path(database).is_file():raise FileNotFoundError(database)
    with duckdb.connect(str(database)) as db:
        db.execute('BEGIN TRANSACTION')
        try:
            db.execute((ROOT/'sql/marts/30_dashboard.sql').read_text(encoding='utf-8'))
            delta=db.execute('''WITH m AS (SELECT contrat_id,year(mois) annee,sum(exposition_annees) e,sum(primes_acquises) p
                FROM marts.mart_contrat_mois GROUP BY 1,2),
              a AS (SELECT contrat_id,annee,exposition_annees e,prime_acquise p FROM core.fait_exposition)
              SELECT max(abs(coalesce(m.e,0)-coalesce(a.e,0))),max(abs(coalesce(m.p,0)-coalesce(a.p,0)))
              FROM m FULL JOIN a USING(contrat_id,annee)''').fetchone()
            if (delta[0] or 0)>1e-9 or (delta[1] or 0)>.01:
                raise ValueError(f'Mois et années non réconciliés : {delta}')
            for column,query in [
              ('nb_resiliations',"SELECT count(*) FROM core.dim_contrat WHERE date_resiliation BETWEEN DATE '2020-01-01' AND DATE '2025-06-30'"),
              ('nb_sinistres_retenus','SELECT count(*) FROM core.fait_sinistre WHERE retenu'),
              ('charge_retenue','SELECT sum(charge) FROM core.fait_sinistre WHERE retenu'),
              ('paiements_flux','SELECT sum(montant) FROM core.fait_reglement')]:
                got=float(db.execute('SELECT coalesce(sum('+column+'),0) FROM marts.mart_portefeuille_mensuel').fetchone()[0])
                expected=float(db.execute(query).fetchone()[0] or 0)
                if abs(got-expected)>.01: raise ValueError('Réconciliation échouée : '+column)
            active=db.execute("SELECT sum(contrats_actifs) FROM marts.mart_portefeuille_mensuel WHERE mois=DATE '2025-06-01'").fetchone()[0]
            expected=db.execute("SELECT count(*) FROM core.dim_contrat WHERE date_effet<=DATE '2025-06-30' AND (date_resiliation IS NULL OR date_resiliation>DATE '2025-06-30')").fetchone()[0]
            if active!=expected:raise ValueError('Stock de contrats actifs non réconcilié')
            duplicates=db.execute('''SELECT count(*) FROM (SELECT contrat_id,mois FROM marts.mart_contrat_mois GROUP BY ALL HAVING count(*)>1)''').fetchone()[0]
            if duplicates:raise ValueError('Doublons contrat-mois')
            db.execute('COMMIT')
            print(f'Marts dashboard prêts ; contrats actifs au 30/06/2025 : {active}. Exposition/primes mensuelles réconciliées avec core.')
        except Exception:
            db.execute('ROLLBACK');raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',default='boreal.duckdb')
    a=p.parse_args();run(a.database)
