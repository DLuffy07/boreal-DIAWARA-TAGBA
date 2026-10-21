import importlib.util
from pathlib import Path
import tempfile
import unittest
import duckdb
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('clientsmetrics',ROOT/'analyses/05_clients_sinistres.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def fixture(db):
    db.execute('''CREATE SCHEMA core;CREATE SCHEMA marts;
    CREATE TABLE core.v_client_analyse AS SELECT * FROM (VALUES
      (1,'IDF','35-49','CADRE'),(2,'OCC','25-34','EMPLOYE'),(3,'IDF','50-64','CADRE'))
      t(client_id_maitre,region,tranche_age,csp);
    CREATE TABLE core.dim_contrat AS SELECT * FROM (VALUES
      (1,1,'AUTO','CONFORT','WEB',1,DATE '2020-01-01',DATE '2021-01-01'),
      (2,1,'HABITATION','CONFORT','WEB',1,DATE '2020-01-01',NULL),
      (3,2,'AUTO','CONFORT','AGENT',2,DATE '2024-12-01',NULL),
      (4,3,'AUTO','CONFORT','AGENT',2,DATE '2023-01-01',DATE '2025-01-01'))
      t(contrat_id,client_id_maitre,produit,formule,canal_distribution,zone_risque,date_effet,date_resiliation);
    CREATE TABLE core.fait_exposition AS SELECT * FROM (VALUES (1,500.0),(2,300.0),(3,400.0),(4,200.0)) t(contrat_id,prime_acquise);
    CREATE TABLE core.fait_sinistre AS SELECT * FROM (VALUES
      (1,1,DATE '2020-01-01',DATE '2020-01-03','RC','CLOTURE',DATE '2020-01-10',DATE '2020-01-15',100.0,100.0,true,true,DATE '2020-01-05'),
      (2,3,DATE '2025-02-01',DATE '2025-02-02','RC','OUVERT',NULL,NULL,0.0,200.0,false,false,NULL))
      t(sinistre_id,contrat_id,date_survenance,date_declaration,garantie,statut,date_premier_paiement,date_dernier_paiement,montant_paye,charge,audite,fraude_confirmee,date_audit);''')

class ClientMetricsTests(unittest.TestCase):
    def setUp(self):
        self.db=duckdb.connect(':memory:');fixture(self.db)
        self.db.execute((ROOT/'sql/marts/20_clients_sinistres.sql').read_text(encoding='utf-8'))
    def tearDown(self): self.db.close()
    def test_recent_cohort_not_observable(self):
        row=self.db.execute("SELECT observable,taux_retention FROM marts.mart_retention WHERE cohorte=2024 AND produit='AUTO' AND anciennete=1 AND detention_entree='Tous'").fetchone()
        self.assertEqual(row,(False,None))
    def test_exclusive_resiliation_anniversary(self):
        row=self.db.execute("SELECT taux_retention FROM marts.mart_retention WHERE cohorte=2020 AND produit='AUTO' AND anciennete=1 AND detention_entree='Tous'").fetchone()
        self.assertEqual(row[0],0.0)
    def test_multiholding_at_entry_not_current(self):
        row=self.db.execute("SELECT detention_entree FROM marts.mart_retention_individuelle WHERE client_id_maitre=1 AND produit='AUTO' AND anciennete=0").fetchone()
        self.assertEqual(row[0],'Multi à entrée')
        self.assertFalse(self.db.execute('SELECT multi_detenteur_actuel FROM marts.mart_valeur_client WHERE client_id_maitre=1').fetchone()[0])
    def test_missing_payment_not_zero_delay(self):
        row=self.db.execute('SELECT delai_premier_reglement_jours,delai_dernier_reglement_clotures_jours FROM marts.mart_delais WHERE sinistre_id=2').fetchone()
        self.assertEqual(row,(None,None))
    def test_last_payment_proxy(self):
        self.assertEqual(self.db.execute('SELECT delai_dernier_reglement_clotures_jours FROM marts.mart_delais WHERE sinistre_id=1').fetchone()[0],12)
    def test_value_reconciles(self):
        mod.validate(self.db)
        self.assertAlmostEqual(self.db.execute('SELECT sum(valeur_observee) FROM marts.mart_valeur_client').fetchone()[0],1300.0)
    def test_wilson_all_success_bounds(self):
        low,high=mod.wilson(np.array([10]),np.array([10]))
        self.assertAlmostEqual(high[0],1.0)
        self.assertGreater(low[0],0.7)
    def test_audits_only_audited_population(self):
        self.assertEqual(self.db.execute("SELECT nb_audits,nb_fraudes_confirmees,taux_confirmation FROM marts.mart_audits WHERE axe='global'").fetchone(),(1,1,1.0))

if __name__=='__main__':unittest.main()
