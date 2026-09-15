import unittest

import numpy as np

from inksurf.fragment_asset_audit import summarize


class FragmentAssetAuditTests(unittest.TestCase):
    def test_summary_respects_mask_and_half_open_bbox(self) -> None:
        ir = np.arange(16, dtype=np.uint8).reshape(4, 4)
        labels = np.zeros((4, 4), dtype=np.uint8)
        labels[1, 1] = 255
        labels[3, 3] = 255
        mask = np.zeros((4, 4), dtype=np.uint8)
        mask[1:3, 1:4] = 255
        result = summarize(ir, labels, mask)
        self.assertEqual(result["valid_pixels"], 6)
        self.assertEqual(result["ink_pixels_inside_mask"], 1)
        self.assertEqual(result["ink_pixels_outside_mask"], 1)
        self.assertEqual(result["mask_bbox_yx_half_open"], [1, 3, 1, 4])

    def test_rejects_misaligned_inputs(self) -> None:
        with self.assertRaises(ValueError):
            summarize(np.zeros((2, 2)), np.zeros((2, 3)), np.zeros((2, 2)))


if __name__ == "__main__":
    unittest.main()
