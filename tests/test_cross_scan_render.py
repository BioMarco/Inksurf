import tempfile
import unittest
from pathlib import Path

import numpy as np

from inksurf.cross_scan_render import ChunkReader


class CrossScanRenderTests(unittest.TestCase):
    def test_trilinear_interpolates_linear_volume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            chunk_path = root / "0" / "0" / "0"
            chunk_path.parent.mkdir(parents=True)
            z, y, x = np.mgrid[:4, :4, :4]
            (z + 2 * y + 3 * x).astype(np.uint8).tofile(chunk_path)

            reader = ChunkReader(root, chunk=4)
            result = reader.trilinear(np.array([[1.5, 1.5, 1.5]], dtype=float))

            np.testing.assert_allclose(result, [9.0])
            self.assertEqual(set(reader.loaded), {(0, 0, 0)})


if __name__ == "__main__":
    unittest.main()
