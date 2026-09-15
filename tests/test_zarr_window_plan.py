import unittest

from inksurf.zarr_window_plan import plan_window


class ZarrWindowPlanTests(unittest.TestCase):
    def test_window_chunks_and_edge_bytes(self):
        rows = plan_window([5, 5, 5], [3, 3, 3], [2, 2, 2], [3, 3, 3])
        self.assertEqual(len(rows), 8)
        self.assertEqual(sum(row["raw_bytes"] for row in rows), 125)

    def test_out_of_bounds_rejected(self):
        with self.assertRaises(ValueError):
            plan_window([5, 5, 5], [3, 3, 3], [4, 4, 4], [2, 2, 2])


if __name__ == "__main__": unittest.main()
