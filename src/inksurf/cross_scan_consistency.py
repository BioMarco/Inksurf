"""Evaluate preregistered repeatability between two independent acquisitions."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import rankdata

from .seating_reproduce import _atomic_json


def correlations(first: np.ndarray, second: np.ndarray, valid: np.ndarray) -> dict[str, float]:
    a = first[valid].astype(np.float64)
    b = second[valid].astype(np.float64)
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return {"pearson_r": float("nan"), "spearman_rho": float("nan")}
    return {
        "pearson_r": float(np.corrcoef(a, b)[0, 1]),
        "spearman_rho": float(np.corrcoef(rankdata(a), rankdata(b))[0, 1]),
    }


def top_overlap(first: np.ndarray, second: np.ndarray, valid: np.ndarray, quantile: float) -> dict[str, float]:
    threshold_a = float(np.quantile(first[valid], 1.0 - quantile))
    threshold_b = float(np.quantile(second[valid], 1.0 - quantile))
    selected_a = valid & (first >= threshold_a)
    selected_b = valid & (second >= threshold_b)
    intersection = int(np.count_nonzero(selected_a & selected_b))
    union = int(np.count_nonzero(selected_a | selected_b))
    valid_count = int(np.count_nonzero(valid))
    observed = intersection / valid_count
    return {
        "quantile": quantile,
        "threshold_first": threshold_a,
        "threshold_second": threshold_b,
        "intersection_pixels": intersection,
        "jaccard": intersection / union if union else 0.0,
        "overlap_fraction": observed,
        "overlap_enrichment_vs_independence": observed / (quantile * quantile),
    }


def shifted_pearson(first: np.ndarray, second: np.ndarray, valid: np.ndarray, dy: int, dx: int) -> float:
    y1 = slice(max(0, dy), min(first.shape[0], first.shape[0] + dy))
    y2 = slice(max(0, -dy), min(first.shape[0], first.shape[0] - dy))
    x1 = slice(max(0, dx), min(first.shape[1], first.shape[1] + dx))
    x2 = slice(max(0, -dx), min(first.shape[1], first.shape[1] - dx))
    shifted_valid = valid[y1, x1] & valid[y2, x2]
    return correlations(first[y1, x1], second[y2, x2], shifted_valid)["pearson_r"]


def atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    try:
        with open(temporary, "wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def run(config_path: Path) -> dict[str, Any]:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    if cfg.get("schema_version") != "inksurf-cross-scan-consistency/1.0":
        raise ValueError("invalid config schema")
    if cfg.get("track") != "A" or cfg.get("regime") != "DEV":
        raise ValueError("this frozen pilot must remain Track A / DEV")
    if len({item["independence_group"] for item in cfg["predictions"]}) != 2:
        raise ValueError("predictions must use distinct acquisition independence groups")

    arrays = []
    weights = []
    for item in cfg["predictions"]:
        with np.load(root / item["path"], allow_pickle=False) as bundle:
            arrays.append(np.asarray(bundle["prediction"], dtype=np.float32))
            weights.append(np.asarray(bundle["weight_sum"], dtype=np.float32))
    if arrays[0].shape != arrays[1].shape:
        raise ValueError("prediction shapes differ")
    valid = (weights[0] > 0) & (weights[1] > 0) & np.isfinite(arrays[0]) & np.isfinite(arrays[1])
    agreement = correlations(arrays[0], arrays[1], valid)
    overlap = [top_overlap(arrays[0], arrays[1], valid, float(q)) for q in cfg["top_quantiles"]]
    shifts = [
        {"shift_yx": shift, "pearson_r": shifted_pearson(arrays[0], arrays[1], valid, *shift)}
        for shift in cfg["negative_control_shifts_yx"]
    ]
    disagreement = np.abs(arrays[0] - arrays[1])
    consensus = np.sqrt(np.clip(arrays[0], 0, 1) * np.clip(arrays[1], 0, 1))
    retained = valid & (disagreement <= float(cfg["disagreement_abstention_threshold"]))
    q05 = next(item for item in overlap if np.isclose(item["quantile"], 0.05))
    best_shift = max(item["pearson_r"] for item in shifts)
    criteria = cfg["go_criteria"]
    checks = {
        "pearson_r": agreement["pearson_r"] >= criteria["pearson_r_min"],
        "top_5pct_overlap_enrichment": q05["overlap_enrichment_vs_independence"] >= criteria["top_5pct_overlap_enrichment_min"],
        "pearson_margin_over_best_shift": agreement["pearson_r"] - best_shift >= criteria["pearson_margin_over_best_shift_min"],
        "retained_fraction": float(retained.sum() / valid.sum()) >= criteria["retained_fraction_at_disagreement_threshold_min"],
    }
    output_path = root / cfg["output_npz"]
    atomic_npz(
        output_path,
        consensus=consensus,
        disagreement=disagreement,
        retained=retained,
        valid=valid,
    )
    report = {
        "schema_version": cfg["schema_version"],
        "experiment_id": cfg["experiment_id"],
        "track": "A",
        "regime": "DEV",
        "geometry_tier": cfg["geometry_tier"],
        "status": "GO_REPEATABILITY" if all(checks.values()) else "NO_GO_REPEATABILITY",
        "valid_pixels": int(valid.sum()),
        "agreement": agreement,
        "top_overlap": overlap,
        "negative_control_shifts": shifts,
        "best_shifted_pearson_r": best_shift,
        "pearson_margin_over_best_shift": agreement["pearson_r"] - best_shift,
        "disagreement_threshold": cfg["disagreement_abstention_threshold"],
        "retained_fraction": float(retained.sum() / valid.sum()),
        "go_checks": checks,
        "interpretation": "Repeatability gate only; no ink or textual-content claim. Shared checkpoint errors remain dependent.",
    }
    _atomic_json(root / cfg["report_json"], report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
