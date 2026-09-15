import tempfile
import unittest
from pathlib import Path

import numpy as np
from numcodecs import Blosc

from inksurf.ink9um_chunk_audit import decode_annotation, pool_centered


class Ink9umChunkAuditTests(unittest.TestCase):
    def test_pool_centered_matches_official_contract(self):
        source = np.arange(109, dtype=np.uint8)[:, None, None]
        pooled = pool_centered(source, 21, 4)
        self.assertEqual(pooled.shape, (21, 1, 1))
        self.assertEqual(pooled[0, 0, 0], 14)
        self.assertEqual(pooled[-1, 0, 0], 94)

    def test_decode_blosc_annotation(self):
        source = np.arange(2 * 3 * 4, dtype=np.uint8).reshape(2, 3, 4)
        codec = Blosc(cname="zstd", clevel=5, shuffle=Blosc.BITSHUFFLE)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "chunk"
            path.write_bytes(codec.encode(source))
            np.testing.assert_array_equal(decode_annotation(path, source.shape), source)


if __name__ == "__main__":
    unittest.main()
