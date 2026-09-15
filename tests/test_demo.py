import tempfile
import unittest
from pathlib import Path

from inksurf.demo import run


class DemoTests(unittest.TestCase):
    def test_correlated_single_group_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            report = run(Path(directory))
            self.assertEqual(report["independent_group_count"], 2)
            self.assertEqual(report["accepted_artifact_pixels"], 0)
            self.assertEqual(report["precision"], 1.0)
            self.assertEqual(report["recall"], 1.0)
            self.assertTrue((Path(directory) / "maps.npz").exists())
            self.assertTrue((Path(directory) / "report.json").exists())


if __name__ == "__main__":
    unittest.main()
