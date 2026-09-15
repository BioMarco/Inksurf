"""Run a small, deterministic evidence-independence demonstration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .cross_scan_consistency import atomic_npz
from .evidence_consistency import combine_evidence
from .seating_reproduce import _atomic_json


def build_demo(seed: int = 7, shape: tuple[int, int] = (64, 64)) -> tuple[list[np.ndarray], np.ndarray, np.ndarray]:
    """Create one shared signal and one correlated single-group artifact."""
    rng = np.random.default_rng(seed)
    reference = np.zeros(shape, dtype=bool)
    reference[16:20, 10:50] = True
    reference[36:40, 14:54] = True
    artifact = np.zeros(shape, dtype=bool)
    artifact[7:12, 44:59] = True

    noise = lambda: rng.normal(0.0, 0.015, size=shape).astype(np.float32)
    group_a_1 = np.clip(0.08 + noise() + 0.84 * reference + 0.86 * artifact, 0.0, 1.0)
    group_a_2 = np.clip(0.09 + noise() + 0.82 * reference + 0.84 * artifact, 0.0, 1.0)
    group_b = np.clip(0.10 + noise() + 0.78 * reference, 0.0, 1.0)
    return [group_a_1, group_a_2, group_b], reference, artifact


def run(output_dir: Path, seed: int = 7) -> dict:
    views, reference, artifact = build_demo(seed=seed)
    maps = combine_evidence(
        views,
        ["model-family-a", "model-family-a", "independent-source-b"],
        evidence_threshold=0.6,
        minimum_independent_groups=2,
        minimum_support_fraction=1.0,
        maximum_disagreement=0.25,
    )
    accepted = maps["accepted"]
    true_positive = int((accepted & reference).sum())
    report = {
        "schema_version": "inksurf-synthetic-demo/1.0",
        "status": "complete",
        "seed": seed,
        "shape_yx": list(reference.shape),
        "view_count": 3,
        "independent_group_count": 2,
        "reference_pixels": int(reference.sum()),
        "single_group_artifact_pixels": int(artifact.sum()),
        "accepted_pixels": int(accepted.sum()),
        "accepted_reference_pixels": true_positive,
        "accepted_artifact_pixels": int((accepted & artifact).sum()),
        "precision": float(true_positive / accepted.sum()) if accepted.any() else 0.0,
        "recall": float(true_positive / reference.sum()),
        "claim": "Synthetic behavior check only; it is not evidence about papyrus ink.",
    }
    output_dir = output_dir.resolve()
    atomic_npz(output_dir / "maps.npz", reference=reference, artifact=artifact, **maps)
    _atomic_json(output_dir / "report.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results/demo"))
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.output_dir, args.seed), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
