import unittest

from inksurf.validation_partition_gate import decide


class ValidationPartitionGateTests(unittest.TestCase):
    def setUp(self):
        self.protocol = {"go_criteria": {
            "minimum_eligible_ink_pixels": 100,
            "minimum_eligible_negative_pixels": 1000,
            "minimum_chunks_with_both_classes": 2,
        }}

    def test_fails_when_positive_diversity_upper_bound_is_too_small(self):
        audit = {
            "total_validation_pixels": 3000, "total_ink_pixels_in_validation": 200,
            "chunks": [
                {"validation_pixels": 1000, "ink_pixels_in_validation": 200},
                {"validation_pixels": 2000, "ink_pixels_in_validation": 0},
            ],
        }
        self.assertEqual(decide(audit, self.protocol)["status"], "NO_GO_LABEL_DIVERSITY_UPPER_BOUND")

    def test_continues_when_all_upper_bounds_pass(self):
        audit = {
            "total_validation_pixels": 3000, "total_ink_pixels_in_validation": 300,
            "chunks": [
                {"validation_pixels": 1000, "ink_pixels_in_validation": 100},
                {"validation_pixels": 2000, "ink_pixels_in_validation": 200},
            ],
        }
        self.assertEqual(decide(audit, self.protocol)["status"], "CONTINUE_GEOMETRY_GATES")


if __name__ == "__main__":
    unittest.main()
