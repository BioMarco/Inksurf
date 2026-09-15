import unittest

from inksurf.ink9um_validation_preflight import raw_chunk_bytes, select_validation_chunks


class Ink9umValidationPreflightTests(unittest.TestCase):
    def test_selects_largest_then_lexicographic(self):
        items = [
            {"path": "a_validation_mask.zarr/0/0.2.1", "size": 90},
            {"path": "a_validation_mask.zarr/0/0.1.2", "size": 120},
            {"path": "a_validation_mask.zarr/0/0.1.1", "size": 120},
            {"path": "a_inklabels.zarr/0/0.0.0", "size": 999},
        ]
        result = select_validation_chunks(items, 2)
        self.assertEqual([entry["chunk_yx"] for entry in result], [[1, 1], [1, 2]])

    def test_raw_bytes_handles_edge_chunks(self):
        self.assertEqual(raw_chunk_bytes([109, 300, 270], [109, 128, 128], 2, 2), 109 * 44 * 14)


if __name__ == "__main__":
    unittest.main()
