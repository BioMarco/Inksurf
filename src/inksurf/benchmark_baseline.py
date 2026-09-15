"""Evaluate frozen region-level raw-prediction baselines on a DEV audit table."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

import numpy as np


def average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=bool)
    scores = np.asarray(scores, dtype=float)
    positives = int(labels.sum())
    if labels.ndim != 1 or scores.shape != labels.shape or positives == 0:
        raise ValueError("AP requires aligned 1D arrays with at least one positive")
    order = np.argsort(-scores, kind="stable")
    y = labels[order]
    s = scores[order]
    ends = np.r_[np.flatnonzero(s[:-1] != s[1:]), len(s) - 1]
    tp = np.cumsum(y)[ends]
    fp = (ends + 1) - tp
    recall = tp / positives
    precision = tp / (tp + fp)
    return float(np.sum(np.diff(np.r_[0.0, recall]) * precision))


def review_metrics(
    scores: np.ndarray,
    ink_pixels: np.ndarray,
    valid_pixels: np.ndarray,
    fraction: float,
) -> dict[str, float | int]:
    if not 0 < fraction <= 1:
        raise ValueError("review fraction must be in (0, 1]")
    count = max(1, int(math.ceil(len(scores) * fraction)))
    order = np.argsort(-scores, kind="stable")[:count]
    selected_ink = int(ink_pixels[order].sum())
    selected_valid = int(valid_pixels[order].sum())
    global_precision = float(ink_pixels.sum() / valid_pixels.sum())
    selected_precision = float(selected_ink / selected_valid) if selected_valid else 0.0
    return {
        "review_fraction": fraction,
        "regions_reviewed": count,
        "reference_ink_recall": float(selected_ink / ink_pixels.sum()) if ink_pixels.sum() else 0.0,
        "reference_ink_precision": selected_precision,
        "enrichment": selected_precision / global_precision if global_precision else 0.0,
    }


def _load_regions(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    return [row for row in rows if row["eligible"].lower() == "true"]


def _bootstrap_interval(
    rows: list[dict[str, Any]],
    metric: Callable[[list[dict[str, Any]]], float],
    *,
    block_size: int,
    samples: int,
    seed: int,
) -> dict[str, float]:
    groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in rows:
        key = (int(row["y0"]) // block_size, int(row["x0"]) // block_size)
        groups.setdefault(key, []).append(row)
    blocks = list(groups.values())
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(samples):
        sample: list[dict[str, Any]] = []
        for index in rng.integers(0, len(blocks), size=len(blocks)):
            sample.extend(blocks[int(index)])
        try:
            values.append(metric(sample))
        except ValueError:
            continue
    if not values:
        raise RuntimeError("all bootstrap replicates were invalid")
    low, high = np.quantile(values, [0.025, 0.975])
    return {"low": float(low), "high": float(high), "valid_replicates": len(values)}


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    rows = _load_regions(root / config["regions_csv"])
    threshold = int(config["positive_region_min_ink_pixels"])
    ink = np.asarray([int(row["ink_pixels"]) for row in rows], dtype=np.int64)
    valid = np.asarray([int(row["valid_pixels"]) for row in rows], dtype=np.int64)
    labels = ink >= threshold
    results: list[dict[str, Any]] = []
    bootstrap = config["bootstrap"]
    baseline_name = config.get("baseline_score")
    baseline_values = (
        np.asarray([float(row[baseline_name]) for row in rows], dtype=float) if baseline_name else None
    )
    review_baseline_name = (
        config["review_baseline_score"] if "review_baseline_score" in config else baseline_name
    )
    review_baseline_values = (
        np.asarray([float(row[review_baseline_name]) for row in rows], dtype=float)
        if review_baseline_name
        else None
    )
    review_baseline_scores = config.get("review_baseline_scores")
    for score_name in config["score_columns"]:
        scores = np.asarray([float(row[score_name]) for row in rows], dtype=float)

        def ap_for(sample_rows: list[dict[str, Any]]) -> float:
            sample_ink = np.asarray([int(row["ink_pixels"]) for row in sample_rows])
            sample_labels = sample_ink >= threshold
            sample_scores = np.asarray([float(row[score_name]) for row in sample_rows])
            return average_precision(sample_labels, sample_scores)

        review = [review_metrics(scores, ink, valid, float(f)) for f in config["review_fractions"]]
        item = {
            "score": score_name,
            "average_precision": average_precision(labels, scores),
            "average_precision_block_bootstrap_95ci": _bootstrap_interval(
                rows,
                ap_for,
                block_size=int(bootstrap["block_size"]),
                samples=int(bootstrap["samples"]),
                seed=int(bootstrap["seed"]),
            ),
            "review": review,
        }
        if baseline_values is not None:
            baseline_ap = average_precision(labels, baseline_values)

            def delta_for(sample_rows: list[dict[str, Any]]) -> float:
                sample_ink = np.asarray([int(row["ink_pixels"]) for row in sample_rows])
                sample_labels = sample_ink >= threshold
                candidate = np.asarray([float(row[score_name]) for row in sample_rows])
                baseline = np.asarray([float(row[baseline_name]) for row in sample_rows])
                return average_precision(sample_labels, candidate) - average_precision(sample_labels, baseline)

            item["delta_average_precision_vs_baseline"] = item["average_precision"] - baseline_ap
            item["delta_average_precision_block_bootstrap_95ci"] = _bootstrap_interval(
                rows,
                delta_for,
                block_size=int(bootstrap["block_size"]),
                samples=int(bootstrap["samples"]),
                seed=int(bootstrap["seed"]),
            )
            for review_item in review if review_baseline_values is not None or review_baseline_scores else []:
                fraction = float(review_item["review_fraction"])
                fraction_key = str(fraction)
                fraction_baseline_name = (
                    review_baseline_scores[fraction_key] if review_baseline_scores else review_baseline_name
                )
                fraction_baseline_values = np.asarray(
                    [float(row[fraction_baseline_name]) for row in rows], dtype=float
                )
                baseline_review = review_metrics(fraction_baseline_values, ink, valid, fraction)
                review_item["baseline_score"] = fraction_baseline_name
                review_item["delta_enrichment_vs_baseline"] = (
                    float(review_item["enrichment"]) - float(baseline_review["enrichment"])
                )

                def enrichment_delta(sample_rows: list[dict[str, Any]], fraction: float = fraction) -> float:
                    candidate = np.asarray([float(row[score_name]) for row in sample_rows])
                    baseline = np.asarray([float(row[fraction_baseline_name]) for row in sample_rows])
                    sample_ink = np.asarray([int(row["ink_pixels"]) for row in sample_rows])
                    sample_valid = np.asarray([int(row["valid_pixels"]) for row in sample_rows])
                    return float(review_metrics(candidate, sample_ink, sample_valid, fraction)["enrichment"]) - float(
                        review_metrics(baseline, sample_ink, sample_valid, fraction)["enrichment"]
                    )

                review_item["delta_enrichment_block_bootstrap_95ci"] = _bootstrap_interval(
                    rows,
                    enrichment_delta,
                    block_size=int(bootstrap["block_size"]),
                    samples=int(bootstrap["samples"]),
                    seed=int(bootstrap["seed"]),
                )
        results.append(item)
    best = max(results, key=lambda item: item["average_precision"])
    report = {
        "experiment_id": config["experiment_id"],
        "status": "dev_ranking_ablation_complete_validation_locked",
        "track": "A",
        "regime": "DEV",
        "geometry_tier": "G0",
        "region_size": int(config["region_size"]),
        "positive_region_min_ink_pixels": threshold,
        "regions": len(rows),
        "positive_regions": int(labels.sum()),
        "negative_regions": int((~labels).sum()),
        "bootstrap": bootstrap,
        "results": results,
        "baseline_score": baseline_name,
        "review_baseline_score": review_baseline_name,
        "review_baseline_scores": review_baseline_scores,
        "best_dev_score": best["score"],
        "warning": config.get(
            "reference_warning",
            "DEV-only model-selection evidence using pseudo-label-refined reference annotations; not a physical-ink or generalisation claim.",
        ),
    }
    output = root / config["output_report"]
    _atomic_json(output, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
