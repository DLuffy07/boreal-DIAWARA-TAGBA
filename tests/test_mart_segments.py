import importlib.util
from pathlib import Path
import tempfile
import unittest
import duckdb

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mart',ROOT/'analyses/02_mart_segments.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def fixture(path):
    with duckdb.connect(str(path)) as db:
        db.execute('''CREATE SCHEMA core;
        CREATE TABLE core.dim_contrat AS SELECT * FROM (VALUES
          (1,1,'AUTO',1,'CONFORT','AGENT'),(2,2,'AUTO',1,'CONFORT','AGENT'),
          (3,3,'HAB',2,'ECO','WEB')) t(contrat_id,client_id_maitre,produit,zone_risque,formule,canal_distribution);
        ALTER TABLE core.dim_contrat ADD COLUMN date_resiliation DATE;
        UPDATE core.dim_contrat SET date_resiliation=DATE '2024-12-01' WHERE contrat_id=2;
        CREATE TABLE core.dim_segment AS SELECT * FROM (VALUES
          (10,'AUTO',1,'CONFORT','AGENT'),(20,'HAB',2,'ECO','WEB')) t(segment_id,produit,zone_risque,formule,canal_distribution);
        CREATE TABLE core.v_client_analyse AS SELECT * FROM (VALUES (1,'25-34'),(2,'25-34'),(3,'inconnu')) t(client_id_maitre,tranche_age);
        CREATE TABLE core.fait_exposition AS SELECT * FROM (VALUES
          (1,2024,10,1.0,1000.0,false),(2,2024,10,0.5,500.0,true),
          (3,2025,20,0.5,200.0,false)) t(contrat_id,annee,segment_id,exposition_annees,prime_acquise,resilie_dans_annee);
        CREATE TABLE core.fait_sinistre AS SELECT * FROM (VALUES
          (1,1,DATE '2024-02-01','OUVERT',100.0,300.0,400.0),
          (2,1,DATE '2024-03-01','REJETE',50.0,0.0,50.0))
          t(sinistre_id,contrat_id,date_survenance,statut,montant_paye,reserve_restante,charge);''')

class MartTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.db=self.root/'fixture.duckdb'
        fixture(self.db)
    def tearDown(self): self.tmp.cleanup()
    def run_mart(self): mod.build(self.db,self.root/'exports')
    def test_indicators_no_multiplication(self):
        self.run_mart()
        with duckdb.connect(str(self.db)) as db:
            row=db.execute('SELECT exposition_annees,primes_acquises,nb_sinistres_retenus,charge_retenue,ratio_sp,frequence,cout_moyen,prime_moyenne,taux_resiliation,montant_paye_tous_statuts,nb_rejetes FROM marts.mart_segments WHERE segment_id=10').fetchone()
        for actual,expected in zip(row,[1.5,1500,1,400,400/1500,1/1.5,400,1000,1/1.5,150,1]):
            self.assertAlmostEqual(float(actual),expected)
    def test_zero_claims_and_partial_year(self):
        self.run_mart()
        with duckdb.connect(str(self.db)) as db:
            row=db.execute('SELECT frequence,cout_moyen,ratio_sp,annee_partielle FROM marts.mart_segments WHERE segment_id=20').fetchone()
        self.assertEqual(row,(0.0,None,0.0,True))
    def test_duplicate_clients_blocked(self):
        with duckdb.connect(str(self.db)) as db:
            db.execute("INSERT INTO core.v_client_analyse VALUES (1,'25-34')")
        with self.assertRaisesRegex(ValueError,'Clé absente ou dupliquée'): self.run_mart()
    def test_missing_contract_blocked(self):
        with duckdb.connect(str(self.db)) as db:
            db.execute('UPDATE core.fait_sinistre SET contrat_id=999 WHERE sinistre_id=1')
        with self.assertRaisesRegex(ValueError,'sans contrat'): self.run_mart()
    def test_repeat_stable(self):
        self.run_mart()
        first=(self.root/'exports/mart_segments.csv').read_bytes()
        self.run_mart()
        self.assertEqual(first,(self.root/'exports/mart_segments.csv').read_bytes())
    def test_resiliation_janvier_without_exposure_in_year(self):
        with duckdb.connect(str(self.db)) as db:
            db.execute("UPDATE core.dim_contrat SET date_resiliation=DATE '2025-01-01' WHERE contrat_id=2")
        self.run_mart()
        with duckdb.connect(str(self.db)) as db:
            row=db.execute("SELECT annee,nb_resiliations,exposition_annees,taux_resiliation FROM marts.mart_segments WHERE annee=2025 AND segment_id=10").fetchone()
        self.assertEqual(row,(2025,1,0.0,None))

    def test_zero_exposure_null_rates(self):
        with duckdb.connect(str(self.db)) as db:
            db.execute('DELETE FROM core.fait_exposition WHERE segment_id=10')
        self.run_mart()
        with duckdb.connect(str(self.db)) as db:
            row=db.execute('SELECT frequence,prime_moyenne,ratio_sp,taux_resiliation FROM marts.mart_segments WHERE segment_id=10').fetchone()
        self.assertEqual(row,(None,None,None,None))

if __name__=='__main__': unittest.main()
