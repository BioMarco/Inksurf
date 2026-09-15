"""Evaluate fixed 16-layer CT-profile models on local DEV pairs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Callable

import numpy as np

from inksurf.benchmark_baseline import _atomic_json
from inksurf.structural_features import _atomic_csv


def profile_features(profiles: np.ndarray) -> tuple[np.ndarray, list[str]]:
    """Return fixed raw-profile and summary features without label access."""
    if profiles.ndim != 2 or profiles.shape[1] < 3:
        raise ValueError("profiles must have shape N,L with at least three layers")
    values = profiles.astype(np.float32, copy=False)
    layer_names = [f"layer_{index:02d}" for index in range(values.shape[1])]
    locations = np.arange(values.shape[1], dtype=np.float32)
    centered_locations = locations - locations.mean()
    slope = (values @ centered_locations) / float(np.square(centered_locations).sum())
    center = values[:, values.shape[1] // 4: values.shape[1] - values.shape[1] // 4].mean(axis=1)
    edges = np.concatenate((values[:, : values.shape[1] // 4], values[:, -values.shape[1] // 4:]), axis=1).mean(axis=1)
    summaries = np.column_stack((
        values.mean(axis=1), values.std(axis=1), values.min(axis=1), values.max(axis=1),
        np.ptp(values, axis=1), np.argmax(values, axis=1), slope, center - edges,
    )).astype(np.float32)
    names = layer_names + ["mean", "std", "min", "max", "range", "argmax", "slope", "center_contrast"]
    return np.column_stack((values, summaries)), names


def contiguous_fold_ids(block_ids: np.ndarray, folds: int) -> np.ndarray:
    """Assign complete 1024-pixel block rows to contiguous folds."""
    block_rows = np.asarray([int(str(value).split("_")[0][2:]) for value in block_ids])
    unique_rows = np.unique(block_rows)
    if folds < 2 or folds > len(unique_rows):
        raise ValueError("fold count must be between 2 and the number of block rows")
    assignments = np.empty(len(block_rows), dtype=np.int16)
    for fold, row_group in enumerate(np.array_split(unique_rows, folds)):
        assignments[np.isin(block_rows, row_group)] = fold
    return assignments


def _metric_intervals(
    labels: np.ndarray,
    candidate: np.ndarray,
    baseline: np.ndarray,
    blocks: np.ndarray,
    *,
    samples: int,
    seed: int,
) -> dict[str, dict[str, float | int]]:
    from sklearn.metrics import average_precision_score, roc_auc_score

    metrics: dict[str, Callable[[np.ndarray, np.ndarray], float]] = {
        "roc_auc": roc_auc_score,
        "average_precision": average_precision_score,
    }
    rng = np.random.default_rng(seed)
    unique_blocks = np.unique(blocks)
    by_block = {block: np.flatnonzero(blocks == block) for block in unique_blocks}
    values = {name: [] for name in metrics}
    for _ in range(samples):
        selected = rng.choice(unique_blocks, size=len(unique_blocks), replace=True)
        indexes = np.concatenate([by_block[block] for block in selected])
        if np.unique(labels[indexes]).size != 2:
            continue
        for name, metric in metrics.items():
            values[name].append(float(metric(labels[indexes], candidate[indexes]) - metric(labels[indexes], baseline[indexes])))
    result: dict[str, dict[str, float | int]] = {}
    for name, metric_values in values.items():
        if not metric_values:
            raise RuntimeError(f"no valid bootstrap replicates for {name}")
        low, high = np.quantile(metric_values, [0.025, 0.975])
        result[name] = {"low": float(low), "high": float(high), "valid_replicates": len(metric_values)}
    return result


def run(config_path: Path) -> dict[str, Any]:
    try:
        import tifffile
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import average_precision_score, roc_auc_score
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("install benchmark and structure dependencies") from exc

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("regime") != "DEV":
        raise ValueError("profile-model development is restricted to DEV")
    root = config_path.resolve().parent.parent
    with (root / config["pairs_csv"]).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    labels = np.asarray([int(row["label"]) for row in rows], dtype=np.uint8)
    ys = np.asarray([int(row["y"]) for row in rows], dtype=np.int32)
    xs = np.asarray([int(row["x"]) for row in rows], dtype=np.int32)
    blocks = np.asarray([row["block_id"] for row in rows])
    pair_ids = np.asarray([int(row["pair_id"]) for row in rows], dtype=np.int32)
    if len(np.unique(pair_ids)) * 2 != len(rows):
        raise ValueError("expected exactly two samples per local pair")

    volume_dir = root / config["surface_volume_directory"]
    profiles = np.empty((len(rows), len(config["surface_volume_layers"])), dtype=np.float32)
    layer_paths = []
    for column, layer in enumerate(config["surface_volume_layers"]):
        path = volume_dir / f"{int(layer):02d}.tif"
        layer_paths.append(str(path.relative_to(root)))
        image = tifffile.memmap(path)
        profiles[:, column] = image[ys, xs]
        del image
    features, feature_names = profile_features(profiles)
    baseline_map = np.load(root / config["baseline_map"], mmap_mode="r")
    baseline = np.asarray(baseline_map[ys, xs], dtype=np.float64)
    del baseline_map

    fold_ids = contiguous_fold_ids(blocks, int(config["folds"]))
    model_scores = {
        "logistic": np.full(len(rows), np.nan, dtype=np.float64),
        "hist_gradient_boosting": np.full(len(rows), np.nan, dtype=np.float64),
    }
    fold_details = []
    for fold in range(int(config["folds"])):
        test = fold_ids == fold
        test_y_min, test_y_max = int(ys[test].min()), int(ys[test].max())
        buffer = int(config["spatial_buffer_pixels"])
        train = ~test & ((ys < test_y_min - buffer) | (ys > test_y_max + buffer))
        if np.unique(labels[train]).size != 2 or np.unique(labels[test]).size != 2:
            raise RuntimeError(f"fold {fold} does not contain both classes")
        logistic_config = config["models"]["logistic"]
        logistic = make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=float(logistic_config["C"]), max_iter=int(logistic_config["max_iter"]),
                class_weight="balanced", random_state=int(config["seed"]),
            ),
        )
        boost_config = config["models"]["hist_gradient_boosting"]
        boosting = HistGradientBoostingClassifier(
            learning_rate=float(boost_config["learning_rate"]), max_iter=int(boost_config["max_iter"]),
            max_leaf_nodes=int(boost_config["max_leaf_nodes"]),
            l2_regularization=float(boost_config["l2_regularization"]),
            class_weight="balanced", random_state=int(config["seed"]),
        )
        for name, model in (("logistic", logistic), ("hist_gradient_boosting", boosting)):
            model.fit(features[train], labels[train])
            model_scores[name][test] = model.predict_proba(features[test])[:, 1]
        fold_details.append({
            "fold": fold, "test_samples": int(test.sum()), "train_samples": int(train.sum()),
            "buffer_excluded_samples": int((~test & ~train).sum()),
            "test_block_rows": sorted(set(int(str(value).split("_")[0][2:]) for value in blocks[test])),
            "test_y_range": [test_y_min, test_y_max],
        })
    if any(np.isnan(scores).any() for scores in model_scores.values()):
        raise RuntimeError("cross-fitting left samples without predictions")

    baseline_metrics = {
        "roc_auc": float(roc_auc_score(labels, baseline)),
        "average_precision": float(average_precision_score(labels, baseline)),
    }
    model_results = []
    for index, (name, scores) in enumerate(model_scores.items()):
        metrics = {
            "roc_auc": float(roc_auc_score(labels, scores)),
            "average_precision": float(average_precision_score(labels, scores)),
        }
        delta = {key: metrics[key] - baseline_metrics[key] for key in metrics}
        intervals = _metric_intervals(
            labels, scores, baseline, blocks, samples=int(config["bootstrap"]["samples"]),
            seed=int(config["bootstrap"]["seed"]) + index,
        )
        criteria = config["go_criteria"]
        passes = (
            delta["roc_auc"] >= float(criteria["minimum_auc_gain"])
            and delta["average_precision"] >= float(criteria["minimum_average_precision_gain"])
            and (not criteria["require_positive_auc_ci_lower"] or float(intervals["roc_auc"]["low"]) > 0)
            and (not criteria["require_positive_average_precision_ci_lower"] or float(intervals["average_precision"]["low"]) > 0)
        )
        model_results.append({
            "model": name, "metrics": metrics, "delta_vs_depth_std": delta,
            "paired_spatial_block_bootstrap_95ci": intervals, "passes_go_criteria": bool(passes),
        })

    best = max(model_results, key=lambda item: item["metrics"]["average_precision"])
    output_rows = []
    for index, row in enumerate(rows):
        output_rows.append({
            **row, "fold": int(fold_ids[index]), "depth_std_baseline": float(baseline[index]),
            "logistic_score": float(model_scores["logistic"][index]),
            "hist_gradient_boosting_score": float(model_scores["hist_gradient_boosting"][index]),
        })
    report = {
        "experiment_id": config["experiment_id"], "regime": "DEV",
        "geometry_tier": config["geometry_tier"], "status": "GO" if best["passes_go_criteria"] else "NO_GO",
        "coordinate_order": "Y,X", "samples": len(rows), "pairs": int(len(rows) // 2),
        "blocks": int(len(np.unique(blocks))), "features": feature_names,
        "surface_volume_layers": config["surface_volume_layers"], "surface_volume_files": layer_paths,
        "baseline": {"name": "depth_std", "metrics": baseline_metrics},
        "folds": fold_details, "models": model_results, "selected_by_dev_average_precision": best["model"],
        "go_criteria": config["go_criteria"],
        "interpretation": (
            "DEV gate passed; freeze this exact score before any locked evaluation."
            if best["passes_go_criteria"] else
            "DEV gate failed; do not generate a full-map structural claim from this profile model."
        ),
        "limitations": [
            "Labels were used to construct the DEV local pairs.",
            "Controls are distance-matched but not explicitly matched for fiber orientation or CT texture.",
            "Model selection by DEV average precision is exploratory and is not held-out evidence.",
            "G0 Surface Prediction is a volumetric cue, not verified geometry.",
        ],
        "validation_files_accessed": 0,
    }
    _atomic_csv(root / config["outputs"]["predictions_csv"], output_rows)
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
