"""Spatially cross-fit a shallow multivariate DEV ranking baseline."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from inksurf.benchmark_baseline import _atomic_json, _bootstrap_interval, average_precision, review_metrics
from inksurf.structural_features import _atomic_csv


def assign_vertical_folds(x0: np.ndarray, folds: int) -> np.ndarray:
    unique = np.unique(x0)
    if folds < 2 or unique.size < folds:
        raise ValueError("not enough spatial columns for requested folds")
    assignment = np.empty(x0.shape, dtype=np.int64)
    for fold, columns in enumerate(np.array_split(unique, folds)):
        assignment[np.isin(x0, columns)] = fold
    return assignment


def run(config_path: Path) -> dict[str, Any]:
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("install structure dependencies with pip install '.[structure]'") from exc
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("regime") != "DEV":
        raise ValueError("shallow baseline is restricted to DEV")
    root = config_path.resolve().parent.parent
    with (root / config["regions_csv"]).open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row["eligible"].lower() == "true"]
    features = np.asarray([[float(row[name]) for name in config["feature_columns"]] for row in rows])
    ink = np.asarray([int(row["ink_pixels"]) for row in rows])
    valid = np.asarray([int(row["valid_pixels"]) for row in rows])
    labels = ink >= int(config["positive_region_min_ink_pixels"])
    x0 = np.asarray([int(row["x0"]) for row in rows])
    folds = assign_vertical_folds(x0, int(config["folds"]))
    scores = np.full(len(rows), np.nan, dtype=float)
    fold_reports = []
    buffer_distance = int(config["buffer_columns"]) * int(config["region_size"])
    for fold in range(int(config["folds"])):
        test = folds == fold
        test_x = np.unique(x0[test])
        buffered = np.min(np.abs(x0[:, None] - test_x[None, :]), axis=1) <= buffer_distance
        train = ~test & ~buffered
        if np.unique(labels[train]).size != 2 or np.unique(labels[test]).size != 2:
            raise ValueError(f"fold {fold} lacks both classes")
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=float(config["logistic_c"]), class_weight=config["class_weight"],
                max_iter=2000, random_state=int(config["seed"]), solver="liblinear",
            ),
        )
        model.fit(features[train], labels[train])
        scores[test] = model.predict_proba(features[test])[:, 1]
        fold_reports.append({
            "fold": fold, "train_regions": int(train.sum()), "test_regions": int(test.sum()),
            "test_x_min": int(x0[test].min()), "test_x_max": int(x0[test].max()),
            "excluded_buffer_regions": int((~test & buffered).sum()),
        })
    if not np.isfinite(scores).all():
        raise RuntimeError("cross-fit predictions are incomplete")
    for row, fold, score in zip(rows, folds, scores, strict=True):
        row["spatial_fold"] = int(fold)
        row["shallow_crossfit_score"] = float(score)
    baseline_name = config["ap_baseline_score"]
    baseline = np.asarray([float(row[baseline_name]) for row in rows])

    def ap_delta(sample: list[dict[str, Any]]) -> float:
        sample_labels = np.asarray([int(row["ink_pixels"]) >= int(config["positive_region_min_ink_pixels"]) for row in sample])
        candidate = np.asarray([float(row["shallow_crossfit_score"]) for row in sample])
        reference = np.asarray([float(row[baseline_name]) for row in sample])
        return average_precision(sample_labels, candidate) - average_precision(sample_labels, reference)

    bootstrap = config["bootstrap"]
    reviews = []
    for fraction in (0.01, 0.05, 0.10):
        key = str(fraction)
        reference_name = config["review_baseline_scores"][key]
        reference = np.asarray([float(row[reference_name]) for row in rows])
        candidate_result = review_metrics(scores, ink, valid, fraction)
        reference_result = review_metrics(reference, ink, valid, fraction)

        def review_delta(sample: list[dict[str, Any]], fraction: float = fraction, reference_name: str = reference_name) -> float:
            sample_ink = np.asarray([int(row["ink_pixels"]) for row in sample])
            sample_valid = np.asarray([int(row["valid_pixels"]) for row in sample])
            candidate = np.asarray([float(row["shallow_crossfit_score"]) for row in sample])
            reference_scores = np.asarray([float(row[reference_name]) for row in sample])
            return float(review_metrics(candidate, sample_ink, sample_valid, fraction)["enrichment"]) - float(
                review_metrics(reference_scores, sample_ink, sample_valid, fraction)["enrichment"]
            )

        candidate_result["baseline_score"] = reference_name
        candidate_result["delta_enrichment_vs_baseline"] = float(candidate_result["enrichment"]) - float(reference_result["enrichment"])
        candidate_result["delta_enrichment_block_bootstrap_95ci"] = _bootstrap_interval(
            rows, review_delta, block_size=int(bootstrap["block_size"]),
            samples=int(bootstrap["samples"]), seed=int(bootstrap["seed"]),
        )
        reviews.append(candidate_result)
    ap = average_precision(labels, scores)
    report = {
        "experiment_id": config["experiment_id"], "regime": "DEV",
        "status": "spatial_crossfit_shallow_baseline_complete_validation_locked",
        "regions": len(rows), "positive_regions": int(labels.sum()), "folds": fold_reports,
        "feature_columns": config["feature_columns"], "ap_baseline_score": baseline_name,
        "average_precision": ap, "baseline_average_precision": average_precision(labels, baseline),
        "delta_average_precision_vs_baseline": ap - average_precision(labels, baseline),
        "delta_average_precision_block_bootstrap_95ci": _bootstrap_interval(
            rows, ap_delta, block_size=int(bootstrap["block_size"]),
            samples=int(bootstrap["samples"]), seed=int(bootstrap["seed"]),
        ),
        "review": reviews,
        "warning": "DEV-only cross-fit estimate. Vertical test strips are non-overlapping; one adjacent region column is excluded from training.",
    }
    _atomic_csv(root / config["outputs"]["predictions_csv"], rows)
    _atomic_json(root / config["outputs"]["report_json"], report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
