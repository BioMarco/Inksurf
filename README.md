# InkSurf

[![tests](https://github.com/BioMarco/Inksurf/actions/workflows/tests.yml/badge.svg)](https://github.com/BioMarco/Inksurf/actions/workflows/tests.yml)

**Fail-closed evidence auditing for surface-based Vesuvius Challenge ink
workflows.**

InkSurf checks whether aligned surface-space signals are supported by genuinely
independent evidence. It aggregates correlated replicas before measuring
consensus, disagreement and abstention, and records enough provenance to make a
result auditable.

InkSurf does **not** claim that a high model score is ink, that repeatability is
independence, or that a small image patch is a readable letter.

```text
declared sources -> verified registration -> continuous surface coordinates
                 -> collapse correlated replicas by independence group
                 -> consensus / disagreement -> abstention -> audit receipt
```

## Why this exists

Ink-detection pipelines often average model seeds, offsets, tiles or rescans and
treat agreement as added confidence. Those inputs can share training labels,
anatomy, preprocessing and failure modes. InkSurf makes those dependencies
explicit and fails closed when the evidence is insufficient.

A real locked check in this repository demonstrates the problem. On PHerc0814,
an ensemble improved average precision over raw CT baselines, but abstaining on
the 20% of pixels with greatest seed disagreement reduced AP from `0.59718` to
`0.52245`. Post-hoc diagnosis found that disagreement itself was positively
associated with the reference label (`AP 0.63808`). The negative validation
result is preserved rather than retuned.

## Current capabilities

| Capability | Behavior |
|---|---|
| Independence groups | Correlated variants are collapsed before support is counted |
| Evidence maps | Consensus, support fraction, cross-group disagreement and acceptance |
| Fail-closed validation | Requires explicit track, visibility regime and geometry tier |
| Disagreement audit | Tests whether replica disagreement behaves like uncertainty or signal |
| Geometry checks | TIFXYZ bounds, coordinates, CT support and surface seating utilities |
| Bounded I/O | Chunk-aware plans, byte limits, manifests, hashes, resume and atomic output |
| Physical burden | False-positive area and reviewable regions per negative cm² on G2/G3 surfaces |
| Reproducibility | Frozen JSON configs, seeds, source versions and machine-readable reports |

The historical threshold/component/skeleton micro-patch review path is closed
`NO-GO`. Human reviewers are not asked to identify ink in physically tiny,
context-free crops.

## Installation

Python 3.10 or newer is required.

```bash
git clone https://github.com/BioMarco/Inksurf.git
cd Inksurf
python -m venv .venv
```

Activate the environment, then install the package:

```bash
python -m pip install -e ".[catalog,benchmark,structure,fragment]"
python -m unittest discover -s tests
```

The core package depends only on NumPy and Requests. Optional groups add Zarr,
TIFF, scientific-image and Kaggle support.

## One-minute demo

The deterministic synthetic demo needs no scan data, network access or GPU:

```bash
inksurf-demo --output-dir results/demo
```

It creates three views: two correlated replicas containing the same false
artifact and one independent source that supports only the reference structure.
Because the replicas share one `independence_group`, the duplicated artifact
does not receive two votes. The expected receipt contains:

```json
{
  "view_count": 3,
  "independent_group_count": 2,
  "reference_pixels": 320,
  "single_group_artifact_pixels": 75,
  "accepted_reference_pixels": 320,
  "accepted_artifact_pixels": 0
}
```

This is a software behavior check, not evidence about papyrus ink.

## Core Python API

```python
from inksurf.evidence_consistency import combine_evidence

maps = combine_evidence(
    views=[seed_1, seed_2, independent_map],
    independence_groups=["model-a", "model-a", "source-b"],
    evidence_threshold=0.6,
    minimum_independent_groups=2,
    minimum_support_fraction=1.0,
    maximum_disagreement=0.2,
)

accepted = maps["accepted"]
```

All views must already be registered to the same surface coordinate frame and
have identical shapes. Registration is deliberately not hidden inside the
combiner: it must be versioned and verified separately.

The configuration-driven CLI accepts NumPy, TIFF and Zarr inputs:

```bash
inksurf-evidence-consistency --config path/to/config.json
```

See [the evidence consistency protocol](docs/evidence_consistency_protocol.md)
for the input contract and a complete configuration example.
Physical false-positive reporting is specified in
[the physical-area protocol](docs/physical_false_positive_protocol.md).

The reviewer-facing claim audit verifies receipt hashes and schemas, then
computes the highest claim the evidence actually permits:

```bash
inksurf-claim-audit --config configs/progress_prize_claim_audit.json
```

The current result is deliberately `NO_GO_SUBMISSION_CLAIM`: the software
guardrail is demonstrated, but no receipt yet combines locked success, G2/G3
geometry, independent evidence groups and independent ground truth.
Claims of two or more independent groups require a hashed provenance-audit
receipt; an unaudited number in the ledger is automatically capped at one.

Declared group names are not trusted on their own. The provenance audit merges
groups that share any required dependency field, and also fails closed when a
required field is missing:

```bash
inksurf-independence-audit --config configs/independence_audit_seed_example.json
```

In the example, two seeds are deliberately declared as separate groups. Shared
acquisition, model family and training data reduce them to one effective group,
so the independence gate fails.

## Real-data evidence ledger

These experiments are receipts for specific claims, not a ladder in which every
`GO` proves ink.

| Experiment | Regime / tier | Verified result | Interpretation |
|---|---|---|---|
| Canonical model compatibility | DEV / G1 | Pearson `0.98974` against the official map | Pipeline compatibility only |
| PHerc0139 cross-scan repeatability | DEV / G2 | Pearson `0.99534`, top-5% Jaccard `0.95270` | Robust repeatability; shared anatomy remains a confounder |
| PHerc0139 bounded labels | DEV / G1 | Ensemble AP `0.72371`; abstained AP `0.80921` | Promising development result |
| PHerc0814 locked labels | VALIDATION / G1 | Ensemble AP `0.59718`; 2/4 gates passed | `NO-GO` for seed-disagreement abstention |

Detailed reports:

- [canonical compatibility](results/ink_model_compatibility/report.md)
- [cross-scan repeatability](results/pherc0139_cross_scan_consistency/report.md)
- [bounded DEV benchmark](results/ink9um_validation_evaluation/report.md)
- [locked PHerc0814 validation](results/ink9um_pherc0814_validation/report.md)
- [naive workflow versus InkSurf](docs/method_comparison.md)
- [bounded real-data walkthrough](docs/real_data_walkthrough.md)
- [Progress Prize submission draft](docs/progress_prize_submission_draft.md)

The PHerc0814 labels are transferred annotations/pseudo-labels and the upstream
model used that case for online validation. This is not fully independent
ground truth, and geometry tier G1 does not support submission-grade structural
or ink claims.

## Scientific guardrails

- Declare every input's `independence_group`.
- Do not count seeds, offsets, tiles or augmentations of one model/acquisition as
  independent confirmations.
- Do not use disagreement for abstention until DEV and a separate locked check
  show that larger disagreement predicts error rather than signal.
- Use spatial or whole-region splits; overlapping patches must not cross folds.
- Freeze validation selection, code, metrics and gates before label reveal.
- Report baselines, effect sizes, intervals and negative results.
- Require verified geometry and CT support for structural claims.
- Keep discovery data and public Progress Prize evidence strictly separated.

The binding project rules are in [AGENTS.md](AGENTS.md). The complete scientific
record is maintained in [PROJECT_STATE.md](PROJECT_STATE.md).

## Repository layout

```text
src/inksurf/   Python package and CLIs
tests/         offline unit tests
configs/       frozen experiment configurations
docs/          protocols, governance and submission planning
kaggle/        reproducible GPU inference source, without credentials/weights
results/       reviewed aggregate receipts only
```

Scan data, caches, model weights, prediction arrays and discovery previews are
not committed. New files under `results/` fail closed in Git and require an
explicit publication review. See the
[public release manifest](docs/public_release_manifest.md).

## Project status and roadmap

The immediate target is a defensible Vesuvius Challenge Progress Prize
submission. The current contribution is an evidence-independence and failure
diagnostic layer, not a First Letters submission.

Before submission:

1. ~~demonstrate a decision-level advantage over naive ensemble/repeatability
   checks;~~ completed in the preserved comparison;
2. measure the implemented physical false-positive burden on an eligible G2
   labeled ROI;
3. consume rather than duplicate community CT-support, seating and dual-energy
   outputs;
4. publish an end-to-end real-data walkthrough with bounded downloads;
5. obtain community feedback and complete the official submission review.

First Letters work remains a separate locked-discovery track. A qualifying
submission would additionally require a verified TIFXYZ mesh, low-distortion
flattening and ten legible letters in one 4 cm² area under the current prize
rules.

## Licence and data

InkSurf code is released under the [MIT License](LICENSE). Vesuvius Challenge
scan data, labels and derived data retain their upstream licences and terms;
the MIT licence does not relicense them. This repository distributes aggregate
receipts but no original CT volume or model checkpoint.

Official resources:

- [Vesuvius Challenge](https://scrollprize.org/)
- [Open prizes](https://scrollprize.org/prizes)
- [ScrollPrize/villa](https://github.com/ScrollPrize/villa)
- [Open-data documentation](https://github.com/ScrollPrize/open-data)

Contributions are welcome; read [CONTRIBUTING.md](CONTRIBUTING.md) first.
