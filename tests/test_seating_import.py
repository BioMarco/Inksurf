import unittest

from inksurf.seating_import import screen_rows


def _config():
    return {
        "schema_version": "inksurf-seating-import/1.0", "experiment_id": "test",
        "track": "A", "regime": "DEV",
        "source": {"url": "x", "sha256": "0", "max_bytes": 1},
        "gate": {"minimum_score": 15, "minimum_coverage": 0.8, "maximum_voxel_um": 4},
    }


class SeatingImportTests(unittest.TestCase):
    def test_distinct_passing_acquisitions_make_one_pair(self):
        base = {"scroll": "s", "segment": "x", "mesh": "m", "score": 16, "coverage": 0.9}
        rows = [
            {**base, "volume": "111-2.400um-x-78keV-masked.zarr"},
            {**base, "volume": "222-2.400um-x-78keV-masked.zarr"},
        ]
        report, pairs = screen_rows(_config(), rows)
        self.assertEqual(report["status"], "go_external_pair_requires_reproduction")
        self.assertEqual(len(pairs), 1)
        self.assertTrue(pairs[0]["pair_passes_gate"])

    def test_correlated_same_acquisition_is_not_a_pair(self):
        base = {"scroll": "s", "segment": "x", "mesh": "m", "score": 16, "coverage": 0.9}
        rows = [
            {**base, "volume": "111-2.400um-x-78keV-masked.zarr"},
            {**base, "volume": "111-2.400um-y-78keV-masked.zarr"},
        ]
        report, pairs = screen_rows(_config(), rows)
        self.assertEqual(report["status"], "no_go_no_strict_cross_scan_pair")
        self.assertFalse(pairs)

    def test_volume_without_beamline_field_is_supported(self):
        base = {"scroll": "s", "segment": "x", "mesh": "m", "score": 16, "coverage": 0.9}
        rows = [
            {**base, "volume": "111-2.400um-78keV-masked.zarr"},
            {**base, "volume": "222-2.400um-78keV-masked.zarr"},
        ]
        _, pairs = screen_rows(_config(), rows)
        self.assertEqual(len(pairs), 1)


if __name__ == "__main__":
    unittest.main()
