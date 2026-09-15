import unittest
import numpy as np
from inksurf.cross_scan_render_plan import bilinear

class CrossScanRenderPlanTests(unittest.TestCase):
    def test_bilinear_plane(self):
        r,c=np.mgrid[:4,:5]; a=(2*r+3*c).astype(float)
        rows=np.array([0.5,2.25]); cols=np.array([1.5,3.0])
        expected=2*rows[:,None]+3*cols[None,:]
        np.testing.assert_allclose(bilinear(a,rows,cols),expected)
