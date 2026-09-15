import unittest

from inksurf.candidate_package import validate_package


class CandidatePackageTests(unittest.TestCase):
    def test_valid_minimum_package(self) -> None:
        package = {
            "schema_version": "inksurf-candidate-package/1.0", "experiment_id": "x",
            "track": "A", "regime": "DEV", "geometry_tier": "G0", "surface_id": "s",
            "coordinate_frame": {"axes": "Y,X"}, "ranking": {}, "provenance": [],
            "submission_readiness": {},
            "candidates": [{"candidate_id": "c", "rank": 1,
                            "bounds_yx": {"y0": 0, "y1": 2, "x0": 3, "x1": 5}}],
        }
        self.assertEqual(validate_package(package), [])

    def test_rejects_implicit_axes_and_bad_bounds(self) -> None:
        package = {
            "schema_version": "x", "experiment_id": "x", "track": "A", "regime": "DEV",
            "geometry_tier": "G0", "surface_id": "s", "coordinate_frame": {},
            "ranking": {}, "provenance": [], "submission_readiness": {},
            "candidates": [{"candidate_id": "c", "rank": 1,
                            "bounds_yx": {"y0": 2, "y1": 2, "x0": 0, "x1": 1}}],
        }
        errors = validate_package(package)
        self.assertEqual(len(errors), 2)

    def test_g1_requires_uv_and_xyz_bounds(self) -> None:
        package = {
            "schema_version": "x", "experiment_id": "x", "track": "A", "regime": "DEV",
            "geometry_tier": "G1", "surface_id": "s", "coordinate_frame": {"axes": "X,Y,Z"},
            "ranking": {}, "provenance": [], "submission_readiness": {},
            "candidates": [{"candidate_id": "c", "rank": 1,
                            "bounds_yx": {"y0": 0, "y1": 1, "x0": 0, "x1": 1}}],
        }
        errors = validate_package(package)
        self.assertEqual(len(errors), 2)


if __name__ == "__main__":
    unittest.main()
