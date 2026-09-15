# PHerc0139 bounded cross-scan seating reproduction

**Run:** `pherc0139-seating-reproduction-20260914`

**Track/regime:** Track A / DEV

**Result:** `GO` for bounded geometry; no ink claim.

## Frozen unit

- mesh: `20250108000000-on-20260319133554-2.403um.tifxyz`;
- crop: 417 x 417 mesh cells, approximately 20 x 20 mm;
- crop origin: row 329, column 295;
- valid geometry: 100%;
- deterministic sample: 50 points, seed 0;
- volume level: 2, axes `Z,Y,X`;
- normal probe: 59 offsets, span 60 level-2 voxels.

## I/O

- TIFXYZ: 22,662,510 bytes, SHA256 recorded in config;
- volume chunks: 226 objects, 473,956,352 bytes;
- total downloaded for this reproduction: 496,618,862 bytes;
- VALIDATION/DISCOVERY files: zero.

## Reproduced measurements

| acquisition | score | coverage | contrast | fitted gap L2 |
|---|---:|---:|---:|---:|
| `20250820105138` | 15.0200 | 0.940 | 15.9787 | 10 |
| `20260319133554` | 17.5400 | 0.800 | 21.9250 | 10 |

Both acquisitions meet the frozen score >=15 and coverage >=0.8 gate on this
crop. The corresponding third-party whole-mesh measurements were 14.96/0.880
and 17.41/0.725. The close agreement is evidence that the adapter reproduces
the external metric on the bounded unit.

## Interpretation and next gate

This verifies that the same mesh follows papyrus in both acquisitions closely
enough for a DEV comparison. It does not demonstrate ink, pixel registration
or statistical independence of model errors.

Next, render the same frozen surface crop from both acquisitions, apply one
pinned ink pipeline independently to each acquisition, align the resulting UV
maps without using ink labels, and compare best-single, naive fusion and
InkSurf consensus/disagreement on spatially separated known-text controls.
