import unittest

from inksurf.review_results import validate_results


class ReviewResultsTests(unittest.TestCase):
    def test_complete_review_is_valid(self) -> None:
        queue = [{"candidate_id": "a"}, {"candidate_id": "b"}]
        payload = {"experiment_id": "e", "results": [
            {"candidate_id": "a", "response": "yes", "confidence": 3, "elapsed_seconds": 1.2},
            {"candidate_id": "b", "response": "no", "confidence": 4, "elapsed_seconds": 2.0},
        ]}
        self.assertEqual(validate_results(payload, queue, ["yes", "no"], "e"), [])

    def test_duplicate_and_incomplete_review_is_rejected(self) -> None:
        queue = [{"candidate_id": "a"}, {"candidate_id": "b"}]
        payload = {"experiment_id": "e", "results": [
            {"candidate_id": "a", "response": "yes", "confidence": 3, "elapsed_seconds": 1},
            {"candidate_id": "a", "response": "yes", "confidence": 3, "elapsed_seconds": 1},
        ]}
        self.assertTrue(validate_results(payload, queue, ["yes"], "e"))


if __name__ == "__main__":
    unittest.main()
