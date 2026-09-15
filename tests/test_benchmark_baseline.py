import unittest

import numpy as np

from inksurf.benchmark_baseline import average_precision, review_metrics


class BenchmarkBaselineTests(unittest.TestCase):
    def test_average_precision_perfect_and_reversed(self):
        labels = np.array([1, 0, 1, 0], dtype=bool)
        self.assertEqual(average_precision(labels, np.array([4, 2, 3, 1])), 1.0)
        self.assertAlmostEqual(average_precision(labels, np.array([1, 3, 2, 4])), 5 / 12)

    def test_average_precision_handles_ties_as_threshold(self):
        labels = np.array([1, 0], dtype=bool)
        self.assertEqual(average_precision(labels, np.array([1, 1])), 0.5)

    def test_review_enrichment(self):
        result = review_metrics(
            np.array([2.0, 1.0]),
            np.array([50, 0]),
            np.array([100, 100]),
            0.5,
        )
        self.assertEqual(result["regions_reviewed"], 1)
        self.assertEqual(result["reference_ink_recall"], 1.0)
        self.assertEqual(result["enrichment"], 2.0)


if __name__ == "__main__":
    unittest.main()
