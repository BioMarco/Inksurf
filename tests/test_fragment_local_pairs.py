import unittest

import numpy as np

from inksurf.fragment_local_pairs import match_local_controls


class FragmentLocalPairsTests(unittest.TestCase):
    def test_pairs_are_unique_and_in_annulus(self) -> None:
        ink = np.asarray([[10, 10], [20, 20], [30, 30]])
        controls = np.ones((50, 50), dtype=bool)
        pairs = match_local_controls(
            ink, controls, maximum=3, minimum_distance=3, maximum_distance=8,
            attempts=200, rng=np.random.default_rng(3),
        )
        self.assertEqual(len(pairs), 3)
        self.assertEqual(len({(pair[2], pair[3]) for pair in pairs}), 3)
        self.assertTrue(all(3 <= pair[4] <= 8 for pair in pairs))


if __name__ == "__main__":
    unittest.main()
