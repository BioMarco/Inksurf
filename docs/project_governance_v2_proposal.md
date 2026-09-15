# InkSurf project governance v2 — proposal

**Status:** approved and applied to `AGENTS.md`
**Date:** 2026-09-10

## Why revise the initial rules

The original rules correctly protected the project from regional-label leakage,
unverified geometry, opportunistic threshold tuning, and uncontrolled I/O. They
also assumed that the Grand Prize region of PHercParis4 should be the next and
primary experiment. That assumption is now too narrow.

InkSurf should be managed as a reusable method with three separate tracks:

1. a public, quantitatively evaluated tool suitable for a Progress Prize;
2. a locked discovery pipeline that may support First Letters or the Paris 4
   Title Prize;
3. a longer-term component for full-scroll/VC3D workflows.

Combining those tracks in one ROI creates incompatible rules about ground-truth
visibility, publication, target size, and acceptable human input.

## Rules that remain non-negotiable

- A regional association is not proof of ink.
- Training and evaluation regions must not overlap, including receptive-field,
  patch, neighboring-chunk, or near-duplicate leakage.
- Every transform declares source frame, destination frame, level, axis order,
  units, and uncertainty.
- Surface predictions are cues, not verified sheet geometry.
- Every material result is traceable to code, config, data version, seed, and
  immutable output.
- Heavy reads require unique-chunk, byte, time, cache, and free-space preflight.
- Negative results and false-positive failure modes are first-class outputs.
- The system must expose CT/geometry support and uncertainty rather than hiding
  them behind a single attractive score.

## Rules to revise

### 1. Replace universal blindness with partitioned blindness

Development data may be inspected and labeled. A separate validation partition
is locked before tuning, and discovery targets are frozen before any visual
inspection. Ground truth is therefore allowed where it is scientifically
necessary, but never reused as both design input and final evidence.

### 2. Replace “Grand Prize ROI first” with multi-dataset validation first

The first end-to-end benchmark should use public surfaces with known ink labels
and whole-region splits. PHercParis4 Grand Prize remains a historical stress
test, not the sole source of truth. At least one other scroll/domain is required
before claiming generality.

### 3. Treat TIFXYZ as a preferred interface, not the only internal geometry

InkSurf may accept:

- TIFXYZ grids;
- triangular/quad meshes with a declared UV parametrization;
- verified surface-coordinate fields for controlled ablations.

Every input receives a geometry confidence tier. Prize-bound output must still
be exportable and traceable to the standard format required by the target prize.

### 4. Scope the 4 cm² limit to First Letters

Four square centimeters is a submission constraint for First Letters, not a
universal research ROI. Development may use multi-scale continuous regions.
Discovery output can later be cropped to a frozen 4 cm² package if it contains
independently legible evidence.

### 5. Make GO/NO-GO criteria experiment-specific

The current `2x top-1% enrichment` and `+0.10 AP` thresholds remain the frozen
criteria for the current GP pilot. They are not universal laws. Every future
experiment preregisters its minimum effect, confidence interval, review budget,
and baseline before evaluation. A useful reduction in human review time may be
decisive even when a single global AP threshold is not.

### 6. Permit `ink_frac128` only as a named baseline

It remains prohibited as the primary decision score. It is retained as a weak
baseline so improvements are measurable and negative evidence is visible.

## Product definition

InkSurf 2.0 should implement this contract:

```text
Ink3D or compatible volumetric evidence
  + verified/graded surface geometry
  + optional CT-support and geometry-QA channels
  -> continuous UV evidence map with uncertainty
  -> connected components, skeletons, stroke-like descriptors
  -> ranked candidate packages
  -> overlays, provenance and review decisions
```

A candidate package should contain the surface identifier, UV and XYZ bounds,
input chunk manifest, component mask/skeleton, baseline scores, InkSurf score,
support diagnostics, perturbation stability, and a reproducible preview. It
must never contain an automatic claim that a component is a letter.

## Differentiation from existing community tools

InkSurf should consume or interoperate with established work instead of
reimplementing it:

- data access: `vesuvius`/official catalog tooling;
- CT support: Herculaneum Scroll Tools;
- TIFXYZ metadata and geometry QA: `tifxyz-repair`, TIFXYZ Doctor, `windcheck`;
- rendering and VC3D integration: official VC3D/Volume Cartographer tooling;
- explanation of neural ink models: Inkalyzer where useful.

The original contribution is the surface-aware structural retrieval layer:
continuity-aware fusion of volumetric evidence, calibrated ranking, stability
tests, false-positive controls, and measurable human-review yield.

## Three-track roadmap

### Track A — Progress Prize MVP (primary)

- standard TIFXYZ plus Zarr inputs;
- frozen public benchmark with known labels and region-level splits;
- raw Ink3D, Surface-only, density, and morphology baselines;
- candidate report plus static overlay accepted by existing workflows;
- quantitative retrieval metrics and a short reviewer usability study;
- Docker/CLI documentation and one-command demo on bounded data.

### Track B — locked discovery (secondary)

- select an eligible scroll/region independently of visible predictions;
- freeze code, model, config, and surface before inspection;
- keep discovery artifacts private where prize terms require it;
- package only independently legible results meeting the chosen prize rules.

### Track C — full-scroll integration (long-term)

- stream across column-scale surfaces;
- expose candidate layers in VC3D;
- measure performance, failure recovery, and annotation hours;
- support full-scroll provenance and column-level outputs.

## Immediate decision recommended

Pause expansion of the five GP volumetric candidates after the sparse TIFXYZ
geometry audit. In parallel, build the surface-map and component-ranking MVP on
a small public labeled dataset with a clean region split. This supplies the
feedback currently missing: whether InkSurf improves structural retrieval over
raw Ink3D at all. Only then spend several gigabytes on the GP pilot.

## Approval effect

Applied on 2026-09-10. `AGENTS.md` now encodes partitioned blindness,
multi-track targets, tiered geometry inputs, experiment-specific GO criteria,
and reuse of existing QA tools. The safety, provenance, leakage, coordinate,
and I/O rules remain unchanged.
