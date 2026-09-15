# Evidence Consistency Phase 0 — metadata preflight

**Run:** `inksurf-evidence-phase0-20260914`

**Track/regime:** Track A / DEV

**Result:** `conditional_go_alignment_unverified`

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

The corrected artifact audit now inspects multiple render entries on one
segment as well as same-label pairs across segments. It finds 93 ink-output
pairs associated with distinct source-volume IDs. These are candidates, not 93
independent confirmations: transform, model lineage and training-data
dependencies remain unverified. The audited count of independent pairs is
therefore still zero.

One actionable DEV candidate is PHerc0139 segment `20250108000004` (`w029`):
the catalog exposes a 2.399 µm / 78 keV render from volume `20260102150214` and
a 1.129 µm / 59 keV render from volume `20260413113053`, using different model
IDs. HTTP metadata confirms tiled DEFLATE TIFFs of 63,656,391 and 41,030,186
bytes. No prediction pixels were downloaded in this phase.

The Paris 4 declared ink count is 80 while the catalog contains 81 ink-segment
entries, 80 of which have a `full` output. This is recorded as a provenance
distinction, not interpreted as an upstream error.

## Open blockers

- Common physical surface coverage across scans is not established.
- Cross-scan transforms and registration error are not verified.
- Distinct source volumes and model names do not establish independent training
  data or failure modes.
- A held-out evaluation unit has not been frozen.
- Paris 4 carries a publication-reservation notice that must be preserved in
  every derived manifest.

## Decision

Proceed to a bounded transform/overlap plan for the PHerc0139-w029 render pair.
Use TIFF tile ranges rather than downloading the complete 104.7 MB pair, and do
not count it as two groups until provenance and registration pass.

Machine-readable artifacts: `report.json`, `scan_pairs.csv` and
`artifact_pairs.csv` in this folder.
