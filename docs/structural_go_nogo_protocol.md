# InkSurf structural GO/NO-GO protocol

**Protocol version:** 1.0
**Freeze candidate:** 2026-09-10
**Coordinate convention:** `Z,Y,X` for arrays; TIFXYZ pixels contain `X,Y,Z`

## Intended contribution

InkSurf is a surface-aware candidate miner and false-positive mitigation layer.
It converts volumetric Ink3D evidence into continuous, ranked surface objects
that a human can inspect. It does not claim to unroll a whole scroll, perform
OCR, or establish that a regional signal is genuine ink.

The nearest current prize target is a Progress Prize: a modular tool accepting
community formats, demonstrated quantitatively on public data, and useful to
annotation or ink-detection workflows. A successful candidate may also support
a First Letters submission, but only if a held-out surface contains independently
legible letters and meets the official submission requirements.

## Blind ROI proposal

The proposal stage may use only:

1. the preserved 106,749-chunk Grand Prize occupancy mask in the 2023 frame;
2. the documented 2023-to-2026 affine;
3. array metadata required for bounds and I/O planning.

It must not inspect the Grand Prize banner, Ink3D values, Surface Prediction
values, or visual labels. Candidate centers are density maxima after transform
to level 3, with deterministic spatial non-maximum suppression. These are search
locations, not verified surfaces.

## Surface freeze gate

Before any volumetric scan, each candidate must pass all of the following:

- resolve a published TIFXYZ/mesh and immutable dataset identifier;
- recompute finite XYZ coverage from the coordinate TIFFs rather than trusting
  `meta.json` bounds alone;
- record the TIFXYZ source frame/level and convert `X,Y,Z` pixels explicitly to
  array `Z,Y,X` coordinates;
- reject invalid pixels, out-of-bounds points, foldovers, discontinuities, and
  likely sheet jumps;
- verify local papyrus support in CT independently of the Surface Prediction;
- freeze a UV rectangle no larger than 4 cm² without consulting the banner;
- enumerate exact chunk keys and raw/compressed byte estimates for Ink3D,
  Surface Prediction, and CT; verify free space and write a cache manifest.

Failure of a candidate advances to the next predeclared candidate; it does not
permit tuning on Ink3D or banner appearance.

## Frozen comparisons

The primary comparison is InkSurf versus raw Ink3D. Secondary controls are
Surface-only and matched morphology-only. Training and evaluation use whole
spatial regions with a buffer at least as wide as the largest receptive field;
no overlapping patch or neighboring chunk may cross a split.

Metrics:

- region-level average precision with uncertainty;
- top-k enrichment with cluster/bootstrap confidence intervals;
- component continuity and skeleton length beyond patch scale;
- stability under score-threshold and surface-offset perturbations;
- human review yield and time per accepted candidate.

## Decision rule

GO requires all of:

- at least 2.0x enrichment in the top 1% versus raw Ink3D;
- at least +0.10 absolute region-level AP versus raw Ink3D;
- continuity beyond the patch scale;
- stability to predeclared threshold and surface-offset perturbations;
- consistent direction on held-out whole regions with spatial buffers.

If any mandatory criterion fails, the outcome is NO-GO for structural ink
mining on this configuration. The documented pivot is a prediction-consistency
or surface/CT quality validator; no threshold may be relaxed after revealing
the reference image.

## Reproducibility artifacts

- config: `configs/structural_roi_preflight.json`;
- command: `PYTHONPATH=src python -m inksurf.roi_preflight --config configs/structural_roi_preflight.json`;
- candidates: `results/structural_roi_preflight/candidate_centers.csv`;
- machine-readable report: `results/structural_roi_preflight/preflight_report.json`;
- unit tests: `PYTHONPATH=src python -m unittest discover -s tests -v`.

## Catalog-audit outcome

The metadata-only audit resolved 80 Paris 4 segments at 2.4 µm. All 25 top-five
candidate/segment associations had zero point-to-bbox distance, demonstrating
that the published `meta.json` boxes are too broad for surface selection. This
stage is recorded as `bbox_shortlist_only`. The next permitted read is bounded
TIFF-header inspection followed by pre-budgeted sparse sampling of finite
`x.tif`, `y.tif`, and `z.tif` pixels.
