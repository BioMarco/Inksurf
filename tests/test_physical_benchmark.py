import unittest

import numpy as np

from inksurf.physical_benchmark import evaluate_policy


class PhysicalBenchmarkTests(unittest.TestCase):
    def test_aggregates_area_and_yield(self):
        result = evaluate_policy(
            [np.array([[1, 1]], dtype=bool)],
            [np.array([[1, 0]], dtype=bool)],
            [np.ones((1, 2), dtype=bool)],
            [np.array([[10.0, 20.0]])],
            minimum_component_area_mm2=0.0,
        )
        self.assertEqual(result["true_positive_pixels"], 1)
        self.assertEqual(result["pixel_precision"], 0.5)
        self.assertEqual(result["pixel_recall"], 1.0)
        self.assertAlmostEqual(result["false_positive_area_cm2"], 2e-7)

    def test_zero_yield_is_explicit(self):
        result = evaluate_policy(
            [np.zeros((1, 2), dtype=bool)], [np.array([[1, 0]], dtype=bool)],
            [np.ones((1, 2), dtype=bool)], [np.ones((1, 2))],
            minimum_component_area_mm2=0.0,
        )
        self.assertIsNone(result["pixel_precision"])
        self.assertEqual(result["pixel_recall"], 0.0)


if __name__ == "__main__":
    unittest.main()
