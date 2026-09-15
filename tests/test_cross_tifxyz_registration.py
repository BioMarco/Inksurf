import unittest

import numpy as np

from inksurf.cross_tifxyz_registration import apply_affine, fit_affine, paired_uv_samples


class CrossTifxyzRegistrationTests(unittest.TestCase):
    def test_affine_fit_recovers_exact_transform(self):
        source = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 2, 3]], dtype=float)
        expected = np.array([[2, 0, 0], [0, 3, 0], [0, 0, 4], [5, 6, 7]], dtype=float)
        target = apply_affine(source, expected)
        self.assertTrue(np.allclose(fit_affine(source, target), expected))

    def test_uv_pairing_maps_endpoints_between_grid_sizes(self):
        source = np.zeros((3, 3, 3), dtype=float)
        target = np.zeros((5, 5, 3), dtype=float)
        source[..., 2] = 1
        target[..., 2] = 1
        target[4, 4, 0] = 9
        paired_source, paired_target, rows, columns = paired_uv_samples(source, target, 2)
        index = np.where((rows == 2) & (columns == 2))[0][0]
        self.assertEqual(paired_target[index, 0], 9)


if __name__ == "__main__":
    unittest.main()
