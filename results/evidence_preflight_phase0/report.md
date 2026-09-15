# Evidence Consistency Phase 0 — metadata preflight

**Run:** `inksurf-evidence-phase0-20260914`

**Track/regime:** Track A / DEV

**Result:** `conditional_go_raw_evidence_only`

**Volumetric bytes downloaded:** 0

**VALIDATION/DISCOVERY files accessed:** 0 / 0

The official data-browser catalog was read from the frozen `ScrollPrize/villa`
commit `2c477013ed05d0823f193d8eeccf25e93293503f`. The bounded document contains
751,244 bytes and matches SHA256
`b464f82279ed5cecba4a3a4c9838aa56e212ab23918114b9f19252ea5564fafc`.

## Observed metadata

| DEV sample | scans | segments | declared ink | ink entries / outputs | prediction entries | qualifying scan pairs |
|---|---:|---:|---:|---:|---:|---:|
| PHercParis4 | 7 | 81 | 80 | 81 / 80 | 4 | 20 |
| PHerc1667 | 4 | 20 | 19 | 19 / 19 | 1 | 6 |
| PHerc0139 | 5 | 38 | 38 | 38 / 38 | 4 | 9 |

A pair qualifies this metadata-only screen when the acquisition IDs differ and
at least one of energy, resolution or facility differs. This is a shortlist
rule, not proof of statistical independence.

## Verified result

All three known-text DEV samples satisfy the preregistered catalog gate. Paris
4 is the strongest first target because the catalog also reports surface
prediction and Ink3D products. This only establishes that a bounded pilot has
plausible source material.

The artifact audit found two Paris 4 same-label pairs backed by distinct
surface-volume IDs (`w104-106` and `w122-123`). Neither provides two independent
ink outputs: one member of `w104-106` has no full ink output, while both
`w122-123` outputs point to the same 2.4 um source volume. Therefore the catalog
contains a route to compare raw acquisitions, but **zero catalogued pairs of
independent ink predictions** on an apparently corresponding surface.

The Paris 4 declared ink count is 80 while the catalog contains 81 ink-segment
entries, 80 of which have a `full` output. This is recorded as a provenance
distinction, not interpreted as an upstream error.

## Open blockers

- Common physical surface coverage across scans is not established.
- Cross-scan transforms and registration error are not verified.
- No independent ink-output pair is present in the two same-label cross-volume
  candidates; any independence test must start from raw evidence or generate
  new outputs under a frozen protocol.
- A held-out evaluation unit has not been frozen.
- Paris 4 carries a publication-reservation notice that must be preserved in
  every derived manifest.

## Decision

Proceed only to a transform/overlap feasibility audit for the two Paris 4 raw
surface candidates. Do not download or scan volumes until one pair has a
bounded I/O plan, a transform path, a physical-scale evaluation unit and a
declared legal regime.

Machine-readable artifacts: `report.json`, `scan_pairs.csv` and
`artifact_pairs.csv` in this folder.
