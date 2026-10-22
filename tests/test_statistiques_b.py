import importlib.util
import itertools
from pathlib import Path
import unittest
import numpy as np
spec=importlib.util.spec_from_file_location('technicalstats',Path(__file__).resolve().parents[1]/'analyses/04_statistiques.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class StatisticsTests(unittest.TestCase):
    def test_poisson_zero_count(self):
        lo,hi=mod.poisson_interval(0,100)
        self.assertEqual(lo,0)
        self.assertAlmostEqual(hi,0.03688879454113935)
    def test_shapley_reconciles_variation(self):
        before=[0.1,1000,500];after=[0.2,1500,600]
        effects=mod.shapley(before,after)
        self.assertAlmostEqual(effects.sum(),0.5-0.2)
    def test_shapley_one_factor(self):
        effects=mod.shapley([.1,1000,500],[.2,1000,500])
        np.testing.assert_allclose(effects,[.2,0,0])
    def test_shapley_reverse(self):
        a=[.1,1000,500];b=[.2,1500,600]
        np.testing.assert_allclose(mod.shapley(a,b),-mod.shapley(b,a),atol=1e-12)
    def test_no_exposure_has_no_interval(self):
        self.assertTrue(all(np.isnan(x) for x in mod.poisson_interval(1,0)))

if __name__=='__main__': unittest.main()
