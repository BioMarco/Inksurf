# Geometric Validation Extended - methodological audit

Date: 2026-09-10
Coordinate order: `Z,Y,X`
Verdict: **promising result, but still requires structural validation**.

## Evidence verified locally

- The feature table contains 990 rows: 500 GP and 490 CONTROL.
- All 500 GP centers reproduce exactly from `grand_prize_chunk_coords.npy`, using the documented 2023->2026 affine, chunk center `c*128+64`, and level conversion `/8` with rounding.
- All 490 CONTROL centers reproduce exactly from the CONTROL rows of `gp_vs_control.csv` via `source_index`.
- There are no duplicate centers and no duplicate `(target, source_index)` keys.
- The requested source filter is `surf_frac128` in `[0.20, 0.60)`. Source-patch medians are GP `0.40488` and CONTROL `0.40625`. Recomputed 64^3 geometric-patch medians are GP `0.39797` and CONTROL `0.41733`; these are different quantities.
- Strict matching contains 429 one-to-one pairs. Stored differences reproduce exactly; median absolute Surface difference is `0.00153`, maximum `0.00495`.
- Reported CV AUCs reproduce from the stored feature CSV and recovered script: Logistic random `0.8104`, Logistic spatial `0.8081`, nonlinear random `0.8197`, nonlinear spatial `0.8109`.
- Matched univariate results reproduce, including `ink_max=0.7478`, `dist_le_1=0.7290`, `abs(dist_mean)=0.7114`, `dist_le_2=0.6871`, `abs(dist_p90)=0.6743`, `ink_surface_ratio=0.6651`, and `surface_decay=0.6257`.

Artifact SHA-256:

- features CSV: `6e5f9854e209905eb6c734da1aedae414bf9e7574fb819efc027d62cc5f3a372`
- matched pairs CSV: `62992fb48042046f92e65fc4700bc5a48264966ca9701a81828288e8e234a29f`
- original report: `a67f4f335b7ff8be07d274abf06855080d101ae1f0c7119518e616cf70efd537`
- recovered executed script: `f20a9d629b8d90722c2a61a2fe4af04b8f2234eb3b60ff213511a562d5c43f43`

## Methodological findings

1. The 490 CONTROL count results from per-bin capped sampling without redistribution from undersupplied bins. The design is deterministic but not exactly balanced.
2. Matching is greedy, ordered by GP Surface fraction, and not globally optimal. It is one-to-one and respects the 0.5 percentage-point caliper; sensitivity to match order or optimal assignment was not tested.
3. Matched AUC compares matched marginal distributions; no paired effect estimate or cluster/bootstrap confidence interval was generated.
4. The four model AUCs use all 990 selected rows, not the 429 matched pairs. The ML feature set excludes `surface_fraction`, but several geometry features are functions of predicted Surface and can retain regional/surface-quality information.
5. Spatial groups are fixed 256^3 L3 blocks with no exclusion buffer. Of 35 same-class pairs whose 64^3 patches overlap, 10 are assigned to different spatial folds (8 GP, 2 CONTROL). Spatial CV is not fully leakage-safe.
6. Spatial block CV is not a held-out-region test. GP and CONTROL labels may encode scan position, wrap, CT quality, or prediction-domain shift rather than handwriting.
7. `ink_max` is strongest matched feature but is sensitive to one extreme voxel. Robust top-k/quantile/cluster-persistence ablations were not included.
8. The original report lacks confidence intervals, effect sizes, calibration, retrieval metrics, feature ablations, and a matched-model baseline.
9. Surface input is a volumetric prediction, not verified sheet geometry. CT-support was not checked, signed surface distance is unavailable, and distinct wraps may be mixed.
10. Cache coverage is complete (990 Ink and 990 Surface patches; 519,298,560 bytes), but cache is patch-based, lacks manifest/checksum validation, and uses non-atomic `.npy` writes.

## Interpretation

Stored artifacts demonstrate a reproducible association between regional GP membership and local Ink3D/Surface-derived features. They do **not** demonstrate real ink, a letter, or continuous written structure. The original automatic conclusion "GO FORTE" is not supported by the validation target and leakage controls. Appropriate status: **promising result, but still requires validation**.

## Most informative next test

Freeze a continuous Grand Prize ROI before inspection; associate samples with verified TIFXYZ/mesh and CT-support; construct a continuous 2D/2.5D evidence map without using the banner; extract connected components and skeletons. Evaluate only after freeze against Ink3D-raw, Surface-only, and simple morphology baselines, using top-k enrichment, region-level AP/precision-recall, continuity, and stability under threshold/surface perturbations. Use spatially separate development ROIs and leave the primary ROI untouched for final reveal.
