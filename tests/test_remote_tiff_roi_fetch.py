import unittest

import numpy as np

from inksurf.remote_tiff_roi_fetch import extract_roi


class RemoteTiffRoiFetchTests(unittest.TestCase):
    def test_extracts_across_four_tiles(self):
        tiles = {
            0: np.full((2, 2), 1), 1: np.full((2, 2), 2),
            2: np.full((2, 2), 3), 3: np.full((2, 2), 4),
        }
        result = extract_roi(tiles, (1, 3, 1, 3), (4, 4), (2, 2))
        np.testing.assert_array_equal(result, [[1, 2], [3, 4]])


if __name__ == "__main__":
    unittest.main()
