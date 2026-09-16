import unittest

from inksurf.cross_model_candidate_decision import decide


class CrossModelCandidateDecisionTests(unittest.TestCase):
    def test_registration_failure_precedes_support(self):
        registration = {"status": "NO_GO_UV_CORRESPONDENCE"}
        support = {"totals": {"any": {"eligible_pixels": 100, "eligible_ink_pixels": 50, "eligible_negative_pixels": 50}}}
        self.assertEqual(decide(registration, support), "NO_GO_REGISTRATION")

    def test_zero_permissive_support_fails_closed(self):
        registration = {"status": "GO_UV_CORRESPONDENCE"}
        support = {"totals": {"any": {"eligible_pixels": 0, "eligible_ink_pixels": 0, "eligible_negative_pixels": 0}}}
        self.assertEqual(decide(registration, support), "NO_GO_NO_COMMON_GEOMETRY_SUPPORT")

    def test_single_class_support_fails_closed(self):
        registration = {"status": "GO_UV_CORRESPONDENCE"}
        support = {"totals": {"any": {"eligible_pixels": 10, "eligible_ink_pixels": 0, "eligible_negative_pixels": 10}}}
        self.assertEqual(decide(registration, support), "NO_GO_SINGLE_CLASS_COMMON_SUPPORT")

    def test_sufficient_support_allows_score_comparison(self):
        registration = {"status": "GO_UV_CORRESPONDENCE"}
        support = {"totals": {"any": {"eligible_pixels": 10, "eligible_ink_pixels": 5, "eligible_negative_pixels": 5}}}
        self.assertEqual(decide(registration, support), "GO_SCORE_COMPARISON")


if __name__ == "__main__":
    unittest.main()
