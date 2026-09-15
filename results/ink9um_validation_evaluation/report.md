# Bounded ink_9um DEV evaluation

**Date:** 2026-09-15

**Track / regime / geometry:** A / DEV / G1

**Classification:** promising result requiring cross-scroll confirmation

Twelve 128 × 128 chunks were selected deterministically from the official
PHerc0139-w016 online-validation mask using compressed mask size followed by
lexicographic coordinates. No CT intensity, ink label content or model output
entered selection. The source transfer was bounded to 21,435,514 bytes and the
official 2.4-to-9.6 µm preparation was reproduced: level-2 XY, centered 84 Z
planes, rounded 4× Z mean pooling, then the centered 17-plane model input.

Two official `ink_9um` checkpoints at step 75,000 (seed 42 and seed 43) were
run with the pinned villa commit
`3ea17f54a9b3d5fd1aaf73e1d2c8386dbaa9f30e`. Both loaded with zero missing or
unexpected keys. They are correlated replicas and are aggregated as one model
family, never counted as two independent confirmations.

## Verified result

- Evaluation pixels: 81,524; positive prevalence: 0.23820.
- Seed 42 AP: 0.58690; seed 43 AP: 0.71779.
- Mean ensemble AP: 0.72371.
- Best frozen raw baseline (`depth_std17`) AP: 0.25269.
- Ensemble gain over best raw baseline: +0.47102 AP.
- Mean per-region AP gain over six mixed-class chunks: +0.31096; 95% whole-
  chunk bootstrap interval `[0.17237, 0.42552]` (2,000 draws, seed 0).
- Six selected chunks contain no positive label. Their mean ensemble score is
  0.24881 versus 0.57814 on positive-labeled pixels, margin 0.32933.
- Seed prediction Pearson: 0.52601; mean absolute disagreement: 0.12606.
- Abstaining on the frozen 20% highest-disagreement pixels retains 0.80000 of
  evaluation pixels and raises AP from 0.72371 to 0.80921.
- All preregistered bounded-DEV checks pass: `GO_BOUNDED_DEV`.

## Limits

This is not confirmatory evidence. PHerc0139-w016 is an official online-
validation case for the released checkpoint family, and the labels are
transferred annotations/pseudo-labels rather than independent IR truth. The 12
chunks intentionally form a coverage-rich stress subset and are not a random
or spatially representative sample. G1 pixel alignment is sufficient for this
model benchmark but not for a G2 structural claim. The abstention improvement
must be reproduced with the exact frozen method on another scroll and on a
partition not used to choose its parameters.

## Reproducibility

- `configs/ink9um_validation_preflight.json`
- `configs/ink9um_validation_chunk_audit.json`
- `configs/ink9um_validation_inference.json`
- `configs/ink9um_validation_evaluation.json`
- `kaggle/ink9um_validation_inference/`
- `results/ink9um_validation_preflight/`
- `results/ink9um_validation_inference/kaggle_v3/`
- `results/ink9um_validation_evaluation/evaluation_report.json`

The two failed Kaggle environment attempts are retained. No Discovery data was
accessed.
