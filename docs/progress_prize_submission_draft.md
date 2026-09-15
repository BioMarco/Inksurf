# InkSurf Progress Prize submission draft

**Repository:** https://github.com/BioMarco/Inksurf

**Licence:** MIT (code only)

**Target:** Vesuvius Challenge Progress Prize, September 2026 review cycle

## Problem identification

Surface-based ink workflows frequently combine model seeds, offsets, tiles or
rescans and interpret agreement as confidence. These views can share training
labels, preprocessing, anatomy and failure modes. Standard ensemble metrics do
not state when those dependencies invalidate a confidence claim.

## Solution

InkSurf is a fail-closed evidence and provenance layer. Every view declares an
`independence_group`; correlated variants are collapsed before cross-group
support is counted. The software produces continuous consensus, support,
disagreement and acceptance maps, audits whether disagreement actually predicts
error, and computes a machine-readable ceiling on the claims supported by the
available receipts.

InkSurf accepts NumPy, TIFF and Zarr evidence maps and is designed to consume
versioned registration, TIFXYZ/mesh QA, CT-support and other community-tool
outputs rather than reimplement them.

## Demonstrated advantage

A naive reading of the preserved experiments could report:

- canonical reproduction Pearson `0.98974`;
- cross-scan Pearson `0.99534` and top-5% Jaccard `0.95270`;
- PHerc0139 DEV ensemble AP `0.72371`, increasing to `0.80921` after
  seed-disagreement abstention.

InkSurf blocks the implied confirmation because the views are one dependent
model family and repeatable anatomy is not independent ink evidence. The need
for this guardrail was then demonstrated prospectively: on the frozen
PHerc0814 partition, only 2/4 gates passed and the same abstention rule reduced
AP from `0.59718` to `0.52245`. Post-hoc audit found that seed disagreement was
itself signal-bearing (`AP 0.63808`, label correlation `r=0.47522`).

The result was preserved as `NO-GO`; no threshold, subset or narrative was
changed after label reveal. `inksurf-claim-audit` verifies all receipt hashes
and returns:

```text
NO_GO_SUBMISSION_CLAIM
software_guardrail_demonstrated = true
confirmation_eligible_receipts = 0
```

This converts a subtle scientific failure mode into actionable information:
teams can determine whether an ensemble or rescan really adds evidence before
spending review time or publishing an ink claim.

## Reproducibility

- 106 offline tests on Windows; the same suite runs in GitHub Actions;
- deterministic synthetic demonstration with a planted correlated artifact;
- frozen real-data configs, source/checkpoint hashes and bounded I/O manifests;
- atomic output, cache verification and explicit negative-result retention;
- public aggregate receipts without redistributing CT data, labels or weights.

Start with:

```bash
python -m pip install -e ".[catalog,benchmark,structure,fragment]"
inksurf-demo --output-dir results/demo
inksurf-claim-audit --config configs/progress_prize_claim_audit.json
```

The complete bounded real-data workflow is documented in
`docs/real_data_walkthrough.md`.

## Honest scope

InkSurf has not validated physical ink, found letters or produced a qualifying
First Letters image. PHerc0814 uses transferred reference annotations and was
exposed to upstream model selection; the locked result is therefore useful as a
local method stress test, not independent ground truth. Structural claims
require G2/G3 geometry and are currently blocked.

## Integration path

The next integration target is a small adapter contract for versioned outputs
from community CT-support, seating, dual-energy and VC3D workflows. A new
confirmatory run will require at least two genuinely independent groups and a
whole-region held-out reference.

## Requested consideration

We request consideration as an analytic/failure-diagnostic Progress Prize
contribution: InkSurf exposes when apparently strong ink evidence is dependent,
tests the semantics of disagreement rather than assuming them, and provides a
reusable fail-closed implementation with real-data receipts.
