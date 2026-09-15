"""Validate and summarize an exported InkSurf blinded-review session."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from inksurf.benchmark_baseline import _atomic_json


def validate_results(
    payload: dict[str, Any], queue: list[dict[str, Any]], options: list[str], experiment_id: str
) -> list[str]:
    errors = []
    if payload.get("experiment_id") != experiment_id:
        errors.append("experiment_id mismatch")
    results = payload.get("results")
    if not isinstance(results, list):
        return errors + ["results must be a list"]
    expected = {item["candidate_id"] for item in queue}
    observed = [item.get("candidate_id") for item in results]
    if len(observed) != len(expected) or set(observed) != expected:
        errors.append("review must contain every queued candidate exactly once")
    if len(observed) != len(set(observed)):
        errors.append("duplicate candidate reviews")
    for item in results:
        if item.get("response") not in options:
            errors.append(f"invalid response for {item.get('candidate_id')}")
        confidence = item.get("confidence")
        if not isinstance(confidence, (int, float)) or not 1 <= confidence <= 5:
            errors.append(f"invalid confidence for {item.get('candidate_id')}")
        elapsed = item.get("elapsed_seconds")
        if not isinstance(elapsed, (int, float)) or elapsed < 0:
            errors.append(f"invalid elapsed time for {item.get('candidate_id')}")
    return errors


def run(config_path: Path, review_json: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    queue_path = root / config["local_output_directory"] / "queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    payload = json.loads(review_json.read_text(encoding="utf-8"))
    errors = validate_results(payload, queue, config["response_options"], config["experiment_id"])
    if errors:
        raise ValueError("; ".join(errors))
    results = payload["results"]
    counts = Counter(item["response"] for item in results)
    elapsed = np.asarray([float(item["elapsed_seconds"]) for item in results])
    plausible = counts.get("plausible_structure", 0)
    report = {
        "experiment_id": config["experiment_id"], "track": config["track"], "regime": config["regime"],
        "geometry_tier": config["geometry_tier"], "status": "human_review_complete",
        "completed_at": payload.get("completed_at"), "reviewed_candidates": len(results),
        "response_counts": dict(counts), "plausible_structure_yield": plausible / len(results),
        "total_review_seconds": float(elapsed.sum()), "median_review_seconds": float(np.median(elapsed)),
        "p90_review_seconds": float(np.quantile(elapsed, 0.9)),
        "mean_confidence": float(np.mean([float(item["confidence"]) for item in results])),
        "detailed_review_storage": "local_ignored", "validation_files_accessed": 0,
        "interpretation_warning": "A single DEV reviewer measures workflow utility, not physical ink accuracy or inter-rater reliability.",
    }
    _atomic_json(root / config["outputs"]["review_results_report_json"], report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--review-json", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config, args.review_json), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
