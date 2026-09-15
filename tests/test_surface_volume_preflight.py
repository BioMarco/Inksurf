import unittest

from inksurf.surface_volume_preflight import candidate_chunk_indices


class SurfaceVolumePreflightTests(unittest.TestCase):
    def test_deduplicates_chunks_and_includes_depth_edge(self) -> None:
        candidates = [
            {"candidate_id": "a", "bounds_yx": {"y0": 0, "y1": 256, "x0": 0, "x1": 256}},
            {"candidate_id": "b", "bounds_yx": {"y0": 128, "y1": 384, "x0": 0, "x1": 256}},
        ]
        indices = candidate_chunk_indices(
            candidates, shape=(65, 512, 512), chunks=(64, 256, 256), depth_range=(0, 65),
        )
        self.assertEqual(indices, [(0, 0, 0), (0, 1, 0), (1, 0, 0), (1, 1, 0)])

    def test_rejects_candidate_outside_array(self) -> None:
        with self.assertRaises(ValueError):
            candidate_chunk_indices(
                [{"candidate_id": "x", "bounds_yx": {"y0": 0, "y1": 513, "x0": 0, "x1": 1}}],
                shape=(65, 512, 512), chunks=(64, 256, 256), depth_range=(0, 65),
            )


if __name__ == "__main__":
    unittest.main()
