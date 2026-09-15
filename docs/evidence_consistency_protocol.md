# InkSurf Evidence Consistency Protocol

## Purpose

InkSurf 2.0 verifies whether an aligned surface-space signal is consistent
across genuinely independent evidence sources. It does not classify a small
patch as ink and it does not treat repeated perturbations of one source as
independent confirmation.

The pipeline is:

```text
official metadata
    -> source and legal audit
    -> declared registration into one UV frame
    -> within-source perturbation aggregation
    -> cross-source consensus and disagreement
    -> abstention
    -> continuous, physically scaled review regions
```

## Independence contract

Every input view has a required `independence_group`.

- Normal offsets, thresholds, tiles or test-time augmentations derived from the
  same acquisition/model belong to the same group.
- Replicate outputs trained from the same labels are not automatically
  independent; their relationship must be documented.
- A distinct scan ID is necessary for scan independence, but catalog metadata
  alone does not prove that two scans contain a co-registered common surface.
- Views in one group are reduced to one median group map before cross-group
  support is counted.
- Disagreement within one correlated model family is never interpreted as
  epistemic uncertainty by default. A labeled DEV audit and a separate locked
  confirmation must first show that larger disagreement predicts error rather
  than signal.

This prevents correlated variants from manufacturing confidence.

The PHerc0814 locked check demonstrates why this guardrail matters: disagreement
between two official seed replicas was positively associated with the ink label
and removing the highest-disagreement 20% reduced AP. Only disagreement between
declared, sufficiently independent group maps belongs in the abstention gate.

## Numerical outputs

`inksurf.evidence_consistency` produces five aligned arrays:

- `consensus`: median of the independent group maps;
- `support_fraction`: fraction of valid groups above the frozen evidence
  threshold;
- `disagreement`: range between independent group maps;
- `valid_independent_groups`: number of valid groups at each pixel;
- `accepted`: pixels passing evidence, support, disagreement and minimum-group
  gates.

Acceptance means only consistency under the declared rules. It is not a claim
of physical ink.

## Input formats

The first implementation reads local `.npy`, `.npz`, TIFF and Zarr arrays. All
views must already be aligned, have identical shape and declare an explicit
`value_range`. TIFF and Zarr support use the `benchmark` optional dependencies.
Registration is intentionally outside this module: InkSurf must consume a
versioned transform and its validation report rather than hiding resampling
inside the consensus calculation.

Example configuration fragment:

```json
{
  "schema_version": "inksurf-evidence-consistency/1.0",
  "experiment_id": "example-dev",
  "track": "A",
  "regime": "DEV",
  "geometry_tier": "G2",
  "views": [
    {
      "view_id": "scan-a-offsets-median-input-1",
      "independence_group": "scan-a",
      "path": "data/aligned/scan_a_0.tif",
      "value_range": [0, 255]
    },
    {
      "view_id": "scan-b-offsets-median-input-1",
      "independence_group": "scan-b",
      "path": "data/aligned/scan_b_0.tif",
      "value_range": [0, 255]
    }
  ],
  "thresholds": {
    "evidence": 0.5,
    "minimum_independent_groups": 2,
    "minimum_support_fraction": 1.0,
    "maximum_disagreement": 0.2
  },
  "outputs": {
    "maps_npz": "results/example/evidence_maps.npz",
    "report_json": "results/example/report.json"
  }
}
```

Thresholds in this example are illustrative. Every real experiment must freeze
them before inspecting its held-out target.

## Phase gates

### Phase 0 — metadata

The catalog source, commit and SHA256 are frozen. The phase transfers no volume
data. A metadata GO remains conditional until same-surface overlap, transforms,
registration error and independent evidence are verified. The frozen catalog
audit currently finds two same-label Paris 4 surfaces across source volumes,
but zero pairs of ink outputs derived from distinct source volumes. Existing
ink predictions therefore cannot be counted as cross-acquisition consensus.

### Phase 1 — bounded DEV

Use known readable regions and negative controls. Compare against the best
single source. Primary outcomes are AP, false positives per cm², stability and
abstention coverage. Review images must be physically scaled and large enough
to expose rows or context; micro-patch lay review is prohibited.

### Phase 2 — held out

Freeze code, transforms, thresholds and region split before accessing the
held-out surface. Require a spatially independent unit and confidence intervals.

### Discovery

Discovery inputs and outputs must remain separate from public DEV artifacts and
follow the applicable prize confidentiality and publication terms. A stable
signal is not a First Letters or Title claim until it is legible and the full
submission requirements are satisfied.
