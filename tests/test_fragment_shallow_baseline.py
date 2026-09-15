import unittest

import numpy as np

from inksurf.fragment_shallow_baseline import assign_vertical_folds


class FragmentShallowBaselineTests(unittest.TestCase):
    def test_vertical_folds_are_contiguous_and_complete(self) -> None:
        x0 = np.asarray([0, 0, 256, 256, 512, 512, 768, 768])
        folds = assign_vertical_folds(x0, 2)
        np.testing.assert_array_equal(folds, [0, 0, 0, 0, 1, 1, 1, 1])

    def test_rejects_too_many_folds(self) -> None:
        with self.assertRaises(ValueError):
            assign_vertical_folds(np.asarray([0, 256]), 3)


if __name__ == "__main__":
    unittest.main()
