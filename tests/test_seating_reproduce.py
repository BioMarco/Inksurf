import unittest

import numpy as np

from inksurf.seating_reproduce import probe_and_score


class SeatingReproduceTests(unittest.TestCase):
    def test_flat_reader_has_zero_contrast(self):
        points = np.array([[10, 10, 10], [20, 20, 20]], dtype=float)
        normals = np.array([[1, 0, 0], [1, 0, 0]], dtype=float)
        result = probe_and_score(points, normals, lambda coordinates: np.full(len(coordinates), 100), 10)
        self.assertAlmostEqual(result["score"], 0.0)
        self.assertEqual(result["coverage"], 1.0)


if __name__ == "__main__":
    unittest.main()
