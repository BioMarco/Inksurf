# Progress Prize claim audit

**Date:** 2026-09-15

**Verdict:** `NO_GO_SUBMISSION_CLAIM`

InkSurf verified the hashes and schemas of five preserved receipts and applied
one claim policy to all of them. There are currently zero confirmation-eligible
receipts.

| Receipt | Role | Tier | Groups | Gates | Permitted claim |
|---|---|---:|---:|---:|---|
| Canonical compatibility | compatibility | G1 | 1 | n/a | pipeline compatibility |
| PHerc0139 cross-scan | repeatability | G2 | 1 | 4/4 | repeatability under a shared model |
| PHerc0139 labels | development | G1 | 1 | 3/3 | promising bounded DEV behavior |
| PHerc0814 locked | locked validation | G1 | 1 | 2/4 | negative result; no confirmation |
| PHerc0814 diagnosis | post-hoc | n/a | 1 | n/a | signal-bearing disagreement diagnosis |

The software guardrail is demonstrated: several attractive metrics are present,
but no combination satisfies the frozen confirmation contract. A confirmatory
claim requires a G2/G3 locked result, at least two sufficiently independent
evidence groups and independent ground truth.

This audit does not weaken the software contribution. It makes the current
claim ceiling explicit and machine-checkable instead of allowing a promising
DEV metric or repeatability number to silently become an ink claim.
