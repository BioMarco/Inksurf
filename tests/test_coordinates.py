import unittest

import numpy as np

from inksurf.coordinates import apply_affine_zyx, chunk_centers_zyx, level0_to_level


class CoordinateTests(unittest.TestCase):
    def test_documented_gp_center_landmark(self):
        matrix = np.array(
            [
                [3.26113192, -0.0430053155, 0.0234621175, 29400.7294],
                [0.0469460556, 2.52585108, -2.05228272, 15821.0804],
                [-0.00893849999, -2.05174152, -2.52748174, 33653.8570],
                [0.0, 0.0, 0.0, 1.0],
            ]
        )
        point = np.array([6912.0, 3648.0, 3776.0])
        actual = apply_affine_zyx(point, matrix)
        np.testing.assert_allclose(actual, [51873.38, 17610.46, 16563.55], atol=0.02)

    def test_chunk_center_and_level_conversion(self):
        centers = chunk_centers_zyx(np.array([[0, 11, 15]]), (128, 128, 128))
        np.testing.assert_array_equal(centers, [[64.0, 1472.0, 1984.0]])
        np.testing.assert_array_equal(level0_to_level([[16, 24, 32]], 3, rounding=True), [[2, 3, 4]])

    def test_rejects_implicit_coordinate_shape(self):
        with self.assertRaises(ValueError):
            apply_affine_zyx([1, 2], np.eye(4))


if __name__ == "__main__":
    unittest.main()
