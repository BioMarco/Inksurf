import unittest

import numpy as np

from inksurf.structural_features import component_score, structural_map


class StructuralFeatureTests(unittest.TestCase):
    def test_structural_map_is_finite_and_bounded(self):
        image = np.zeros((64, 64), dtype=np.uint8)
        image[32, 8:56] = 255
        result = structural_map(
            image,
            intensity_low=0,
            intensity_high=255,
            gradient_sigma=1,
            tensor_sigma=2,
            contrast_sigma=4,
        )
        self.assertTrue(np.isfinite(result).all())
        self.assertGreaterEqual(float(result.min()), 0.0)
        self.assertLessEqual(float(result.max()), 1.0)

    def test_component_score_prefers_continuous_line_over_dot(self):
        valid = np.ones((64, 64), dtype=bool)
        line = np.zeros((64, 64), dtype=np.uint8)
        line[32, 8:56] = 255
        dot = np.zeros((64, 64), dtype=np.uint8)
        dot[32:35, 32:35] = 255
        line_score = structural_map(line, intensity_low=0, intensity_high=255, gradient_sigma=1, tensor_sigma=2, contrast_sigma=4)
        dot_score = structural_map(dot, intensity_low=0, intensity_high=255, gradient_sigma=1, tensor_sigma=2, contrast_sigma=4)
        line_best, _, _ = component_score(line_score, line, valid, threshold=200, min_component_pixels=1, closing_radius=0, min_skeleton_pixels=2)
        dot_best, _, _ = component_score(dot_score, dot, valid, threshold=200, min_component_pixels=1, closing_radius=0, min_skeleton_pixels=2)
        self.assertGreater(line_best, dot_best)


if __name__ == "__main__":
    unittest.main()
