import tempfile
import unittest
from pathlib import Path

from inksurf.benchmark_download import select_downloads, sha256_file


class BenchmarkDownloadTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "files": [
                {"regime": "DEV", "stage": "A1", "size_bytes": 10},
                {"regime": "DEV", "stage": "A2", "size_bytes": 4},
                {"regime": "VALIDATION", "stage": "A1", "size_bytes": 20},
            ]
        }

    def test_dev_selection_and_budget(self):
        rows = select_downloads(self.manifest, regime="DEV", stage="A1", max_bytes=10)
        self.assertEqual(len(rows), 1)
        with self.assertRaises(RuntimeError):
            select_downloads(self.manifest, regime="DEV", stage="A1", max_bytes=9)

    def test_validation_fails_closed(self):
        with self.assertRaises(PermissionError):
            select_downloads(self.manifest, regime="VALIDATION", stage="A1", max_bytes=100)
        rows = select_downloads(
            self.manifest, regime="VALIDATION", stage="A1", max_bytes=100, unlock_validation=True
        )
        self.assertEqual(len(rows), 1)

    def test_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x"
            path.write_bytes(b"abc")
            self.assertEqual(
                sha256_file(path),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            )


if __name__ == "__main__":
    unittest.main()
