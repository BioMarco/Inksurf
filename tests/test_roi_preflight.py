import unittest

import numpy as np

from inksurf.roi_preflight import select_density_candidates


class RoiPreflightTests(unittest.TestCase):
    def test_selection_is_deterministic_and_separated(self):
        points = np.array(
            [[1, 1, 1], [2, 2, 2], [101, 1, 1], [102, 2, 2], [201, 1, 1]],
            dtype=float,
        )
        result = select_density_candidates(
            points, bin_shape_zyx=(100, 100, 100), limit=2, minimum_separation=50
        )
        self.assertEqual([r["density_bin_zyx"] for r in result], [[0, 0, 0], [1, 0, 0]])
        self.assertEqual([r["density_count"] for r in result], [2, 2])


if __name__ == "__main__":
    unittest.main()
