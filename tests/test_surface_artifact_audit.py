import unittest

from inksurf.surface_artifact_audit import _http_url, validate_config


class SurfaceArtifactAuditTests(unittest.TestCase):
    def test_s3_url_is_converted_without_changing_key(self):
        value = _http_url("s3://vesuvius-challenge-open-data/a/b.zarr/")
        self.assertEqual(
            value,
            "https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/a/b.zarr/",
        )

    def test_non_dev_fails_closed(self):
        config = {
            "schema_version": "inksurf-surface-artifact-audit/1.0",
            "track": "A", "regime": "VALIDATION", "max_bytes_per_object": 1,
        }
        with self.assertRaises(ValueError):
            validate_config(config)


if __name__ == "__main__":
    unittest.main()
