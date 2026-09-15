import unittest

from inksurf.fragment_volume_download import select_layers


class FragmentVolumeDownloadTests(unittest.TestCase):
    def test_exact_layer_selection_and_budget(self) -> None:
        config = {
            "regime": "DEV",
            "fragment": "train/3",
            "surface_volume_layers_inclusive": [24, 25],
            "surface_volume_file_count": 2,
            "expected_bytes": 30,
            "max_download_bytes": 30,
        }
        manifest = {"files": [
            {"name": "train/3/surface_volume/24.tif", "bytes": 10},
            {"name": "train/3/surface_volume/25.tif", "bytes": 20},
        ]}
        self.assertEqual(len(select_layers(config, manifest)), 2)

    def test_rejects_non_dev(self) -> None:
        with self.assertRaises(ValueError):
            select_layers({"regime": "VALIDATION"}, {"files": []})


if __name__ == "__main__":
    unittest.main()
