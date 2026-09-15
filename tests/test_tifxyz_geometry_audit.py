import unittest

import numpy as np

from inksurf.tifxyz_geometry_audit import audit_geometry_arrays


class TifxyzGeometryAuditTests(unittest.TestCase):
    def test_planar_grid_passes_local_checks(self) -> None:
        v, u = np.mgrid[:5, :6]
        x = (u * 20).astype(np.float32)
        y = (v * 20).astype(np.float32)
        z = np.full_like(x, 10)
        report, valid = audit_geometry_arrays(
            x, y, z, expected_spacing=20, spacing_tolerance=0.15, maximum_jump_factor=3,
        )
        self.assertTrue(valid.all())
        self.assertEqual(report["valid_components_8_connected"], 1)
        self.assertEqual(report["topology"]["adjacent_normal_flips"], 0)
        self.assertEqual(report["continuity"]["u"]["abrupt_jumps"], 0)

    def test_partial_sentinel_is_rejected_as_valid(self) -> None:
        v, u = np.mgrid[:3, :3]
        x, y, z = u.astype(float), v.astype(float), np.ones((3, 3))
        x[1, 1] = -1
        report, valid = audit_geometry_arrays(
            x, y, z, expected_spacing=1, spacing_tolerance=0.2, maximum_jump_factor=3,
        )
        self.assertEqual(report["partial_sentinel_vertices"], 1)
        self.assertFalse(valid[1, 1])


if __name__ == "__main__":
    unittest.main()
