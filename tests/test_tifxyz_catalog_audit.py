import unittest

import numpy as np

from inksurf.tifxyz_catalog_audit import bbox_volume_xyz, point_bbox_distance_xyz, s3_to_https, tifxyz_meta_url


class TifxyzCatalogAuditTests(unittest.TestCase):
    def test_s3_conversion_and_url(self):
        folder = "s3://bucket/a/segment/"
        expected = "https://bucket.s3.amazonaws.com/a/segment/mesh/123-on-vol-2.4um.tifxyz/meta.json"
        self.assertEqual(tifxyz_meta_url(folder, "123", "vol", 2.4), expected)

    def test_bbox_distance(self):
        bbox = [[0, 0, 0], [10, 10, 10]]
        self.assertEqual(point_bbox_distance_xyz(np.array([5, 5, 5]), bbox), 0.0)
        self.assertAlmostEqual(point_bbox_distance_xyz(np.array([13, 14, 5]), bbox), 5.0)
        self.assertEqual(bbox_volume_xyz(bbox), 1000.0)

    def test_bbox_validation(self):
        with self.assertRaises(ValueError):
            point_bbox_distance_xyz(np.zeros(3), [[1, 0, 0], [0, 1, 1]])

    def test_null_voxel_size_is_not_numeric(self):
        items = [{"um": None}, {"um": 2.4}]
        selected = [item for item in items if item.get("um") is not None and float(item["um"]) == 2.4]
        self.assertEqual(selected, [{"um": 2.4}])


if __name__ == "__main__":
    unittest.main()
