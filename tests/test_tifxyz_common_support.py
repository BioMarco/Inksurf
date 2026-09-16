import unittest

import numpy as np

from inksurf.tifxyz_common_support import sample_grid_support


class TifxyzCommonSupportTests(unittest.TestCase):
    def test_policies_bound_edge_support(self):
        valid = np.array([[1, 0], [1, 1]], dtype=bool)
        gy = np.array([[0]])
        gx = np.array([[0]])
        self.assertFalse(sample_grid_support(valid, gy, gx, (1, 1), "all")[0, 0])
        self.assertTrue(sample_grid_support(valid, gy, gx, (1, 1), "any")[0, 0])

    def test_invalid_policy_fails(self):
        with self.assertRaises(ValueError):
            sample_grid_support(np.ones((2, 2), bool), np.array([[0]]), np.array([[0]]), (1, 1), "mean")


if __name__ == "__main__":
    unittest.main()
