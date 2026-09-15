import tempfile
import unittest
from pathlib import Path

from inksurf.bounded_http_download import report_destination, validate_manifest


class BoundedHttpDownloadTests(unittest.TestCase):
    def test_budget_and_host_are_enforced(self):
        manifest = {
            "schema_version": "inksurf-bounded-http-download/1.0",
            "track": "A", "regime": "DEV", "allowed_hosts": ["example.test"],
            "max_total_bytes": 10,
            "files": [{"url": "https://example.test/a", "destination": "a", "size_bytes": 11}],
        }
        with self.assertRaises(RuntimeError):
            validate_manifest(manifest)
        manifest["max_total_bytes"] = 20
        manifest["files"][0]["url"] = "https://wrong.test/a"
        with self.assertRaises(ValueError):
            validate_manifest(manifest)

    def test_validation_is_rejected(self):
        manifest = {
            "schema_version": "inksurf-bounded-http-download/1.0",
            "track": "A", "regime": "VALIDATION", "allowed_hosts": ["example.test"],
            "max_total_bytes": 1,
            "files": [{"url": "https://example.test/a", "destination": "a", "size_bytes": 1}],
        }
        with self.assertRaises(ValueError):
            validate_manifest(manifest)

    def test_portable_destination_is_relative_to_project_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "data" / "chunk.bin"
            self.assertEqual(report_destination(root, destination, True), "data/chunk.bin")


if __name__ == "__main__":
    unittest.main()
