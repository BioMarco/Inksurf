import unittest

import numpy as np

from inksurf.fragment_profile_model import contiguous_fold_ids, profile_features


class FragmentProfileModelTests(unittest.TestCase):
    def test_profile_features_are_finite_and_named(self) -> None:
        values = np.arange(32, dtype=np.float32).reshape(2, 16)
        features, names = profile_features(values)
        self.assertEqual(features.shape, (2, 24))
        self.assertEqual(len(names), 24)
        self.assertTrue(np.isfinite(features).all())

    def test_contiguous_folds_keep_block_rows_together(self) -> None:
        blocks = np.asarray(["by00_bx00", "by00_bx01", "by01_bx00", "by02_bx00", "by03_bx00"])
        folds = contiguous_fold_ids(blocks, 2)
        self.assertEqual(folds[0], folds[1])
        self.assertEqual(set(folds), {0, 1})


if __name__ == "__main__":
    unittest.main()
