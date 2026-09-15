import unittest

import numpy as np

from inksurf.io_plan import centered_bounds_zyx, intersecting_chunks_zyx, raw_chunk_bytes


class IoPlanTests(unittest.TestCase):
    def test_half_open_bounds_and_chunk_deduplication(self):
        lo, hi = centered_bounds_zyx((256, 256, 256), (128, 128, 128), (1000, 1000, 1000))
        np.testing.assert_array_equal(lo, [192, 192, 192])
        np.testing.assert_array_equal(hi, [320, 320, 320])
        chunks = intersecting_chunks_zyx(lo, hi, (256, 256, 256))
        self.assertEqual(len(chunks), 8)
        self.assertEqual(len(set(chunks)), 8)

    def test_edge_clipping(self):
        lo, hi = centered_bounds_zyx((10, 10, 10), (64, 64, 64), (100, 100, 100))
        np.testing.assert_array_equal(lo, [0, 0, 0])
        np.testing.assert_array_equal(hi, [42, 42, 42])

    def test_raw_bytes(self):
        self.assertEqual(raw_chunk_bytes(2, (4, 4, 4), "uint8", 3), 384)


if __name__ == "__main__":
    unittest.main()
