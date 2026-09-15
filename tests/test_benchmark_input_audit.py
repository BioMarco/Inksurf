import unittest

import numpy as np

from inksurf.benchmark_input_audit import _percentiles_from_histogram, summarize_region


class BenchmarkInputAuditTests(unittest.TestCase):
    def test_region_summary_respects_mask(self):
        prediction = np.array([[1, 2], [100, 200]], dtype=np.uint8)
        labels = np.array([[0, 255], [255, 255]], dtype=np.uint8)
        mask = np.array([[255, 255], [0, 0]], dtype=np.uint8)
        result = summarize_region(prediction, labels, mask)
        self.assertEqual(result["valid_pixels"], 2)
        self.assertEqual(result["ink_pixels"], 1)
        self.assertEqual(result["ink_fraction"], 0.5)
        self.assertEqual(result["prediction_max"], 2)

    def test_empty_region_is_explicit(self):
        zeros = np.zeros((2, 2), dtype=np.uint8)
        result = summarize_region(zeros, zeros, zeros)
        self.assertEqual(result["valid_pixels"], 0)
        self.assertIsNone(result["prediction_mean"])

    def test_histogram_percentiles(self):
        histogram = np.zeros(256, dtype=np.int64)
        histogram[10] = 3
        histogram[20] = 1
        result = _percentiles_from_histogram(histogram, [0.5, 0.99])
        self.assertEqual(result["p50"], 10)
        self.assertEqual(result["p99"], 20)


if __name__ == "__main__":
    unittest.main()
