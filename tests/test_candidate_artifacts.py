import unittest

import numpy as np

from inksurf.candidate_artifacts import mask_iou


class CandidateArtifactsTests(unittest.TestCase):
    def test_mask_iou(self) -> None:
        left = np.asarray([[1, 1], [0, 0]], dtype=bool)
        right = np.asarray([[1, 0], [1, 0]], dtype=bool)
        self.assertAlmostEqual(mask_iou(left, right), 1 / 3)
        self.assertEqual(mask_iou(np.zeros((2, 2), bool), np.zeros((2, 2), bool)), 1.0)


if __name__ == "__main__":
    unittest.main()
