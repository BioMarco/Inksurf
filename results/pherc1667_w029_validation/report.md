# PHerc1667-w029 locked partition gate

- Date: 2026-09-16
- Track / regime / geometry tier: A / local VALIDATION / G1
- Frozen protocol commit: `a2ec27f`
- Final status: `NO_GO_LABEL_DIVERSITY_UPPER_BOUND`
- Score comparison performed: no
- Prediction or TIFXYZ pixels downloaded: no

The metadata-only selector froze 12 validation-mask chunks before any PHerc1667
pixel access. The bounded reveal transferred and verified 48 source/annotation
files totaling 21,434,252 bytes.

The partition contains 68,831 validation pixels: 3,541 positive and 65,290
negative. All positive pixels occur in chunk `[28,54]`; the remaining 11 chunks
contain no positives. The frozen protocol requires at least four chunks with
both classes. Since subsequent common-geometry filtering can only remove
pixels, the maximum possible count is one and the experiment stops immediately.

This is a robust eligibility failure under the frozen rule. It is not a score
or model-quality result, does not show absence of ink, and must not be repaired
by choosing new chunks after reveal. The labels are upstream online-validation
pseudo-labels and would not constitute independent ground truth even if the gate
had passed.
