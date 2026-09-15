# PHerc0139-w016 bounded physical diagnostic

**Date:** 2026-09-15

**Track / regime / geometry:** A / DEV / G2 on the frozen bounded pixels only

The matching 2.399 µm TIFXYZ was downloaded under a 24 MiB cap. Whole-surface
geometry remains G1 because 137 adjacent-normal flips and three degenerate
quads occur somewhere in roughly 1.71 million valid quads. No criterion was
relaxed after that result.

A separate audit of the 12 already-frozen evaluation chunks found zero
unsupported pixels, zero selected degenerate cells and zero selected normal
flips. CT support is 1.0 in all 12 chunks. The verified evaluation area is
`0.0751664 cm²`, including `0.0571943 cm²` of negative-reference area.

| Policy | Accepted | Pixel precision | Pixel recall | False area / negative area |
|---|---:|---:|---:|---:|
| InkSurf fail-closed, one effective group | 0.00% | n/a | 0.0000 | 0.0000% |
| Naive score >= 0.5 | 27.01% | 0.5809 | 0.6587 | 14.8732% |
| Naive top 1% | 1.00% | 1.0000 | 0.0420 | 0.0000% |
| Naive top 5% | 5.00% | 0.9375 | 0.1968 | 0.4216% |

The component count is chunk-clipped and must not be interpreted as a
continuous-ROI false-region rate. The reference is transferred/pseudo-label
DEV data and the upstream model family is not independent of model selection.
The top-1% result is promising but not confirmatory. InkSurf's zero false area
comes with zero yield and is a safety behavior, not detector superiority.
