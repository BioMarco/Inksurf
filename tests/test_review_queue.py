import unittest

import numpy as np

from inksurf.review_queue import _html, blinded_order, preview_views


class ReviewQueueTests(unittest.TestCase):
    def test_order_is_deterministic_and_complete(self) -> None:
        values = ["a", "b", "c", "d"]
        self.assertEqual(blinded_order(values, 7), blinded_order(values, 7))
        self.assertEqual(set(blinded_order(values, 7)), set(values))

    def test_preview_views_separate_evidence_from_overlay(self) -> None:
        prediction = np.full((12, 12), 245, dtype=np.uint8)
        component = np.zeros((8, 8), dtype=np.uint8)
        component[1:7, 1:7] = 1
        skeleton = np.zeros_like(component)
        skeleton[4, 4] = 1
        views = preview_views(
            prediction,
            {"y0": 2, "y1": 10, "x0": 2, "x1": 10},
            component,
            skeleton,
            halo=1,
        )
        self.assertEqual(set(views), {"raw", "enhanced", "mask", "overlay"})
        self.assertTrue(all(view.shape == (10, 10, 3) for view in views.values()))
        # The raw evidence is not contaminated by magenta or cyan overlays.
        self.assertFalse(np.any(np.all(views["raw"] == [225, 42, 92], axis=2)))
        self.assertTrue(np.any(np.all(views["mask"] == [225, 42, 92], axis=2)))
        self.assertTrue(np.any(np.all(views["mask"] == [0, 235, 255], axis=2)))

    def test_html_contains_guided_blind_review_and_local_resume(self) -> None:
        queue = [{"blind_id": "B001", "candidate_id": "c1", "previews": {
            "raw": "r.png", "enhanced": "e.png", "mask": "m.png", "overlay": "o.png",
        }}]
        html = _html(
            queue,
            ["plausible_structure", "imaging_or_model_artifact", "no_coherent_signal", "uncertain"],
            "experiment-v2",
        )
        self.assertIn("Tre domande guida", html)
        self.assertIn("localStorage", html)
        self.assertIn("Il rango, lo score e le label sono nascosti", html)
        self.assertNotIn("candidate rank", html.lower())


if __name__ == "__main__":
    unittest.main()
