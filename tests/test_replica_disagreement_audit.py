import unittest

import numpy as np

from inksurf.replica_disagreement_audit import disagreement_summary


class ReplicaDisagreementAuditTests(unittest.TestCase):
    def test_detects_signal_bearing_disagreement(self):
        labels = np.array([[False, False, True, True]])
        mask = np.ones_like(labels, dtype=bool)
        predictions = np.array([
            [[0.1, 0.2, 0.2, 0.1]],
            [[0.1, 0.2, 0.8, 0.9]],
        ])
        report = disagreement_summary(predictions, labels, mask, bins=2)
        self.assertEqual(report["pixels"], 4)
        self.assertGreater(report["disagreement_ap"], report["positive_prevalence"])
        self.assertGreater(report["mean_disagreement_positive"], report["mean_disagreement_negative"])

    def test_rejects_single_class_labels(self):
        predictions = np.zeros((2, 1, 4), dtype=np.float32)
        labels = np.zeros((1, 4), dtype=bool)
        with self.assertRaises(ValueError):
            disagreement_summary(predictions, labels, np.ones_like(labels), bins=2)


if __name__ == "__main__":
    unittest.main()
