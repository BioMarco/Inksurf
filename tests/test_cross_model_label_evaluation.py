import unittest

import numpy as np

from inksurf.cross_model_label_evaluation import average_precision, sample_bilinear_roi


class CrossModelLabelEvaluationTests(unittest.TestCase):
    def test_average_precision_perfect_and_tied(self):
        labels = np.array([1, 0, 1, 0], dtype=bool)
        self.assertEqual(average_precision(labels, np.array([4, 1, 3, 0])), 1.0)
        self.assertAlmostEqual(average_precision(labels, np.ones(4)), 0.5)

    def test_average_precision_rejects_single_class(self):
        with self.assertRaises(ValueError):
            average_precision(np.ones(3, dtype=bool), np.arange(3))

    def test_bilinear_identity_roi(self):
        image = np.arange(16, dtype=float).reshape(4, 4)
        gy = np.arange(4)[:, None]
        gx = np.arange(4)[None, :]
        sampled = sample_bilinear_roi(image, gy, gx, (4, 4), (4, 4), (0, 4, 0, 4))
        np.testing.assert_allclose(sampled, image)


if __name__ == "__main__":
    unittest.main()
