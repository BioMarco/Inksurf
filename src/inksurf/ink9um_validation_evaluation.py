"""Evaluate bounded ink_9um predictions against frozen DEV labels and controls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .benchmark_baseline import average_precision
from .seating_reproduce import _atomic_json


def metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    return {
        "average_precision": float(average_precision(labels.astype(np.uint8), scores)),
        "positive_mean": float(scores[labels].mean()),
        "negative_mean": float(scores[~labels].mean()),
        "mean_margin": float(scores[labels].mean() - scores[~labels].mean()),
    }


def bootstrap_mean_interval(values: np.ndarray, replicates: int, seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    draws = values[rng.integers(0, len(values), size=(replicates, len(values)))].mean(axis=1)
    return [float(value) for value in np.quantile(draws, [0.025, 0.975])]


def run(config_path: Path) -> dict:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    if cfg.get("schema_version") != "inksurf-ink9um-validation-evaluation/1.0":
        raise ValueError("invalid config schema")
    regime = cfg.get("regime")
    if cfg.get("track") != "A" or regime not in {"DEV", "VALIDATION"}:
        raise ValueError("evaluation is restricted to Track A DEV/VALIDATION")
    if regime == "VALIDATION" and cfg.get("freeze_state") != "frozen_before_ground_truth":
        raise ValueError("VALIDATION evaluation requires a frozen protocol")
    inference = json.loads((root / cfg["inference_report"]).read_text(encoding="utf-8"))
    if inference.get("status") != "complete" or inference.get("input_chunks") != 12:
        raise ValueError("inference report is incomplete")
    with np.load(root / cfg["predictions"], allow_pickle=False) as bundle:
        predictions = np.asarray(bundle["predictions"], dtype=np.float32)
        chunk_yx = np.asarray(bundle["chunk_yx"], dtype=int)
        model_ids = [str(value) for value in bundle["model_ids"]]
    if predictions.shape != (2, 12, 128, 128):
        raise ValueError(f"unexpected prediction shape {predictions.shape}")

    labels_by_chunk = []
    masks_by_chunk = []
    baselines = {name: [] for name in cfg["raw_baselines"]}
    for y, x in chunk_yx:
        derived_root = Path(cfg.get("derived_root", "data/ink9um_validation_pilot/derived"))
        path = root / derived_root / f"chunk_{y}_{x}.npz"
        with np.load(path, allow_pickle=False) as chunk:
            volume = np.asarray(chunk["volume"], dtype=np.float32)[2:19]
            labels_by_chunk.append(np.asarray(chunk["inklabels"], dtype=bool))
            masks_by_chunk.append(np.asarray(chunk["validation_mask"], dtype=bool))
        baselines["depth_std17"].append(volume.std(axis=0))
        baselines["depth_max17"].append(volume.max(axis=0))
        baselines["central_slice"].append(volume[8])
    labels_by_chunk = np.stack(labels_by_chunk)
    masks_by_chunk = np.stack(masks_by_chunk)
    baselines = {name: np.stack(values) for name, values in baselines.items()}
    ensemble = predictions.mean(axis=0)
    disagreement = np.abs(predictions[0] - predictions[1])

    labels = labels_by_chunk[masks_by_chunk]
    model_metrics = {
        model_id: metrics(labels, predictions[index][masks_by_chunk])
        for index, model_id in enumerate(model_ids)
    }
    ensemble_metrics = metrics(labels, ensemble[masks_by_chunk])
    baseline_metrics = {name: metrics(labels, values[masks_by_chunk]) for name, values in baselines.items()}
    best_baseline = max(baseline_metrics, key=lambda name: baseline_metrics[name]["average_precision"])
    ap_gain = ensemble_metrics["average_precision"] - baseline_metrics[best_baseline]["average_precision"]

    eligible = []
    regional = []
    for index, key in enumerate(chunk_yx.tolist()):
        mask = masks_by_chunk[index]
        local_labels = labels_by_chunk[index][mask]
        if local_labels.any() and (~local_labels).any():
            model_ap = average_precision(local_labels.astype(np.uint8), ensemble[index][mask])
            baseline_ap = average_precision(local_labels.astype(np.uint8), baselines[best_baseline][index][mask])
            eligible.append(float(model_ap - baseline_ap))
            regional.append({"chunk_yx": key, "ensemble_ap": float(model_ap), "baseline_ap": float(baseline_ap), "ap_gain": float(model_ap - baseline_ap)})
    eligible_array = np.asarray(eligible)
    interval = bootstrap_mean_interval(eligible_array, int(cfg["bootstrap_replicates"]), int(cfg["seed"]))

    valid_disagreement = disagreement[masks_by_chunk]
    cutoff = float(np.quantile(valid_disagreement, 1.0 - float(cfg["abstention_fraction"])))
    retained = masks_by_chunk & (disagreement <= cutoff)
    abstained_metrics = metrics(labels_by_chunk[retained], ensemble[retained])
    empty_chunks = np.array([not labels_by_chunk[i][masks_by_chunk[i]].any() for i in range(12)])
    negative_control_mean = float(ensemble[empty_chunks][masks_by_chunk[empty_chunks]].mean())
    positive_score_mean = float(ensemble[masks_by_chunk & labels_by_chunk].mean())
    control_margin = positive_score_mean - negative_control_mean
    seed_corr = float(np.corrcoef(predictions[0][masks_by_chunk], predictions[1][masks_by_chunk])[0, 1])
    checks = {
        "ensemble_ap_gain": ap_gain >= cfg["go_criteria"]["ensemble_ap_gain_over_best_raw_min"],
        "regional_ap_gain_ci95": interval[0] > cfg["go_criteria"]["ensemble_ap_gain_ci95_lower_gt"],
        "positive_to_negative_control_score_margin": control_margin >= cfg["go_criteria"]["positive_to_negative_control_score_margin_min"],
    }
    abstention_gain = abstained_metrics["average_precision"] - ensemble_metrics["average_precision"]
    if "abstention_ap_gain_min" in cfg["go_criteria"]:
        checks["abstention_ap_gain"] = abstention_gain >= cfg["go_criteria"]["abstention_ap_gain_min"]
    report = {
        "schema_version": cfg["schema_version"],
        "experiment_id": cfg["experiment_id"],
        "track": "A",
        "regime": regime,
        "geometry_tier": "G1",
        "status": "GO_BOUNDED_DEV" if all(checks.values()) else "NO_GO_BOUNDED_DEV",
        "pixels": int(labels.size),
        "positive_prevalence": float(labels.mean()),
        "model_metrics": model_metrics,
        "seed_prediction_pearson_r": seed_corr,
        "seed_prediction_mae": float(np.abs(predictions[0][masks_by_chunk] - predictions[1][masks_by_chunk]).mean()),
        "ensemble_metrics": ensemble_metrics,
        "raw_baselines": baseline_metrics,
        "best_raw_baseline": best_baseline,
        "ensemble_ap_gain_over_best_raw": float(ap_gain),
        "regional_ap": regional,
        "regional_mean_ap_gain": float(eligible_array.mean()),
        "regional_mean_ap_gain_ci95_chunk_bootstrap": interval,
        "bootstrap_replicates": cfg["bootstrap_replicates"],
        "abstention_fraction_target": cfg["abstention_fraction"],
        "disagreement_cutoff": cutoff,
        "retained_fraction": float(retained.sum() / masks_by_chunk.sum()),
        "retained_ensemble_metrics": abstained_metrics,
        "abstention_ap_gain": float(abstention_gain),
        "negative_only_chunks": int(empty_chunks.sum()),
        "negative_control_mean_score": negative_control_mean,
        "positive_label_mean_score": positive_score_mean,
        "positive_to_negative_control_score_margin": control_margin,
        "go_checks": checks,
        "interpretation": "Bounded selected DEV stress test using transferred/pseudo labels; correlated seed replicas form one model family and are not independent confirmations.",
    }
    _atomic_json(root / cfg["output_report"], report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
