import unittest

import numpy as np

from inksurf.ink9um_ct_support import chunk_support


class Ink9umCtSupportTests(unittest.TestCase):
    def test_support_is_measured_only_on_evaluation_mask(self):
        volume = np.zeros((3, 2, 2), dtype=np.uint8)
        volume[1, 0, 0] = 5
        volume[0, 1, 1] = 5
        mask = np.array([[1, 0], [0, 1]], dtype=bool)
        result = chunk_support(volume, mask, (1, 2))
        self.assertEqual(result["any_depth_support_fraction"], 1.0)
        self.assertEqual(result["central_depth_support_fraction"], 0.5)

    def test_empty_mask_fails_closed(self):
        with self.assertRaises(ValueError):
            chunk_support(np.ones((3, 2, 2)), np.zeros((2, 2)), (1, 2))


if __name__ == "__main__":
    unittest.main()
