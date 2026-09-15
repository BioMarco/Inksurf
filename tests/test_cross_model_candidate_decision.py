import unittest

from inksurf.cross_model_candidate_decision import decide


class CrossModelCandidateDecisionTests(unittest.TestCase):
    def test_registration_failure_precedes_support(self):
        registration = {"status": "NO_GO_UV_CORRESPONDENCE"}
        support = {"totals": {"any": {"eligible_pixels": 100}}, "center_supported_chunk_count": 5, "minimum_supported_chunks": 4}
        self.assertEqual(decide(registration, support), "NO_GO_REGISTRATION")

    def test_zero_permissive_support_fails_closed(self):
        registration = {"status": "GO_UV_CORRESPONDENCE"}
        support = {"totals": {"any": {"eligible_pixels": 0}}, "center_supported_chunk_count": 0, "minimum_supported_chunks": 4}
        self.assertEqual(decide(registration, support), "NO_GO_NO_LABELED_COMMON_SUPPORT")

    def test_sufficient_support_allows_score_comparison(self):
        registration = {"status": "GO_UV_CORRESPONDENCE"}
        support = {"totals": {"any": {"eligible_pixels": 10}}, "center_supported_chunk_count": 4, "minimum_supported_chunks": 4}
        self.assertEqual(decide(registration, support), "GO_SCORE_COMPARISON")


if __name__ == "__main__":
    unittest.main()
