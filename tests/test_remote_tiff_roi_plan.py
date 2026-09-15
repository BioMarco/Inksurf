import unittest

from inksurf.remote_tiff_roi_plan import map_bounds, required_tile_indices


class RemoteTiffRoiPlanTests(unittest.TestCase):
    def test_normalized_canvas_mapping_uses_outer_rounding(self):
        self.assertEqual(map_bounds((10, 20, 30, 40), (100, 100), (150, 200)), (15, 30, 60, 80))

    def test_tiles_cover_boundary_crossing_roi(self):
        indices = required_tile_indices((900, 1100, 900, 1100), (2048, 2048), (1024, 1024))
        self.assertEqual(indices, {0, 1, 2, 3})

    def test_out_of_bounds_fails(self):
        with self.assertRaises(ValueError):
            required_tile_indices((0, 3000, 0, 1), (2048, 2048), (1024, 1024))


if __name__ == "__main__":
    unittest.main()
