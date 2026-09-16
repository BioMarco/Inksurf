import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from inksurf.evidence_consistency import _atomic_json, combine_evidence, validate_config


class EvidenceConsistencyTests(unittest.TestCase):
    def test_atomic_json_is_git_stable_lf_on_windows(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            _atomic_json(path, {"value": 1})
            self.assertNotIn(b"\r\n", path.read_bytes())

    def test_correlated_variants_cannot_inflate_independent_support(self):
        high = np.ones((2, 2), dtype=np.float32)
        low = np.zeros((2, 2), dtype=np.float32)
        result = combine_evidence(
            [high, high, low], ["model-a", "model-a", "model-b"],
            evidence_threshold=0.5, minimum_independent_groups=2,
            minimum_support_fraction=0.75, maximum_disagreement=1.0,
        )
        self.assertTrue(np.all(result["support_fraction"] == 0.5))
        self.assertFalse(result["accepted"].any())
        self.assertTrue(np.all(result["valid_independent_groups"] == 2))

    def test_agreement_and_disagreement_gate(self):
        first = np.array([[0.9, 0.9], [0.9, np.nan]], dtype=np.float32)
        second = np.array([[0.8, 0.2], [0.65, 0.9]], dtype=np.float32)
        result = combine_evidence(
            [first, second], ["scan-a", "scan-b"],
            evidence_threshold=0.6, minimum_independent_groups=2,
            minimum_support_fraction=1.0, maximum_disagreement=0.3,
        )
        np.testing.assert_array_equal(result["accepted"], [[True, False], [True, False]])
        self.assertEqual(result["valid_independent_groups"][1, 1], 1)

    def test_shape_mismatch_fails(self):
        with self.assertRaises(ValueError):
            combine_evidence(
                [np.zeros((2, 2)), np.zeros((2, 3))], ["a", "b"],
                evidence_threshold=0.5, minimum_independent_groups=2,
                minimum_support_fraction=0.5, maximum_disagreement=0.5,
            )

    def test_config_requires_two_independent_groups(self):
        config = {
            "schema_version": "inksurf-evidence-consistency/1.0", "regime": "DEV",
            "views": [
                {"view_id": "a", "independence_group": "same"},
                {"view_id": "b", "independence_group": "same"},
            ],
            "thresholds": {"evidence": 0.5, "minimum_support_fraction": 0.5,
                           "maximum_disagreement": 0.5, "minimum_independent_groups": 2},
        }
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_config_collapses_falsely_distinct_provenance_groups(self):
        config = {
            "schema_version": "inksurf-evidence-consistency/1.0", "regime": "DEV",
            "views": [
                {"view_id": "seed-a", "independence_group": "a",
                 "provenance": {"acquisition_id": "scan", "model_family_id": "model"}},
                {"view_id": "seed-b", "independence_group": "b",
                 "provenance": {"acquisition_id": "scan", "model_family_id": "model"}},
            ],
            "independence_policy": {
                "required_distinct_fields": ["acquisition_id", "model_family_id"]
            },
            "thresholds": {"evidence": 0.5, "minimum_support_fraction": 0.5,
                           "maximum_disagreement": 0.5, "minimum_independent_groups": 2},
        }
        with self.assertRaisesRegex(ValueError, "effective independent groups"):
            validate_config(config)


if __name__ == "__main__":
    unittest.main()
