from datetime import date
import importlib.util
from pathlib import Path
import unittest
import duckdb
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('data_b',ROOT/'dashboard/data_access.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MonthlyTests(unittest.TestCase):
    def setUp(self):
        self.db=duckdb.connect(':memory:')
        self.db.execute('''CREATE SCHEMA core;CREATE SCHEMA marts;
        CREATE TABLE core.dim_contrat AS SELECT 1 contrat_id,1 client_id_maitre,'AUTO' produit,
           'CONFORT' formule,'WEB' canal_distribution,1 zone_risque,'S1' segment_id,
           DATE '2024-01-01' date_effet,DATE '2025-01-01' date_resiliation,1000.0 prime_annuelle;
        CREATE TABLE core.v_client_analyse AS SELECT 1 client_id_maitre,'IDF' region,'25-34' tranche_age;
        CREATE TABLE core.fait_sinistre(sinistre_id INTEGER,contrat_id INTEGER,date_survenance DATE,statut VARCHAR,retenu BOOLEAN,charge DOUBLE,montant_paye DOUBLE,reserve_restante DOUBLE);
        CREATE TABLE core.fait_reglement(sinistre_id INTEGER,date_paiement DATE,montant DOUBLE);
        CREATE TABLE marts.mart_retention_individuelle(client_id_maitre INTEGER,produit VARCHAR,date_entree DATE,cohorte INTEGER,detention_entree VARCHAR,anciennete INTEGER,date_anniversaire DATE,observable BOOLEAN,retenu_anniversaire BOOLEAN);''')
        self.db.execute((ROOT/'sql/marts/30_dashboard.sql').read_text())
    def tearDown(self):self.db.close()
    def test_leap_year_full_coverage(self):
        expo,prime=self.db.execute('SELECT sum(exposition_annees),sum(primes_acquises) FROM marts.mart_contrat_mois').fetchone()
        self.assertAlmostEqual(expo,366/365.25)
        self.assertAlmostEqual(prime,1000*366/365.25)
    def test_resiliation_kept_in_january_without_exposure(self):
        row=self.db.execute("SELECT exposition_annees,nb_resiliations,contrats_actifs FROM marts.mart_contrat_mois WHERE mois=DATE '2025-01-01'").fetchone()
        self.assertEqual(row,(0.0,1,0))
    def test_december_stock_not_sum_of_months(self):
        stock=self.db.execute("SELECT contrats_actifs FROM marts.mart_contrat_mois WHERE mois=DATE '2024-12-01'").fetchone()[0]
        self.assertEqual(stock,1)
    def test_ratio_recomputed_from_sums(self):
        df=pd.DataFrame({'nb_sinistres_retenus':[1,9],'exposition_annees':[1,99],
           'charge_retenue':[100,900],'primes_acquises':[100,9900],'nb_resiliations':[0,1]})
        combined=m.ratios(pd.DataFrame([df.sum()])).iloc[0]
        self.assertAlmostEqual(combined.frequence,.1)
        self.assertAlmostEqual(combined.ratio_sp,.1)
    def test_filter_values_are_parameterized(self):
        f={'debut':date(2024,1,1),'fin':date(2024,12,1),'produits':['AUTO'],
           'regions':["IDF' OR 1=1 --"],'canaux':['WEB']}
        sql,params=m.where(f)
        self.assertNotIn('OR 1=1',sql)
        self.assertIn("IDF' OR 1=1 --",params)
    def test_previous_year_month_alignment(self):
        def frame(year):
            return pd.DataFrame({'mois':[pd.Timestamp(year,1,1)],**{k:[10.0] for k in m.MEASURES}})
        compared=m.compare_previous_year(frame(2025),frame(2024))
        self.assertEqual(compared.primes_n_1.iloc[0],10)

if __name__=='__main__':unittest.main()
