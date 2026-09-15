import unittest

import numpy as np

from inksurf.seating_io_plan import chunk_keys, densest_square


class SeatingIoPlanTests(unittest.TestCase):
    def test_densest_square_is_deterministic(self):
        mask = np.zeros((5, 6), dtype=bool); mask[2:5, 1:4] = True
        self.assertEqual(densest_square(mask, 3), (2, 1, 9))

    def test_chunk_keys_are_deduplicated(self):
        points = np.array([[10, 10, 10], [11, 11, 11]], dtype=float)
        normals = np.array([[1, 0, 0], [1, 0, 0]], dtype=float)
        keys = chunk_keys(points, normals, np.array([0, 2, -2]), 128)
        np.testing.assert_array_equal(keys, [[0, 0, 0]])


if __name__ == "__main__":
    unittest.main()
