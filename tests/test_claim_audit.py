import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from inksurf.claim_audit import audit_entry


class ClaimAuditTests(unittest.TestCase):
    def test_locked_receipt_needs_all_confirmation_conditions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "receipt.json"
            artifact.write_text(json.dumps({
                "schema_version": "example/1.0",
                "regime": "VALIDATION",
                "geometry_tier": "G2",
                "status": "GO",
                "go_checks": {"a": True, "b": True},
            }), encoding="utf-8")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            base = {
                "evidence_id": "held-out",
                "artifact": "receipt.json",
                "sha256": digest,
                "expected_schema": "example/1.0",
                "role": "locked_validation",
                "independent_groups": 2,
                "ground_truth_independent": True,
                "permitted_claim": "confirmation",
            }
            self.assertTrue(audit_entry(root, base)["confirmation_eligible"])
            base["independent_groups"] = 1
            self.assertFalse(audit_entry(root, base)["confirmation_eligible"])

    def test_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "receipt.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                audit_entry(root, {
                    "evidence_id": "bad",
                    "artifact": "receipt.json",
                    "sha256": "0" * 64,
                    "expected_schema": "example/1.0",
                    "role": "development",
                    "permitted_claim": "none",
                })


if __name__ == "__main__":
    unittest.main()
