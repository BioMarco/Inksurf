import tempfile
import unittest
from pathlib import Path

import numpy as np

from inksurf.ink_model_compatibility import assemble_raw_window, enforce_cpu_tile_guard, grid_1d, hann2d


class InkModelCompatibilityTests(unittest.TestCase):
    def test_grid_for_frozen_window(self):
        self.assertEqual(grid_1d(512, 256, 128), [0, 128, 256])

    def test_hann_is_normalized(self):
        weights = hann2d(8, 8)
        self.assertAlmostEqual(float(weights.sum()), 1.0, places=6)
        self.assertEqual(float(weights[0, 0]), 0.0)

    def test_cpu_multitile_requires_explicit_override(self):
        with self.assertRaises(RuntimeError):
            enforce_cpu_tile_guard(9, False)
        enforce_cpu_tile_guard(9, True)
        enforce_cpu_tile_guard(1, False)

    def test_assemble_unaligned_window(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); volume = "v"
            full = np.arange(4 * 6 * 8, dtype=np.uint8).reshape(4, 6, 8)
            chunks = [2, 3, 4]
            for z in range(2):
                for y in range(2):
                    for x in range(2):
                        path = root / volume / "0" / str(z) / str(y) / str(x)
                        path.parent.mkdir(parents=True, exist_ok=True)
                        full[z*2:(z+1)*2, y*3:(y+1)*3, x*4:(x+1)*4].tofile(path)
            actual = assemble_raw_window(root, volume, 0, [4, 6, 8], chunks, [1, 2, 3], [2, 3, 4])
            np.testing.assert_array_equal(actual, full[1:3, 2:5, 3:7])


if __name__ == "__main__":
    unittest.main()
