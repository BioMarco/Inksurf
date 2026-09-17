# InkSurf v0.1.0 release readiness

**Audit date:** 2026-09-16

**Target:** Vesuvius Challenge Progress Prize, deadline 2026-09-30 23:59 Pacific

**Official requirements:** https://scrollprize.org/prizes#progress-prizes

## Release decision

**Software release: GO.**

**Progress Prize submission: credible as a validator/auditor contribution.**

**Ink, First Letters or structural discovery claim: NO-GO.**

InkSurf addresses a concrete failure mode in real Vesuvius workflows: correlated
model replicas, repeated anatomy, invalid geometry and unsuitable labeled
partitions can otherwise be mistaken for independent confirmation. It provides
a modular, fail-closed implementation and retains negative results rather than
silently changing regions or thresholds.

## Official-criteria mapping

| Requirement | Evidence | Status |
|---|---|---|
| Specific Vesuvius problem | Dependency-aware evidence consistency, geometry/support eligibility and claim ceilings | Ready |
| Clear implementation and demonstration | Package CLIs, deterministic demo, bounded real-data walkthrough | Ready |
| Advantage over existing solutions | Converts high correlation/AP into auditable claim limits; caught three distinct real-data eligibility failures | Ready, but community feedback would strengthen it |
| Comprehensive documentation | README, governance, protocols, walkthrough, method comparison and submission draft | Ready |
| Usage examples | Synthetic demo and bounded PHerc0139/PHerc1667 workflows | Ready |
| Standard formats and modular integration | NumPy, TIFF, Zarr and TIFXYZ/mesh QA receipts; JSON/CSV outputs | Ready |
| Early open-source release | Public GitHub repository, MIT licence and green public CI | Ready |
| Actual community use | No public issue/comment from an external user yet | Feedback requested |

## Verified release gate

- `python -m unittest discover -s tests`: 149/149 passed;
- `python -m pytest -q`: 149/149 passed;
- package wheel built successfully as `inksurf-0.1.0-py3-none-any.whl`;
- synthetic demo: 320/320 reference pixels accepted, 0/75 correlated-artifact
  pixels accepted;
- claim audit: `NO_GO_SUBMISSION_CLAIM`, zero confirmation-eligible receipts,
  software guardrail demonstrated;
- no tracked scan/prediction/model/image payloads with extensions `.npy`, `.npz`,
  `.tif`, `.tiff`, `.zarr`, `.pt`, `.pth`, `.ckpt`, `.onnx`, `.png`, `.jpg` or
  `.jpeg`;
- no credential/private-key pattern found in tracked files;
- generated JSON receipts now use deterministic LF line endings on Windows;
- local data, caches, credentials, model weights and discovery material remain
  excluded by Git.

The public repository API confirms visibility `public`, default branch `main`,
MIT licence and a successful GitHub Actions run for commit `6b3c6a8`.
Machine-readable summary: `results/release_readiness/report.json`.

## Scientific scope to preserve

The public claim is software utility and failure diagnosis, not detection of
physical ink. PHerc0814 is an upstream online-validation pseudo-label case;
PHerc0139-w045 has only negative labels in common geometric support; the frozen
PHerc1667 partition concentrates all positives in one chunk and fails its
preregistered four-chunk diversity gate. None is independent ground truth.

## Remaining actions

1. Create a GitHub release/tag `v0.1.0` after public CI is green.
2. Add discoverability topics to the GitHub About panel.
3. Share the repository in the Vesuvius Challenge community and request one
   concrete reproducibility/integration review.
4. Submit the Progress Prize form using
   `docs/progress_prize_submission_draft.md` before the deadline.
5. Keep First Letters/Title discovery artifacts private and separate; do not
   attach them to this Progress Prize submission.

The public announcement and official submission must be performed or explicitly
approved by the owner because they publish work under the owner's identity.
