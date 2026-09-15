import unittest

import numpy as np

from inksurf.cross_scan_consistency import correlations, shifted_pearson, top_overlap


class CrossScanConsistencyTests(unittest.TestCase):
    def test_identical_maps_have_perfect_agreement_and_enriched_overlap(self):
        first = np.arange(100, dtype=np.float32).reshape(10, 10)
        valid = np.ones_like(first, dtype=bool)
        self.assertAlmostEqual(correlations(first, first, valid)["pearson_r"], 1.0)
        result = top_overlap(first, first, valid, 0.10)
        self.assertAlmostEqual(result["overlap_enrichment_vs_independence"], 10.0)

    def test_shift_control_uses_only_overlapping_pixels(self):
        first = np.arange(36, dtype=np.float32).reshape(6, 6)
        valid = np.ones_like(first, dtype=bool)
        self.assertAlmostEqual(shifted_pearson(first, first, valid, 1, 0), 1.0)


if __name__ == "__main__":
    unittest.main()
