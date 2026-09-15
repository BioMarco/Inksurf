# PHerc0139 cross-scan repeatability pilot

**Date:** 2026-09-15

**Track / regime / geometry:** A / DEV / G2

**Classification:** promising result requiring validation

## Frozen experiment

The same 512 × 512 surface window (approximately 1.230336 × 1.230336 mm) was
rendered along 109 geometric-normal samples from acquisitions `20250820105138`
and `20260319133554`. Both stacks were inferred separately with the pinned
canonical Ink3D checkpoint and loader, layers `[24,86)`, reversed layer order,
256-pixel tiles, stride 128 and Hann blending. Each acquisition is one
`independence_group`; the shared model is explicitly retained as a residual
dependency.

Kaggle v1 failed before inference because it assumed a fixed dataset mount
directory. Kaggle v2 changed only input discovery, continued to require one
unique file per acquisition and verified both frozen SHA-256 hashes.

## Verified results

- GPU run: Tesla T4, 18 total tiles, 42.4106 seconds end-to-end.
- Valid common pixels: 260,100 / 262,144.
- Prediction agreement: Pearson `0.9953403`; Spearman `0.9622815`.
- Top-1% overlap: Jaccard `0.89269`; enrichment over independent rank sets
  `94.35×`.
- Top-5% overlap: Jaccard `0.95270`; enrichment `19.52×`.
- Top-10% overlap: Jaccard `0.92034`; enrichment `9.59×`.
- Best 128-pixel shifted-control Pearson: `0.6426283`; zero-lag margin
  `0.3527120`.
- Prediction mean absolute difference: `0.0081933`; maximum absolute
  difference: `0.1411057`.
- At the frozen disagreement threshold `0.15`, retained valid coverage is
  `1.0`.
- All four preregistered repeatability checks pass: `GO_REPEATABILITY`.

## Methodological interpretation

This is a robust engineering result: coordinate handling, surface-normal
rendering and canonical inference reproduce a highly aligned map across two
acquisitions. It is not proof of ink, readable text or fully independent model
evidence. The raw rendered CT stacks themselves have Pearson `0.9993269`, mean
absolute voxel difference `18.6268` intensity units and only `0.0004099`
exactly equal voxels. The scans are bytewise distinct but share the same
physical anatomy, surface geometry and downstream checkpoint; common
morphological false positives can therefore repeat.

The scientific classification is **promising result requiring validation**,
not a prize claim. The next decisive experiment must estimate specificity on
multiple preregistered ROIs, including negative controls, and compare consensus
against each single acquisition and naive averaging using independent labels
or an appropriately separated verification source.

## Reproducible artifacts

- `configs/pherc0139_cross_scan_render_plan.json`
- `configs/pherc0139_cross_scan_render.json`
- `configs/pherc0139_cross_scan_inference.json`
- `configs/pherc0139_cross_scan_consistency.json`
- `kaggle/cross_scan_inference/`
- `results/pherc0139_cross_scan_render/`
- `results/pherc0139_cross_scan_inference/kaggle_v1/`
- `results/pherc0139_cross_scan_inference/kaggle_v2/`
- `results/pherc0139_cross_scan_consistency/consistency_report.json`
- `results/pherc0139_cross_scan_consistency/consistency_maps.npz`

No VALIDATION or DISCOVERY partition was accessed and no ink/letter claim was
made.
