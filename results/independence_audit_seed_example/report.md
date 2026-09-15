# Independence audit — correlated seed example

**Date:** 2026-09-15

**Track / regime:** A / DEV

**Status:** `NO_GO_DEPENDENT_EVIDENCE`

Two official `ink_9um` checkpoints were deliberately declared as separate
groups (`seed42` and `seed43`). The provenance policy requires distinct
`acquisition_id`, `model_family_id` and `training_data_id` values.

All three fields are shared. InkSurf therefore merges the two declared groups
into one effective group:

| Measure | Value |
|---|---:|
| Declared groups | 2 |
| Effective groups | 1 |
| Minimum required | 2 |
| Independence gate | failed |

This is a verified software guardrail, not evidence that the sources are
statistically dependent in every respect. Its purpose is narrower: correlated
replicas cannot manufacture a second independent confirmation merely by using
different group names. Missing required provenance also fails closed.

Machine-readable receipt: `report.json`.
