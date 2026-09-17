# September 2026 Progress Prize form — prepared answers

Official form:
https://docs.google.com/forms/d/e/1FAIpQLScNBMj25FMnphngRG1Ciryv_2_Mkdq2YPJOD9WqPfZExII2iQ/viewform

Deadline: 2026-09-30, 23:59 Pacific.

## Fields the owner must complete

- **Email:** use the address at which the Vesuvius Challenge team should contact
  you.
- **Full name:** enter your legal/full name.
- **Team description:** `Individual submission by [FULL NAME].`
- **Discord display name:** enter it if you are a member; the field is optional
  in the current form.
- **Contribution URL:** `https://github.com/BioMarco/Inksurf`
- **Terms:** read the current terms and select `Yes, I agree` only if accepted.

## Contribution answer

InkSurf is an open-source toolkit that helps Vesuvius Challenge teams decide whether evidence for a possible ink reading is truly independent and reliable — or just correlated predictions. This prevents false positives, wasted effort, and unsupported conclusions.

(1) Which scroll data did you work on for this submission?
I worked on public Vesuvius data from PHerc0139 (including the w016 and w045 surfaces), PHerc0814-46527, and PHerc1667-w029. I also performed a metadata-only provenance census of all 24 public ink_9um reference cases. The repository contains aggregate receipts and exact bounded configurations, but it does not redistribute CT volumes, labels, or model weights.

(2) How does it substantially increase the probability of yourself or someone else reading those scrolls or others?
Many ink pipelines treat agreement across seeds, offsets, tiles, or rescans as independent confirmation, even when those views share training data, anatomy, and failure modes. InkSurf checks provenance, collapses correlated replicas into independence groups, verifies surface registration and common support, tests whether disagreement actually behaves like uncertainty, and abstains or stops when the evidence cannot support the requested claim. This helps researchers avoid chasing weak candidates and focus on genuinely promising ones.

(3) What does it enable that was not possible before?
InkSurf provides a modular layer between official/community data, TIFXYZ/mesh QA, and ink-review workflows. It accepts NumPy, TIFF, and Zarr evidence maps plus versioned geometry/provenance receipts, and emits deterministic JSON/CSV outputs and surface-space diagnostic maps. Bounded, resumable I/O makes the audits practical without downloading entire CT volumes. Crucially, a machine-readable claim audit (inksurf-claim-audit) states the strongest conclusion the available evidence actually permits. This is a reusable guardrail for the whole community.

(4) What evidence have you provided for this?
The package has 149 offline tests and a green public GitHub Actions run. A deterministic synthetic demo rejects all 75 pixels of a planted correlated artifact while retaining all 320 reference pixels. On real data, InkSurf preserved rather than retuned several actionable failures:

- PHerc0814: seed-disagreement abstention reduced AP from 0.59718 to 0.52245; the result was preserved as NO-GO instead of being retuned after label reveal.

- PHerc0139-w045: 32,467 common geometry-supported labeled pixels, but zero positives; the bound decision was NO_GO_SINGLE_CLASS_COMMON_SUPPORT.

- PHerc1667-w029: the prospectively frozen partition concentrated all 3,541 positives in 1 of 12 chunks, failing its preregistered spatial-diversity gate before prediction download.

- The repository also records promising but explicitly non-confirmatory DEV results, including PHerc0139 ensemble AP 0.72371 and a bounded G2 false-positive area diagnostic.

These results demonstrate that InkSurf detects invalid confidence and unsuitable evaluations that ordinary correlation or ensemble metrics would not expose.

In short: InkSurf does not promise a miraculous reading. It makes the discovery process more reliable, transparent, and reproducible. It is open source under the MIT license, fully documented, and already usable by other teams.

Reproduction starts with the one-minute demo and claim audit in the README. The
bounded real-data workflow, method comparison, frozen configs, release audit and
all aggregate receipts are linked from the repository.

## Final submission check

Before pressing Submit:

1. open the repository URL in a private/incognito browser;
2. verify the latest GitHub Actions run is green;
3. verify the `v0.1.0` release is visible;
4. replace `[FULL NAME]` and provide the correct email/Discord identity;
5. paste the contribution answer without changing its scientific scope;
6. save the emailed copy of the response and submission timestamp.
