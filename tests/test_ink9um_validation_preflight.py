import unittest

from inksurf.ink9um_validation_preflight import (
    InsufficientChunks,
    raw_chunk_bytes,
    select_validation_chunks,
    support_overlap_fraction,
    validate_annotation_provenance,
)


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

    def test_selection_can_be_limited_by_metadata_coverage(self):
        items = [
            {"path": "a_validation_mask.zarr/0/0.10.1", "size": 200},
            {"path": "a_validation_mask.zarr/0/0.20.1", "size": 100},
        ]
        result = select_validation_chunks(items, 1, [[14, 35], [0, 54]])
        self.assertEqual(result[0]["chunk_yx"], [20, 1])

    def test_empty_compressed_chunks_can_be_excluded(self):
        items = [{"path": "a_validation_mask.zarr/0/0.20.1", "size": 78}]
        with self.assertRaises(InsufficientChunks) as caught:
            select_validation_chunks(items, 1, minimum_compressed_bytes=79)
        self.assertEqual((caught.exception.found, caught.exception.required), (0, 1))

    def test_selection_mask_kind_is_configurable(self):
        items = [{"path": "a_supervision_mask.zarr/0/0.20.1", "size": 100}]
        result = select_validation_chunks(items, 1, selection_mask_kind="supervision_mask")
        self.assertEqual(result[0]["chunk_yx"], [20, 1])

    def test_annotation_provenance_matches_source_and_level(self):
        attrs = {"source_surface_volume": "https://example.test/source.zarr/", "source_surface_volume_level": 2}
        validate_annotation_provenance(attrs, "https://example.test/source.zarr", 2)
        with self.assertRaises(ValueError):
            validate_annotation_provenance(attrs, "https://example.test/other.zarr", 2)
        with self.assertRaises(ValueError):
            validate_annotation_provenance(attrs, "https://example.test/source.zarr", 1)

    def test_support_overlap_uses_declared_rectangles(self):
        support = {
            "source_canvas_shape_yx": [100, 100], "target_shape_yx": [100, 100],
            "chunk_pixels": 10, "chunk_to_source_scale": 1,
            "rects_y0_y1_x0_x1": [[5, 15, 0, 10]], "minimum_overlap_fraction": 0.5,
        }
        self.assertEqual(support_overlap_fraction((0, 0), support), 0.5)
        items = [
            {"path": "a_supervision_mask.zarr/0/0.0.0", "size": 100},
            {"path": "a_supervision_mask.zarr/0/0.2.0", "size": 200},
        ]
        result = select_validation_chunks(
            items, 1, selection_mask_kind="supervision_mask", selection_support=support,
        )
        self.assertEqual(result[0]["chunk_yx"], [0, 0])

    def test_overlapping_support_rectangles_fail(self):
        support = {
            "source_canvas_shape_yx": [100, 100], "target_shape_yx": [100, 100],
            "chunk_pixels": 10, "chunk_to_source_scale": 1,
            "rects_y0_y1_x0_x1": [[0, 10, 0, 10], [5, 15, 5, 15]],
            "minimum_overlap_fraction": 0.1,
        }
        with self.assertRaises(ValueError):
            support_overlap_fraction((0, 0), support)


if __name__ == "__main__":
    unittest.main()
