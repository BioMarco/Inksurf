import unittest
import tempfile
import zipfile
from pathlib import Path

from inksurf.fragment_download import _resolve_downloaded, select_files


class FragmentDownloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = {
            "files": [
                {"name": "train/3/mask.png", "bytes": 10},
                {"name": "train/3/surface_volume/00.tif", "bytes": 100},
                {"name": "train/1/mask.png", "bytes": 20},
            ]
        }
        self.config = {
            "regime": "DEV",
            "fragment": "train/3",
            "files": ["train/3/mask.png"],
            "max_bytes": 16,
        }

    def test_selects_bounded_dev_asset(self) -> None:
        self.assertEqual(select_files(self.config, self.manifest)[0]["bytes"], 10)

    def test_rejects_validation_regime(self) -> None:
        self.config["regime"] = "VALIDATION"
        with self.assertRaises(ValueError):
            select_files(self.config, self.manifest)

    def test_rejects_other_fragment(self) -> None:
        self.config["files"] = ["train/1/mask.png"]
        with self.assertRaises(ValueError):
            select_files(self.config, self.manifest)

    def test_rejects_volume_layer(self) -> None:
        self.config["files"] = ["train/3/surface_volume/00.tif"]
        self.config["max_bytes"] = 100
        with self.assertRaises(ValueError):
            select_files(self.config, self.manifest)

    def test_resolves_single_file_kaggle_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "ir.png.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("ir.png", b"pixels")
            resolved = _resolve_downloaded(Path(directory), "train/3/ir.png", 6)
            self.assertEqual(resolved.read_bytes(), b"pixels")

    def test_rejects_unexpected_zip_members(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "ir.png.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("ir.png", b"pixels")
                archive.writestr("extra.txt", b"unexpected")
            with self.assertRaises(RuntimeError):
                _resolve_downloaded(Path(directory), "train/3/ir.png", 6)


if __name__ == "__main__":
    unittest.main()
