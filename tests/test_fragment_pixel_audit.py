import unittest

import numpy as np

from inksurf.fragment_pixel_audit import paired_block_interval


class FragmentPixelAuditTests(unittest.TestCase):
    def test_interval_is_deterministic_and_contains_mean(self) -> None:
        differences = np.asarray([1.0, 2.0, 3.0, 4.0])
        first = paired_block_interval(differences, 500, 7)
        second = paired_block_interval(differences, 500, 7)
        self.assertEqual(first, second)
        self.assertLess(first["low"], differences.mean())
        self.assertGreater(first["high"], differences.mean())


if __name__ == "__main__":
    unittest.main()
