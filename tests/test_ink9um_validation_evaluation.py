import unittest

import numpy as np

from inksurf.ink9um_validation_evaluation import bootstrap_mean_interval, metrics


class Ink9umValidationEvaluationTests(unittest.TestCase):
    def test_metrics_prefers_ordered_scores(self):
        labels = np.array([0, 0, 1, 1], dtype=bool)
        result = metrics(labels, np.array([0.1, 0.2, 0.8, 0.9]))
        self.assertAlmostEqual(result["average_precision"], 1.0)
        self.assertGreater(result["mean_margin"], 0)

    def test_bootstrap_interval_is_deterministic(self):
        values = np.array([0.1, 0.2, 0.3])
        self.assertEqual(bootstrap_mean_interval(values, 100, 7), bootstrap_mean_interval(values, 100, 7))


if __name__ == "__main__":
    unittest.main()
