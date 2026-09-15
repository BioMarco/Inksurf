# Surface Artifact Phase 0 — bounded Zarr metadata audit

**Run:** `inksurf-surface-artifact-phase0-20260914`

**Track/regime:** Track A / DEV

**Result:** `conditional_go_transform_required`

The audit read only `.zattrs` and `0/.zarray` for four surface-volume Zarr
stores: 8 objects and 14,562 bytes total. It read zero volumetric chunks and no
VALIDATION or DISCOVERY data.

## Verified observations

Both same-label pairs use explicit `Z,Y,X` axes and have very similar physical
depth and X extents after applying the level-0 OME-Zarr scale. Their Y extents
are materially different, consistent with unequal or partial coverage:

| label | depth extent ratio | Y extent ratio | X extent ratio |
|---|---:|---:|---:|
| `w104-106` | 0.957568 | 0.656253 | 0.979486 |
| `w122-123` | 0.957568 | 0.611337 | 0.996543 |

Every store declares translation `[0,0,0]`. These are local canvas coordinates,
not a cross-scan transform. No global transform was found in the inspected
metadata.

## Interpretation

Partial physical overlap is plausible, but pixel correspondence is unverified.
It would be methodologically invalid to rescale the two canvases and call them
registered. The next stage needs a versioned transform plus an objective seating
or landmark-residual test before any consensus metric is run.

## Ecosystem constraint

The current community repository `axiosdevs/herculaneum-scroll-tools` already
contains cross-scan registration and a quantitative surface-seating audit. At
commit `c836a52c3dd8e555269c0f8289c40260c7c36e1d`, its archived Paris 4 measurements
also show that a surface can appear to overlap yet fail to seat in another scan.
InkSurf must integrate or independently verify that interface; it must not build
a duplicate registration subsystem without a measured advantage.

Machine-readable artifacts: `report.json` and `pair_geometry.csv`.
