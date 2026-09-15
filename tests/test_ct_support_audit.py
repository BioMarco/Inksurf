import unittest

from inksurf.ct_support_audit import decoded_chunk_shape


class CtSupportAuditTests(unittest.TestCase):
    def test_edge_chunk_shape(self) -> None:
        self.assertEqual(decoded_chunk_shape((0, 0, 0), (65, 300, 300), (64, 256, 256)), (64, 256, 256))
        self.assertEqual(decoded_chunk_shape((1, 1, 1), (65, 300, 300), (64, 256, 256)), (1, 44, 44))


if __name__ == "__main__":
    unittest.main()
