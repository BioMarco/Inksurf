"""Audit CT support in bounded ink_9um derived chunks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .evidence_consistency import _atomic_json


def chunk_support(
    volume: np.ndarray,
    evaluation_mask: np.ndarray,
    central_range: tuple[int, int],
) -> dict[str, float | int]:
    volume = np.asarray(volume)
    mask = np.asarray(evaluation_mask, dtype=bool)
    if volume.ndim != 3 or mask.shape != volume.shape[1:]:
        raise ValueError("volume must be Z,Y,X and mask must match Y,X")
    start, stop = central_range
    if not 0 <= start < stop <= volume.shape[0]:
        raise ValueError("central range is outside the volume")
    if not mask.any():
        raise ValueError("evaluation mask is empty")
    any_support = np.any(volume > 0, axis=0)
    central_support = np.any(volume[start:stop] > 0, axis=0)
    return {
        "evaluated_pixels": int(mask.sum()),
        "any_depth_support_fraction": float(any_support[mask].mean()),
        "central_depth_support_fraction": float(central_support[mask].mean()),
        "median_nonzero_depth_fraction": float(np.median(np.mean(volume[:, mask] > 0, axis=0))),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-ink9um-ct-support/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("bounded ink_9um CT support is Track A DEV only")
    root = config_path.resolve().parent.parent
    source_path = root / config["chunk_audit_report"]
    source_hash = _sha256(source_path)
    if source_hash != config["chunk_audit_sha256"]:
        raise ValueError("chunk audit report hash mismatch")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    start, stop = map(int, config["central_depth_range_half_open"])
    criteria = config["criteria"]
    rows = []
    for item in source["chunks"]:
        path = root / item["derived"]
        with np.load(path) as archive:
            metrics = chunk_support(archive["volume"], archive["validation_mask"], (start, stop))
        passes = (
            metrics["any_depth_support_fraction"] >= float(criteria["minimum_any_depth_support_fraction"])
            and metrics["central_depth_support_fraction"] >= float(criteria["minimum_central_depth_support_fraction"])
        )
        rows.append({
            "chunk_yx": item["chunk_yx"],
            "derived_sha256": _sha256(path),
            **metrics,
            "passes": passes,
        })
    all_pass = all(item["passes"] for item in rows)
    status = "pass" if all_pass or not criteria["require_every_chunk_to_pass"] else "fail"
    report = {
        "schema_version": config["schema_version"],
        "experiment_id": config["experiment_id"],
        "track": "A",
        "regime": "DEV",
        "surface_id": config["surface_id"],
        "status": status,
        "support_source": "published extracted surface volume",
        "central_depth_range_half_open": [start, stop],
        "criteria": criteria,
        "candidate_count": len(rows),
        "passing_candidates": sum(bool(item["passes"]) for item in rows),
        "minimum_any_depth_support_fraction_observed": min(item["any_depth_support_fraction"] for item in rows),
        "minimum_central_depth_support_fraction_observed": min(item["central_depth_support_fraction"] for item in rows),
        "source_chunk_audit": config["chunk_audit_report"],
        "source_chunk_audit_sha256": source_hash,
        "chunks": rows,
        "methodological_note": "Nonzero extracted-CT support is checked only on the bounded DEV evaluation pixels; this does not validate ink.",
        "validation_files_accessed": 0,
        "discovery_files_accessed": 0,
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
