import unittest

import numpy as np

from inksurf.cross_model_support_audit import resample_support


class CrossModelSupportAuditTests(unittest.TestCase):
    def test_resample_support_orders_conservative_to_permissive(self):
        mask = np.array([[1, 0], [1, 1]], dtype=bool)
        conservative = resample_support(mask, (1, 1), "all")
        central = resample_support(mask, (1, 1), "center")
        permissive = resample_support(mask, (1, 1), "any")
        self.assertFalse(conservative[0, 0])
        self.assertTrue(central[0, 0])
        self.assertTrue(permissive[0, 0])

    def test_invalid_policy_fails(self):
        with self.assertRaises(ValueError):
            resample_support(np.ones((2, 2)), (1, 1), "majority")


if __name__ == "__main__":
    unittest.main()
