import hashlib
import json
import unittest

from inksurf.evidence_preflight import CatalogDocument, audit_catalog, validate_config


def _config():
    payload = json.dumps({
        "updated": "test",
        "scrolls": [{
            "id": "known", "n_segments": 2, "n_inkSegments": 1, "n_predictions": 1,
            "hasSurfacePred": True, "hasInk3d": False,
            "stages": {"text": True},
            "scans": [
                {"id": "a", "px": 2.4, "energy": 78, "loc": "ESRF"},
                {"id": "b", "px": 7.9, "energy": 54, "loc": "DLS"},
            ],
            "inkSegments": [
                {"id": "s1", "label": "w1", "layers": "s3://x/volume-111.zarr/",
                 "full": "https://x/volume-333-model.tif"},
                {"id": "s2", "label": "w1", "layers": "s3://x/volume-222.zarr/",
                 "full": "https://x/volume-333-model-2.tif"},
            ],
        }],
    }, sort_keys=True).encode()
    return {
        "schema_version": "inksurf-evidence-preflight/1.0", "experiment_id": "test",
        "track": "A", "regime": "DEV", "development_targets": ["known"],
        "catalog": {"url": "https://example.invalid/catalog.json", "max_bytes": 10000,
                    "sha256": hashlib.sha256(payload).hexdigest()},
        "gate": {"minimum_scans": 2, "minimum_segments": 1, "minimum_ink_segments": 1,
                 "minimum_qualified_pairs": 1, "minimum_pair_dimensions": 1},
        "outputs": {"report_json": "x.json", "pairs_csv": "x.csv",
                    "artifact_pairs_csv": "artifacts.csv"},
    }, payload


class EvidencePreflightTests(unittest.TestCase):
    def test_ready_is_conditional_and_preserves_blockers(self):
        config, payload = _config()
        report, pairs, artifact_pairs = audit_catalog(
            config, CatalogDocument(payload, config["catalog"]["url"])
        )
        self.assertEqual(report["status"], "conditional_go_raw_evidence_only")
        self.assertEqual(report["metadata_ready_samples"], ["known"])
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["physical_independence_dimensions"], 3)
        self.assertEqual(len(artifact_pairs), 1)
        self.assertFalse(artifact_pairs[0]["distinct_ink_source_volumes"])
        self.assertEqual(report["independent_ink_output_pairs"], 0)
        self.assertEqual(report["downloaded_volumetric_bytes"], 0)
        self.assertTrue(report["blockers"])

    def test_hash_mismatch_fails_closed(self):
        config, payload = _config()
        config["catalog"]["sha256"] = "0" * 64
        with self.assertRaises(RuntimeError):
            audit_catalog(config, CatalogDocument(payload, config["catalog"]["url"]))

    def test_two_renders_on_one_segment_are_discovered_but_not_declared_independent(self):
        config, payload = _config()
        document = json.loads(payload)
        document["scrolls"][0]["inkSegments"][0]["renders"] = [
            {"targetVolume": "111", "url": "https://x/a.tif", "modelName": "a"},
            {"targetVolume": "222", "url": "https://x/b.tif", "modelName": "b"},
        ]
        updated = json.dumps(document, sort_keys=True).encode()
        config["catalog"]["sha256"] = hashlib.sha256(updated).hexdigest()
        report, _, pairs = audit_catalog(config, CatalogDocument(updated, config["catalog"]["url"]))
        render_pair = next(row for row in pairs if row["alignment_status"].startswith("same_segment"))
        self.assertTrue(render_pair["distinct_ink_source_volumes"])
        self.assertEqual(render_pair["model_a"], "a")
        self.assertEqual(report["distinct_source_ink_output_pairs"], 1)
        self.assertEqual(report["independent_ink_output_pairs"], 0)
        self.assertEqual(report["status"], "conditional_go_alignment_unverified")

    def test_validation_or_discovery_not_allowed_in_phase_zero(self):
        config, _ = _config()
        config["regime"] = "VALIDATION"
        with self.assertRaises(ValueError):
            validate_config(config)


if __name__ == "__main__":
    unittest.main()
