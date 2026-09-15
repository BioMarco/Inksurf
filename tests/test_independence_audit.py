import unittest

from inksurf.independence_audit import audit_independence


class IndependenceAuditTests(unittest.TestCase):
    def test_shared_training_data_merges_declared_groups(self):
        views = [
            {
                "view_id": "seed-a",
                "independence_group": "claimed-a",
                "provenance": {"acquisition_id": "scan-1", "model_family_id": "m", "training_data_id": "train"},
            },
            {
                "view_id": "seed-b",
                "independence_group": "claimed-b",
                "provenance": {"acquisition_id": "scan-1", "model_family_id": "m", "training_data_id": "train"},
            },
        ]
        report = audit_independence(views, ["acquisition_id", "model_family_id", "training_data_id"])
        self.assertEqual(report["declared_group_count"], 2)
        self.assertEqual(report["effective_group_count"], 1)
        self.assertFalse(report["independence_gate_passed"])

    def test_distinct_provenance_preserves_groups(self):
        views = [
            {
                "view_id": "a",
                "independence_group": "a",
                "provenance": {"acquisition_id": "scan-1", "model_family_id": "m1", "training_data_id": "t1"},
            },
            {
                "view_id": "b",
                "independence_group": "b",
                "provenance": {"acquisition_id": "scan-2", "model_family_id": "m2", "training_data_id": "t2"},
            },
        ]
        report = audit_independence(views, ["acquisition_id", "model_family_id", "training_data_id"])
        self.assertEqual(report["effective_group_count"], 2)
        self.assertTrue(report["independence_gate_passed"])

    def test_missing_provenance_fails_closed(self):
        views = [
            {"view_id": "a", "independence_group": "a", "provenance": {"acquisition_id": "one"}},
            {"view_id": "b", "independence_group": "b", "provenance": {"acquisition_id": "two"}},
        ]
        report = audit_independence(views, ["acquisition_id", "training_data_id"])
        self.assertEqual(report["effective_group_count"], 1)
        self.assertFalse(report["independence_gate_passed"])
        self.assertEqual(report["dependency_edges"][0]["reasons"][0]["reason"], "missing_provenance")

    def test_minimum_must_require_real_cross_group_evidence(self):
        views = [
            {"view_id": "a", "independence_group": "a", "provenance": {"source": "one"}},
            {"view_id": "b", "independence_group": "b", "provenance": {"source": "two"}},
        ]
        with self.assertRaises(ValueError):
            audit_independence(views, ["source"], minimum_effective_groups=1)


if __name__ == "__main__":
    unittest.main()
