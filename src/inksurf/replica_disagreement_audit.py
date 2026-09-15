"""Audit whether within-family replica disagreement behaves like uncertainty."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .benchmark_baseline import average_precision
from .seating_reproduce import _atomic_json


def disagreement_summary(
    predictions: np.ndarray,
    labels: np.ndarray,
    valid_mask: np.ndarray,
    *,
    bins: int = 10,
) -> dict:
    """Describe disagreement without fitting a threshold or changing a score."""
    predictions = np.asarray(predictions, dtype=np.float32)
    labels = np.asarray(labels, dtype=bool)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if predictions.ndim < 2 or predictions.shape[0] != 2:
        raise ValueError("exactly two replica prediction maps are required")
    if predictions.shape[1:] != labels.shape or labels.shape != valid_mask.shape:
        raise ValueError("prediction, label and mask shapes do not match")
    if bins < 2 or not valid_mask.any():
        raise ValueError("bins must be >=2 and valid_mask must not be empty")
    valid_labels = labels[valid_mask]
    if not valid_labels.any() or valid_labels.all():
        raise ValueError("valid labels must contain both classes")

    disagreement = np.abs(predictions[0] - predictions[1])[valid_mask]
    ensemble = predictions.mean(axis=0)[valid_mask]
    edges = np.quantile(disagreement, np.linspace(0.0, 1.0, bins + 1))
    rows = []
    for index in range(bins):
        selected = disagreement >= edges[index]
        selected &= disagreement <= edges[index + 1] if index == bins - 1 else disagreement < edges[index + 1]
        rows.append({
            "bin": index,
            "lower": float(edges[index]),
            "upper": float(edges[index + 1]),
            "pixels": int(selected.sum()),
            "positive_prevalence": float(valid_labels[selected].mean()),
            "mean_ensemble_score": float(ensemble[selected].mean()),
        })
    return {
        "pixels": int(valid_mask.sum()),
        "positive_prevalence": float(valid_labels.mean()),
        "disagreement_ap": float(average_precision(valid_labels.astype(np.uint8), disagreement)),
        "negative_disagreement_ap": float(average_precision(valid_labels.astype(np.uint8), -disagreement)),
        "disagreement_label_pearson_r": float(np.corrcoef(disagreement, valid_labels.astype(np.float32))[0, 1]),
        "mean_disagreement_positive": float(disagreement[valid_labels].mean()),
        "mean_disagreement_negative": float(disagreement[~valid_labels].mean()),
        "quantile_bins": rows,
    }


def run(config_path: Path) -> dict:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    if cfg.get("schema_version") != "inksurf-replica-disagreement-audit/1.0":
        raise ValueError("invalid config schema")
    if cfg.get("regime") != "DEV" or cfg.get("analysis_type") != "post_hoc_diagnostic":
        raise ValueError("revealed-partition disagreement audit must be DEV post-hoc")
    if cfg.get("confirmatory_reuse_allowed") is not False:
        raise ValueError("config must prohibit confirmatory reuse")

    with np.load(root / cfg["predictions"], allow_pickle=False) as bundle:
        predictions = np.asarray(bundle["predictions"], dtype=np.float32)
        chunk_yx = np.asarray(bundle["chunk_yx"], dtype=int)
        model_ids = [str(value) for value in bundle["model_ids"]]
    labels = []
    masks = []
    for y, x in chunk_yx:
        path = root / cfg["derived_root"] / f"chunk_{y}_{x}.npz"
        with np.load(path, allow_pickle=False) as chunk:
            labels.append(np.asarray(chunk["inklabels"], dtype=bool))
            masks.append(np.asarray(chunk["validation_mask"], dtype=bool))
    labels_array = np.stack(labels)
    masks_array = np.stack(masks)
    summary = disagreement_summary(predictions, labels_array, masks_array, bins=int(cfg.get("bins", 10)))
    report = {
        "schema_version": cfg["schema_version"],
        "experiment_id": cfg["experiment_id"],
        "track": cfg["track"],
        "regime": "DEV",
        "analysis_type": "post_hoc_diagnostic",
        "source_partition_previous_regime": cfg["source_partition_previous_regime"],
        "confirmatory_reuse_allowed": False,
        "independence_group": cfg["independence_group"],
        "model_ids": model_ids,
        "status": "diagnostic_complete_no_threshold_fitted",
        **summary,
        "interpretation_guardrail": (
            "Within-family disagreement is descriptive only. It must not drive abstention unless a new DEV analysis "
            "and a separate locked partition demonstrate that larger disagreement predicts error rather than signal."
        ),
    }
    _atomic_json(root / cfg["output_report"], report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
