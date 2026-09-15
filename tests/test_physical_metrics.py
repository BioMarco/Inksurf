import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from inksurf.physical_metrics import false_positive_burden, run


class PhysicalMetricsTests(unittest.TestCase):
    def test_counts_area_and_four_connected_components(self):
        accepted = np.array([[1, 1, 0], [0, 0, 0], [0, 0, 1]], dtype=bool)
        reference = np.zeros((3, 3), dtype=bool)
        valid = np.ones((3, 3), dtype=bool)
        result = false_positive_burden(
            accepted, reference, valid, 1_000_000.0,
            minimum_component_area_mm2=1.5,
        )
        self.assertEqual(result["false_positive_components_all"], 2)
        self.assertEqual(result["false_positive_components_retained"], 1)
        self.assertAlmostEqual(result["evaluated_negative_area_cm2"], 0.09)
        self.assertAlmostEqual(result["false_positive_area_cm2"], 0.03)

    def test_variable_pixel_area_is_used(self):
        accepted = np.array([[1, 0]], dtype=bool)
        reference = np.zeros((1, 2), dtype=bool)
        valid = np.ones((1, 2), dtype=bool)
        result = false_positive_burden(
            accepted, reference, valid, np.array([[2.0, 8.0]]),
            minimum_component_area_mm2=0.0,
        )
        self.assertAlmostEqual(result["false_positive_area_fraction"], 0.2)

    def test_reference_positives_are_not_negative_area(self):
        accepted = np.ones((1, 2), dtype=bool)
        reference = np.array([[1, 0]], dtype=bool)
        valid = np.ones((1, 2), dtype=bool)
        result = false_positive_burden(
            accepted, reference, valid, 1.0, minimum_component_area_mm2=0.0
        )
        self.assertEqual(result["evaluated_negative_pixels"], 1)
        self.assertEqual(result["false_positive_pixels"], 1)

    def test_invalid_physical_area_fails_closed(self):
        with self.assertRaises(ValueError):
            false_positive_burden(
                np.ones((1, 1)), np.zeros((1, 1)), np.ones((1, 1)), 0.0,
                minimum_component_area_mm2=0.0,
            )

    def test_cli_rejects_unverified_geometry_tier(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({
                "schema_version": "inksurf-physical-fp-audit/1.0",
                "track": "A", "regime": "DEV", "geometry_tier": "G1",
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "G2 or G3"):
                run(path)


if __name__ == "__main__":
    unittest.main()
