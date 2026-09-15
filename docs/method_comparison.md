# What InkSurf changes in a real workflow

This comparison uses only preserved InkSurf receipts. It distinguishes a useful
prediction from evidence strong enough to support a scientific claim.

| Workflow | Observation | Naive decision | InkSurf decision | Why the decisions differ |
|---|---|---|---|---|
| Canonical reproduction | Pearson `0.98974` against a published map | Treat the pipeline as validated | Compatibility only | Reproducing one model output adds no independent evidence |
| PHerc0139 cross-scan | Pearson `0.99534`; top-5% Jaccard `0.95270` | Treat repeatability as confirmation | `GO_REPEATABILITY`, but one effective evidence group | The scans share anatomy, surface mapping and the same checkpoint |
| PHerc0139 seed ensemble | AP `0.72371`; AP after 20% abstention `0.80921` | Adopt seed disagreement as uncertainty | Promising DEV result only | Both seeds share acquisition, architecture and training data |
| PHerc0814 locked transfer | Ensemble AP `0.59718`; best raw AP `0.31162` | Report successful transfer | Partial signal, but locked `NO-GO` | Only 2/4 frozen gates passed; regional uncertainty includes zero |
| PHerc0814 seed abstention | AP falls from `0.59718` to `0.52245` | Hide or retune the failed heuristic | Preserve failure and block the claim | Post-hoc disagreement AP is `0.63808`: disagreement is signal-bearing here |

## Practical advantage

An ordinary ensemble can improve a score while still giving the wrong meaning
to agreement or disagreement. InkSurf adds three enforceable checks:

1. correlated views are collapsed before support is counted;
2. provenance fields, not group names, determine the effective group count;
3. a submission claim requires a hashed independence audit bound to the exact
   evidence receipt.

For the current ledger the output is intentionally:

```text
NO_GO_SUBMISSION_CLAIM
software_guardrail_demonstrated = true
confirmation_eligible_receipts = 0
```

This is actionable rather than merely cautionary. It prevents reviewers from
spending time on a confidence map whose supporting votes are replicas of the
same failure mode, and it identifies the missing experiment: a G2/G3 locked
whole-region result with at least two provenance-audited evidence groups and an
independent reference.

## Interoperability boundary

InkSurf consumes aligned arrays and versioned QA receipts. It does not replace
the official tools that already provide OME-Zarr access, TIFXYZ/mesh handling,
surface rendering or model inference. The official data organization is
documented by [ScrollPrize/open-data](https://github.com/ScrollPrize/open-data),
and the maintained libraries and pipelines live in
[ScrollPrize/villa](https://github.com/ScrollPrize/villa).

The proposed contribution is the layer after those tools: dependency-aware
evidence aggregation, disagreement semantics, abstention and a machine-readable
claim ceiling.
