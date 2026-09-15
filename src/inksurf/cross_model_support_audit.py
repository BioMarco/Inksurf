"""Measure common raster support before any cross-model score comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .evidence_consistency import _atomic_json


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resample_support(mask: np.ndarray, shape: tuple[int, int], policy: str) -> np.ndarray:
    mask = np.asarray(mask, dtype=bool)
    if mask.ndim != 2 or min(mask.shape) == 0 or min(shape) == 0:
        raise ValueError("support mask and output shape must be non-empty 2D")
    output = np.zeros(shape, dtype=bool)
    if policy == "center":
        ys = np.minimum(((np.arange(shape[0]) + 0.5) * mask.shape[0] / shape[0]).astype(int), mask.shape[0] - 1)
        xs = np.minimum(((np.arange(shape[1]) + 0.5) * mask.shape[1] / shape[1]).astype(int), mask.shape[1] - 1)
        return mask[np.ix_(ys, xs)]
    if policy not in {"any", "all"}:
        raise ValueError("policy must be center, any or all")
    integral = np.pad(mask.astype(np.int64), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    for y in range(shape[0]):
        y0 = math.floor(y * mask.shape[0] / shape[0])
        y1 = math.ceil((y + 1) * mask.shape[0] / shape[0])
        for x in range(shape[1]):
            x0 = math.floor(x * mask.shape[1] / shape[1])
            x1 = math.ceil((x + 1) * mask.shape[1] / shape[1])
            count = integral[y1, x1] - integral[y0, x1] - integral[y1, x0] + integral[y0, x0]
            output[y, x] = count > 0 if policy == "any" else count == (y1 - y0) * (x1 - x0)
    return output


def run(config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-cross-model-support-audit/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("support audit is Track A DEV only")
    root = config_path.resolve().parent.parent
    chunk_path = root / config["chunk_audit_report"]
    fetch_path = root / config["tiff_fetch_report"]
    if _sha256(chunk_path) != config["chunk_audit_sha256"]:
        raise ValueError("chunk audit hash mismatch")
    if _sha256(fetch_path) != config["tiff_fetch_sha256"]:
        raise ValueError("TIFF fetch hash mismatch")
    chunks = json.loads(chunk_path.read_text(encoding="utf-8"))["chunks"]
    fetch = json.loads(fetch_path.read_text(encoding="utf-8"))
    artifact_arrays = []
    for artifact in fetch["outputs"]:
        path = root / artifact["output"]
        if _sha256(path) != artifact["sha256"]:
            raise ValueError("fetched ROI archive hash mismatch")
        artifact_arrays.append(np.load(path))
    if len(artifact_arrays) < 2:
        raise ValueError("at least two raster artifacts are required")
    policies = ("all", "center", "any")
    totals = {policy: {"eligible_pixels": 0, "eligible_ink_pixels": 0} for policy in policies}
    rows = []
    for index, chunk in enumerate(chunks):
        derived = np.load(root / chunk["derived"])
        evaluation = np.asarray(derived["validation_mask"], dtype=bool)
        ink = np.asarray(derived["inklabels"], dtype=bool)
        supports = {
            policy: np.logical_and.reduce([
                resample_support(archive[f"roi_{index:02d}"] > 0, evaluation.shape, policy)
                for archive in artifact_arrays
            ])
            for policy in policies
        }
        metrics = {}
        for policy, support in supports.items():
            eligible = evaluation & support
            metrics[policy] = {
                "eligible_pixels": int(eligible.sum()),
                "eligible_ink_pixels": int((eligible & ink).sum()),
                "evaluation_coverage": float(eligible.sum() / evaluation.sum()) if evaluation.any() else 0.0,
            }
            totals[policy]["eligible_pixels"] += metrics[policy]["eligible_pixels"]
            totals[policy]["eligible_ink_pixels"] += metrics[policy]["eligible_ink_pixels"]
        rows.append({"chunk_yx": chunk["chunk_yx"], "metrics": metrics})
    for policy in policies:
        eligible = totals[policy]["eligible_pixels"]
        totals[policy]["ink_prevalence"] = (
            totals[policy]["eligible_ink_pixels"] / eligible if eligible else None
        )
    center_chunks = sum(row["metrics"]["center"]["eligible_pixels"] > 0 for row in rows)
    report = {
        "schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
        "track": "A", "regime": "DEV", "geometry_tier": "G1",
        "status": "GO_REGISTRATION_AUDIT" if center_chunks >= int(config["minimum_supported_chunks"]) else "NO_GO_INSUFFICIENT_COMMON_SUPPORT",
        "roi_count": len(rows), "center_supported_chunk_count": center_chunks,
        "minimum_supported_chunks": int(config["minimum_supported_chunks"]),
        "threshold_note": config.get("threshold_note"),
        "totals": totals, "chunks": rows,
        "interpretation_limit": "Support only. Normalized raster mapping is not G2 registration and no score agreement was measured.",
    }
    _atomic_json(root / config["output_report"], report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
