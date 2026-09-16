import unittest

from inksurf.ink9um_provenance_census import parse_ink_render, source_segment_prefix


class Ink9umProvenanceCensusTests(unittest.TestCase):
    def test_source_segment_is_taken_from_attributes_not_case_name(self):
        sample, prefix = source_segment_prefix(
            "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0139/segments/segment-w045/surface-volumes/a.zarr"
        )
        self.assertEqual(sample, "PHerc0139")
        self.assertEqual(prefix, "PHerc0139/segments/segment-w045")

    def test_render_provenance_is_parsed_from_filename(self):
        row = parse_ink_render(
            "PHerc0139/segments/s/ink-detection/PHerc0139-s-1.129um-volume-20260413113053-L1-x-mrg20736-1um-s1z2-tile.tif",
            10, '"abc"', "https://bucket.test",
        )
        self.assertEqual(row["source_volume_id"], "20260413113053")
        self.assertEqual(row["model_id"], "mrg20736_1um_s1z2")
        self.assertEqual(row["etag"], "abc")


if __name__ == "__main__":
    unittest.main()
