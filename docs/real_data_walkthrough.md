# Real-data walkthrough

This walkthrough verifies the published InkSurf evidence ledger without
downloading CT data, then shows the bounded stages needed for a full rerun.

## 1. Verify the software

```bash
python -m pip install -e ".[catalog,benchmark,structure,fragment]"
python -m unittest discover -s tests
inksurf-demo --output-dir results/demo
```

The demo must accept 320 reference pixels and reject all 75 pixels of the
single-group artifact. It is synthetic and makes no ink claim.

## 2. Verify the real-data receipts

The repository includes only aggregate JSON receipts, not predictions, labels
or CT data. Verify their hashes, schemas and claim ceilings with:

```bash
inksurf-claim-audit --config configs/progress_prize_claim_audit.json
```

Expected status:

```text
NO_GO_SUBMISSION_CLAIM
software_guardrail_demonstrated = true
confirmation_eligible_receipts = 0
```

This is the central reproducible result: attractive compatibility,
repeatability and DEV metrics are not silently promoted into a validated ink
claim.

## 3. Bounded PHerc0139 DEV preparation

The following optional run accesses public Vesuvius Challenge metadata and a
bounded set of source chunks. It does not download a full volume.

```bash
inksurf-ink9um-validation-preflight \
  --config configs/ink9um_validation_preflight.json

inksurf-bounded-http-download \
  --manifest results/ink9um_validation_preflight/download_manifest.json

inksurf-ink9um-chunk-audit \
  --config configs/ink9um_validation_chunk_audit.json
```

The frozen plan transfers 48 objects totalling 21,435,514 bytes: 12 raw level-2
chunks and 36 small annotation chunks. The preparation follows the official
`ink_9um` recipe: centred 84-plane depth window, rounded 4x depth mean pooling,
then the central 17 of 21 layers for inference.

Stop if the manifest exceeds its configured byte cap, any checksum/read check
fails, or the source metadata differs. Downloaded data and derived arrays stay
under ignored `data/` paths.

## 4. GPU inference

The reproducible Kaggle source is under
`kaggle/ink9um_validation_inference/`. It pins:

- ScrollPrize/villa commit `3ea17f54a9b3d5fd1aaf73e1d2c8386dbaa9f30e`;
- official seed-42 and seed-43 step-75,000 checkpoint hashes;
- robust-MAD normalization and central 17-layer crop;
- private output and input datasets.

The two checkpoints share training data and architecture and therefore belong
to one independence group. The checked-in Kaggle metadata records the last
locked PHerc0814 run; do not overwrite that run to reproduce DEV. Create a
separate private Kaggle dataset/kernel identity for a new execution and retain
the resulting inference receipt and prediction hash.

## 5. Evaluation and non-reuse rule

The PHerc0139 DEV evaluation can be regenerated after the matching prediction
bundle is restored locally:

```bash
inksurf-ink9um-validation-evaluation \
  --config configs/ink9um_validation_evaluation.json
```

PHerc0814 has already been revealed and may only be used for post-hoc diagnosis:

```bash
inksurf-replica-disagreement-audit \
  --config configs/ink9um_pherc0814_posthoc_disagreement.json
```

It must not be relabelled as a new confirmatory partition. A future confirmation
requires a new frozen whole-region split, G2/G3 geometry, at least two
sufficiently independent evidence groups and ground truth independent of model
selection.

## Data and licence boundary

No original Vesuvius Challenge data are committed here. Upstream data and
labels retain their own licences and terms. Review `docs/data_governance.md`
before redistributing any derived artifact.
