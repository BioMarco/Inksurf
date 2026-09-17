# PHerc0814 locked cross-scroll validation

**Date:** September 15, 2026

**Track / regime / geometry tier:** Track A / VALIDATION / G1

**Frozen verdict:** `NO-GO` (2 of 4 gates passed)

## Protocol and integrity

The partition `ink9um-pherc0814-46527-top12-v1`, the method, the chunk
selection and the four gates were frozen before downloading the annotations.
The 12 `128 x 128` chunks were chosen solely by the compressed size of the
validation mask and lexicographic order, without consulting CT data, ink
labels or predictions. 21,435,302 verified bytes were transferred; no images
were inspected during selection, preparation, inference or evaluation.

Frozen method:

- evaluator source SHA-256:
`d43326870c5edb1e80a74861a49bc82e47c87f4d065ffe167ad5b5e6224a6581`;
- evaluator config SHA-256:
`1c332dc3e92f6276f681d07df84aadd2db0d00da87c1e3a02990c9dc36564373`;
- prediction bundle SHA-256:
`d1ca90a888af3305e0b2b81720029b1f1cb112d86a660c49f0a84f420ac7a1cb`;
- villa commit: `3ea17f54a9b3d5fd1aaf73e1d2c8386dbaa9f30e`;
- official checkpoints step 75,000, seeds 42 and 43, treated as a single
`independence_group`.

## Verified results

The benchmark contains 106,207 validation pixels, 31,737 positives (prevalence
`0.298822`) and 5 negative-only chunks. The frozen metrics are:

| Measure                                              | Result               |
| ----------------------------------------------------- | -------------------- |
| AP seed 42                                             | 0.55954               |
| AP seed 43                                             | 0.53792               |
| Mean ensemble AP                                       | 0.59718               |
| Best raw baseline (`central_slice`)                    | 0.31162               |
| Global AP gain                                         | +0.28556              |
| Mean regional AP gain                                  | +0.16559              |
| 95% CI, whole-chunk bootstrap                          | [-0.04107; 0.40777]  |
| Positive / negative-only-control margin                | +0.10718              |
| Pearson between the two seeds                          | 0.62973               |
| AP after abstention on the 20% highest-disagreement pixels | 0.52245           |
| AP gain from abstention                                 | -0.07473              |

Gates passed: global AP gain >= 0.05; positive/control margin >= 0.10. Gates
failed: regional CI lower bound > 0; AP gain from abstention >= 0.05.

The machine-readable `status` field still uses the historical string
`NO_GO_BOUNDED_DEV`; the regime recorded in the same artifact and in the
config is `VALIDATION`. The string does not change the metrics or the verdict
and is documented as naming debt, without altering the frozen source after
reveal.

## Interpretation

**Promising result for the detector but still to be validated; NO-GO for
InkSurf's current abstention rule.** The model transfers an informative
ranking to PHerc0814 and clearly beats the three global CT baselines, so the
result is not explained by a random baseline. However, the benefit varies
widely across regions, the bootstrap CI includes zero, and disagreement
between correlated replicas here selects pixels that are on average
easier/more positive: removing them worsens AP.

This is not independent confirmation: PHerc0814-46527 was an online-validation
case for upstream training, and the labels are transferred
annotations/pseudo-labels. Geometry tier G1 does not authorize
submission-grade structural or ink claims.

## Decision and next test

No threshold, abstention fraction or selection is retouched on this
partition. PHerc0814 now moves to post-hoc diagnosis only and cannot return as
confirmatory evidence. The next informative gate must replace seed
disagreement with a source that is genuinely more independent (acquisition,
model or contrast), calibrate exclusively on DEV, and freeze a new partition
with whole spatial groups before reveal.

## Post-hoc diagnosis (non-confirmatory)

The descriptive audit performed after the verdict explains the unexpected
sign. Absolute disagreement between seeds has AP `0.63808` as a positive score
and correlation with the label `r=0.47522`; its mean is `0.15735` on positives
versus `0.04386` on negatives. Positive prevalence rises from roughly 10-12%
in the lowest deciles to `71.38%` in the highest-disagreement decile. Removing
those pixels therefore removes signal, not just errors.

These numbers do not constitute a new test and do not authorize reversing the
rule on the same partition. The `posthoc_disagreement_report.json` artifact
explicitly records regime `DEV`, `post_hoc_diagnostic`, and
`confirmatory_reuse_allowed=false`.
