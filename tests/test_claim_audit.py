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
            independence = root / "independence.json"
            independence.write_text(json.dumps({
                "schema_version": "inksurf-independence-audit/1.0",
                "effective_group_count": 2,
                "independence_gate_passed": True,
                "subject": {"sha256": digest},
            }), encoding="utf-8")
            independence_digest = hashlib.sha256(independence.read_bytes()).hexdigest()
            base = {
                "evidence_id": "held-out",
                "artifact": "receipt.json",
                "sha256": digest,
                "expected_schema": "example/1.0",
                "role": "locked_validation",
                "independent_groups": 2,
                "independence_audit": {
                    "artifact": "independence.json",
                    "sha256": independence_digest,
                },
                "ground_truth_independent": True,
                "permitted_claim": "confirmation",
            }
            self.assertTrue(audit_entry(root, base)["confirmation_eligible"])

    def test_group_claim_without_audit_is_capped_at_one(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "receipt.json"
            artifact.write_text(json.dumps({
                "schema_version": "example/1.0", "regime": "VALIDATION",
                "geometry_tier": "G2", "status": "GO", "go_checks": {"a": True},
            }), encoding="utf-8")
            entry = audit_entry(root, {
                "evidence_id": "unverified-groups", "artifact": "receipt.json",
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "expected_schema": "example/1.0", "role": "locked_validation",
                "independent_groups": 3, "ground_truth_independent": True,
                "permitted_claim": "confirmation",
            })
            self.assertEqual(entry["independent_groups"], 1)
            self.assertEqual(entry["independence_verification"]["status"], "unverified")
            self.assertFalse(entry["confirmation_eligible"])

    def test_independence_audit_must_bind_to_evidence_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "receipt.json"
            artifact.write_text(json.dumps({
                "schema_version": "example/1.0", "regime": "VALIDATION",
                "geometry_tier": "G2", "go_checks": {"a": True},
            }), encoding="utf-8")
            audit = root / "independence.json"
            audit.write_text(json.dumps({
                "schema_version": "inksurf-independence-audit/1.0",
                "effective_group_count": 2, "independence_gate_passed": True,
                "subject": {"sha256": "0" * 64},
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not bound"):
                audit_entry(root, {
                    "evidence_id": "wrong-subject", "artifact": "receipt.json",
                    "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    "expected_schema": "example/1.0", "role": "locked_validation",
                    "independent_groups": 2,
                    "independence_audit": {
                        "artifact": "independence.json",
                        "sha256": hashlib.sha256(audit.read_bytes()).hexdigest(),
                    },
                    "ground_truth_independent": True, "permitted_claim": "none",
                })

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
