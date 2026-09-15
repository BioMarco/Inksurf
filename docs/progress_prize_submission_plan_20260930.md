# InkSurf Progress Prize submission sprint

**Target deadline:** 30 September 2026, 23:59 Pacific.

**Primary target:** monthly Progress Prize. First Letters and Paris 4 Title are
separate locked-discovery tracks and are not claimed by this sprint.

## Submission thesis

InkSurf is a fail-closed evidence and provenance layer for surface-based ink
workflows. It prevents correlated predictions, invalid surfaces and unverified
cross-scan mappings from manufacturing confidence; it emits consensus,
disagreement and abstention maps in standard formats.

## Required evidence before submission

1. ~~Reproduce a seating result on a bounded PHerc0139 DEV crop.~~ Completed:
   scores `15.02/17.54`, coverage `0.94/0.80`.
2. ~~Compare best single-source ink evidence with naive fusion and InkSurf.~~
   Completed on bounded DEV and locked PHerc0814. The detector transfers, but
   the seed-disagreement abstention rule fails the locked check.
3. Measure AP, false positives per cm2, abstention coverage and stability on
   spatially separated known-text and blank regions. AP, coverage and spatial
   bootstrap are implemented. Physical false area is now measured on 12 bounded
   G2 DEV chunks; a continuous-region component rate and independent reference
   are still missing.
4. ~~Freeze and run one untouched scroll-surface validation unit.~~ Completed:
   PHerc0814, 2/4 gates, `NO-GO`. The negative outcome is preserved.
5. ~~Package CLI, examples, machine-readable provenance, permissive license and
   an end-to-end walkthrough.~~ Completed in the private release candidate.
6. Prepare an upstream integration example and request community feedback.

Current status: the geometry and cross-scan repeatability gates pass, but the
first locked labeled check rejects within-family disagreement as an uncertainty
proxy. The post-hoc audit shows why: it is positively associated with ink on
PHerc0814. The critical path is now a reviewer-facing **evidence independence
audit**, not a claim that seed ensembling already solves abstention.

## Submission decision after locked validation

The stronger and more defensible Progress Prize thesis is now:

> InkSurf prevents correlated replicas and repeatable acquisition anatomy from
> being mistaken for independent confidence, tests whether disagreement really
> predicts error, and fails closed with machine-readable provenance.

This is candidable only if the final package demonstrates a practical advantage
over ordinary ensemble metrics on real Vesuvius data and has one concise,
end-to-end workflow. The PHerc0814 failure is useful evidence for that guardrail,
not a result to hide or retune.

Next implementation sequence:

1. ~~consolidate the independence-group and disagreement diagnostics behind one
   public audit command;~~ completed;
2. ~~add a small synthetic example plus the preserved real-data receipts;~~
   completed;
3. ~~produce a comparison table: naive repeatability, naive seed abstention and
   InkSurf fail-closed verdict;~~ completed;
4. integrate rather than duplicate official/community CT-support, seating and
   dual-energy outputs;
5. prepare the open-source walkthrough and submission draft for owner review.

The first provenance-correct cross-model candidate has now been audited end to
end. Its TIFXYZ correspondence passes, but it has zero labeled common-support
pixels, so score comparison is blocked. The remaining bounded search is a
metadata census of all `ink_9um` source declarations; if that finds no eligible
pair, the cross-model confirmation route stops and the submission remains an
auditor/validator contribution.

## Stop conditions

- no G2 surface or reproducible seating;
- no independent evidence groups;
- no improvement over the best single source;
- unresolved train/evaluation overlap;
- results require subjective interpretation of micro-patches.

If the fusion hypothesis fails, submit only if the audit tool itself exposes a
reproducible, actionable failure in a real workflow and demonstrates an
advantage over existing provenance checks.

## External actions requiring owner review

Repository publication, GitHub issues or pull requests, community announcements
and the official submission form will be prepared locally first. They must not
be sent under the owner's identity without a final review of content, licensing
and prize confidentiality.
