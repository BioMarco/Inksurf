# Physical false-positive protocol

`inksurf-physical-fp-audit` measures review burden on a verified surface in
physical units. It reports false-positive area and 4-connected false-positive
regions per evaluated negative cm².

The command requires G2 or G3 geometry, a binary accepted map, a binary
reference-positive map, an evaluation-validity mask and surface area in µm².
Area may be a constant only when that assumption is justified by the verified
geometry. For distorted or irregular mappings, provide a per-pixel area map
derived from the surface Jacobian or mesh faces.

Minimum component area is frozen in mm². Components smaller than that threshold
remain in total false-positive area but are excluded from the retained-region
rate. This separates speckle burden from regions large enough to consume human
review time.

Example configuration shape:

```json
{
  "schema_version": "inksurf-physical-fp-audit/1.0",
  "experiment_id": "example-g2-dev",
  "track": "A",
  "regime": "DEV",
  "geometry_tier": "G2",
  "inputs": {
    "accepted": {"path": "data/accepted.npy"},
    "reference_positive": {"path": "data/reference.npy"},
    "valid_mask": {"path": "data/valid.npy"},
    "pixel_area_um2": {"path": "data/pixel_area_um2.npy"}
  },
  "thresholds": {"minimum_component_area_mm2": 0.01},
  "output_report": "results/example/physical_fp_report.json"
}
```

The reference must be independently governed and its visibility regime must be
declared elsewhere in the experiment package. A low rate against a supplied
reference is not by itself proof of ink, reference quality or submission
eligibility.
