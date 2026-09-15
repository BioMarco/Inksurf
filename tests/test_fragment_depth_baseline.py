import unittest

import numpy as np

from inksurf.fragment_depth_baseline import depth_features, histogram_metrics


class FragmentDepthBaselineTests(unittest.TestCase):
    def test_depth_features(self) -> None:
        stack = np.arange(4 * 2 * 2, dtype=np.uint16).reshape(4, 2, 2)
        result = depth_features(stack, 1, 3)
        np.testing.assert_allclose(result["depth_mean"], stack.mean(axis=0))
        np.testing.assert_allclose(result["central_contrast"], stack[1:3].mean(axis=0) - stack[[0, 3]].mean(axis=0))

    def test_histogram_metrics_favors_correct_direction(self) -> None:
        scores = np.asarray([[0.0, 1.0, 2.0, 3.0]])
        labels = np.asarray([[False, False, True, True]])
        valid = np.ones_like(labels)
        high = histogram_metrics(scores, labels, valid, 4, "high")
        low = histogram_metrics(scores, labels, valid, 4, "low")
        self.assertGreater(high["approximate_average_precision"], low["approximate_average_precision"])
        self.assertEqual(high["best_f0_5"], 1.0)


if __name__ == "__main__":
    unittest.main()
