import unittest

from inksurf.benchmark_preflight import RemoteFile, build_manifest, validate_config


def config():
    return {
        "experiment_id": "test",
        "bucket_id": "owner/bucket",
        "dataset_url": "https://example.invalid",
        "annotation_semantics": {"warning": "not absolute ground truth"},
        "split_policy": {"unit": "surface"},
        "evaluation": {"primary_unit": "region"},
        "surfaces": [
            {
                "key": "dev",
                "scroll_id": "a",
                "regime": "DEV",
                "prefix": "ink/a/dev",
                "files": {"prediction": "p.tif", "ink_labels": "l.tif", "supervision_mask": "m.tif", "x": "x.tif"},
            },
            {
                "key": "external",
                "scroll_id": "b",
                "regime": "VALIDATION",
                "external_domain": True,
                "prefix": "ink/b/val",
                "files": {"prediction": "p.tif", "ink_labels": "l.tif", "supervision_mask": "m.tif"},
            },
        ],
    }


class BenchmarkPreflightTests(unittest.TestCase):
    def test_manifest_budget_and_stages(self):
        files = {
            "ink/a/dev": [RemoteFile(f"ink/a/dev/{name}", size, name) for name, size in [("p.tif", 10), ("l.tif", 2), ("m.tif", 3), ("x.tif", 7)]],
            "ink/b/val": [RemoteFile(f"ink/b/val/{name}", size, name) for name, size in [("p.tif", 20), ("l.tif", 4), ("m.tif", 5)]],
        }
        manifest = build_manifest(config(), lister=lambda _bucket, prefix: files[prefix])
        self.assertEqual(manifest["budget"]["a1_dev_bytes"], 15)
        self.assertEqual(manifest["budget"]["a1_validation_locked_bytes"], 29)
        self.assertEqual(manifest["surfaces"]["dev"]["a2_geometry_bytes"], 7)
        self.assertEqual(manifest["status"], "metadata_verified_download_not_started")
        self.assertEqual(len(manifest["snapshot_sha256"]), 64)

    def test_missing_file_fails_closed(self):
        with self.assertRaises(RuntimeError):
            build_manifest(config(), lister=lambda _bucket, _prefix: [])

    def test_nested_prediction_uses_parent_listing(self):
        cfg = config()
        cfg["surfaces"][0]["files"]["prediction"] = "preds/p.tif"
        seen = []

        def lister(_bucket, prefix):
            seen.append(prefix)
            if prefix == "ink/a/dev/preds":
                return [RemoteFile("ink/a/dev/preds/p.tif", 10, "p")]
            direct = {
                "ink/a/dev": [("l.tif", 2), ("m.tif", 3), ("x.tif", 7)],
                "ink/b/val": [("p.tif", 20), ("l.tif", 4), ("m.tif", 5)],
            }
            return [RemoteFile(f"{prefix}/{name}", size, name) for name, size in direct.get(prefix, [])]

        build_manifest(cfg, lister=lister)
        self.assertIn("ink/a/dev/preds", seen)

    def test_external_domain_must_be_validation(self):
        bad = config()
        bad["surfaces"][1]["regime"] = "DEV"
        with self.assertRaises(ValueError):
            validate_config(bad)


if __name__ == "__main__":
    unittest.main()
