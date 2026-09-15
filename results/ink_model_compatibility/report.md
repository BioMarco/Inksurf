# Canonical ink-model compatibility

**Date:** 2026-09-15

**Track / regime / geometry:** Track A / DEV / G1

**Classification:** PASS for pipeline compatibility; not an ink discovery.

The frozen PHerc0139 window was evaluated against its published canonical ink
map. Inputs and code were pinned by SHA256 and the official `ScrollPrize/villa`
loader was fixed at commit `76370e1a6908f0bc2eb7f92bc0397336ecbe3d96`.

Protocol: surface window `Z,Y,X = 109,512,512`, source origin
`0,24576,18432`; layers `[24,86)`; no reversal; clipping at 200; 256-pixel
tiles, stride 128, Hann blending; evaluation on the central 256 x 256 pixels.
The acceptance criterion `Pearson r > 0.5` was frozen before execution.

Verified Kaggle GPU result:

- device: Tesla T4;
- tiles: 9; evaluation pixels: 65,536;
- Pearson `r = 0.9897446957`;
- Spearman `rho = 0.9886468212`;
- elapsed end-to-end time: 42.864 s;
- status: **PASS**.

Artifacts:

- `kaggle_v2/compatibility_report.json`, SHA256
  `4b27a6e050239fd1bdb78e71fc77d5a34a197b17dae50a66d8cfbb9e76d0b60f`;
- `kaggle_v2/local_prediction.npz`, SHA256
  `d1a7eb8da47e807322088c47e5845ef3e3a36633c436317e6068a375eb5f6db4`;
- `kaggle_v2/inksurf-canonical-compatibility.log`, SHA256
  `94507cece65629fd06b75c860db89f5215798734f6d755ef859e259f672f4e82`.

The first Kaggle attempt failed before inference because its runtime lacked
`zarr`; version 2 replaced random-access TIFF reading with an in-memory read
without changing scientific parameters. A local CPU attempt ran for more than
four hours and ended without atomic outputs, so it is non-interpretable.
Multi-tile CPU execution is now blocked by default.

Interpretation: InkSurf reproduces the published model output closely enough to
trust the integration path. This does not establish that any predicted region
is real ink, nor that model errors are independent across acquisitions. The
next informative test is a G2 cross-acquisition render on the already verified
PHerc0139 seating crop, followed by independent inference and a preregistered
consensus/disagreement comparison.
