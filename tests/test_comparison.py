"""Intervals use accepted sample sizes and cover boundary counts."""
import unittest

from qweave.comparison import fidelity_difference, acceptance_summary


class ComparisonTests(unittest.TestCase):
    def test_identical_perfect_counts_have_nonzero_difference_interval(self):
        counts={'XX':{'00':1000},'YY':{'01':1000},'ZZ':{'00':1000}}
        result=fidelity_difference(counts,counts)
        self.assertEqual(result['difference'],0.)
        self.assertLess(result['interval'][0],0.)
        self.assertGreater(result['interval'][1],0.)

    def test_sign_and_accepted_denominator(self):
        reference={'XX':{'00':900,'01':100},'YY':{'01':900,'00':100},'ZZ':{'00':900,'01':100}}
        candidate={'XX':{'00':95,'01':5},'YY':{'01':95,'00':5},'ZZ':{'00':95,'01':5}}
        forward=fidelity_difference(reference,candidate)
        backward=fidelity_difference(candidate,reference)
        self.assertAlmostEqual(forward['difference'],.075)
        self.assertAlmostEqual(forward['interval'][0],-backward['interval'][1])
        larger={basis:{key:100*n for key,n in counts.items()} for basis,counts in candidate.items()}
        precise=fidelity_difference(reference,larger)
        self.assertLess(precise['interval'][1]-precise['interval'][0],forward['interval'][1]-forward['interval'][0])

    def test_zero_acceptance_is_undefined(self):
        counts={'XX':{},'YY':{'01':100},'ZZ':{'00':100}}
        self.assertIsNone(fidelity_difference(counts,counts)['interval'])
        self.assertEqual(acceptance_summary(0,100)['fraction'],0.)
