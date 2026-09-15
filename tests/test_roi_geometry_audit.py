import unittest

import numpy as np

from inksurf.roi_geometry_audit import evaluation_geometry


class RoiGeometryAuditTests(unittest.TestCase):
    def test_planar_grid_produces_physical_area(self):
        rows, columns = np.mgrid[:4, :4]
        x = columns.astype(float) * 20
        y = rows.astype(float) * 20
        z = np.ones((4, 4))
        report, area = evaluation_geometry(
            x, y, z, np.ones((5, 5), dtype=bool), chunk_yx=(0, 0),
            chunk_pixels=5, grid_step_pixels=5, voxel_um=2.0,
        )
        self.assertTrue(report["passes"])
        self.assertAlmostEqual(report["pixel_area_um2_quantiles"]["p50"], 64.0)
        self.assertTrue(np.all(area == 64.0))

    def test_invalid_quad_under_evaluation_fails(self):
        rows, columns = np.mgrid[:3, :3]
        x, y, z = columns.astype(float), rows.astype(float), np.ones((3, 3))
        z[0, 0] = -1
        report, _ = evaluation_geometry(
            x, y, z, np.ones((1, 1), dtype=bool), chunk_yx=(0, 0),
            chunk_pixels=1, grid_step_pixels=1, voxel_um=1.0,
        )
        self.assertFalse(report["passes"])
        self.assertEqual(report["unsupported_pixels"], 1)


if __name__ == "__main__":
    unittest.main()
