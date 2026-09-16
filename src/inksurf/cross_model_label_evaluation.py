"""Evaluate two registered bounded ink renders against a frozen labeled partition."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .evidence_consistency import _atomic_json
from .tifxyz_common_support import sample_grid_support


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=bool).ravel()
    scores = np.asarray(scores, dtype=float).ravel()
    positives = int(labels.sum())
    if positives == 0 or positives == labels.size:
        raise ValueError("average precision requires both classes")
    order = np.argsort(-scores, kind="mergesort")
    ordered_labels = labels[order]
    ordered_scores = scores[order]
    ends = np.r_[np.flatnonzero(ordered_scores[1:] != ordered_scores[:-1]), labels.size - 1]
    true_positive = np.cumsum(ordered_labels)[ends]
    false_positive = (ends + 1) - true_positive
    precision = true_positive / (true_positive + false_positive)
    recall = true_positive / positives
    return float(np.sum(np.diff(np.r_[0.0, recall]) * precision))


def sample_bilinear_roi(
    image: np.ndarray, global_y: np.ndarray, global_x: np.ndarray,
    source_shape_yx: tuple[int, int], target_shape_yx: tuple[int, int],
    roi_bounds: tuple[int, int, int, int],
) -> np.ndarray:
    sy, sx = source_shape_yx
    ty, tx = target_shape_yx
    y0, y1, x0, x1 = roi_bounds
    if image.shape != (y1 - y0, x1 - x0):
        raise ValueError("ROI array shape does not match planned bounds")
    fy = (global_y + 0.5) * ty / sy - 0.5 - y0
    fx = (global_x + 0.5) * tx / sx - 0.5 - x0
    iy0 = np.clip(np.floor(fy).astype(int), 0, image.shape[0] - 1)
    ix0 = np.clip(np.floor(fx).astype(int), 0, image.shape[1] - 1)
    iy1 = np.clip(iy0 + 1, 0, image.shape[0] - 1)
    ix1 = np.clip(ix0 + 1, 0, image.shape[1] - 1)
    wy = np.clip(fy - np.floor(fy), 0.0, 1.0)
    wx = np.clip(fx - np.floor(fx), 0.0, 1.0)
    return (
        image[iy0, ix0] * (1 - wy) * (1 - wx)
        + image[iy0, ix1] * (1 - wy) * wx
        + image[iy1, ix0] * wy * (1 - wx)
        + image[iy1, ix1] * wy * wx
    )


def _metric(labels: np.ndarray, scores: np.ndarray) -> dict:
    return {
        "average_precision": average_precision(labels, scores),
        "positive_mean": float(scores[labels].mean()),
        "negative_mean": float(scores[~labels].mean()),
        "positive_negative_margin": float(scores[labels].mean() - scores[~labels].mean()),
    }


def _percentile_interval(values: list[float]) -> list[float] | None:
    return [float(x) for x in np.percentile(values, [2.5, 97.5])] if values else None


def run(config_path: Path) -> dict:
    import tifffile

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    if cfg.get("schema_version") != "inksurf-cross-model-label-evaluation/1.0":
        raise ValueError("unsupported schema_version")
    if cfg.get("track") != "A" or cfg.get("regime") != "VALIDATION":
        raise ValueError("evaluation requires Track A VALIDATION")
    if cfg.get("freeze_state") != "frozen_before_ground_truth":
        raise ValueError("evaluation must be frozen before ground truth")
    root = config_path.resolve().parent.parent

    receipts = {}
    for name in ("chunk_audit", "tiff_plan", "tiff_fetch", "tifxyz_download", "registration", "common_support"):
        specification = cfg[name]
        path = root / specification["report"]
        if _sha256(path) != specification["sha256"]:
            raise ValueError(f"{name} receipt hash mismatch")
        receipts[name] = json.loads(path.read_text(encoding="utf-8"))
    if receipts["registration"].get("status") != "GO_UV_CORRESPONDENCE":
        raise ValueError("registration gate did not pass")
    if receipts["common_support"].get("status") != "GO_LABELED_COMMON_SUPPORT":
        raise ValueError("two-class common-support gate did not pass")

    verified = {
        ((root / row["destination"]).resolve() if not Path(row["destination"]).is_absolute() else Path(row["destination"]).resolve()): row["sha256"]
        for row in receipts["tifxyz_download"]["files"]
    }
    validity = []
    for specification in cfg["coordinate_sets"]:
        channels = []
        for axis in ("x", "y", "z"):
            path = root / specification[axis]
            if verified.get(path.resolve()) != _sha256(path):
                raise ValueError("coordinate file is not bound to TIFXYZ receipt")
            channels.append(tifffile.imread(path, key=0))
        xyz = np.stack(channels, axis=-1)
        validity.append(np.isfinite(xyz).all(-1) & ~np.all(xyz == -1, axis=-1) & (xyz[..., 2] > 0))

    plan_artifacts = receipts["tiff_plan"]["artifacts"]
    fetch_by_id = {item["artifact_id"]: item for item in receipts["tiff_fetch"]["outputs"]}
    arrays = []
    for artifact in plan_artifacts:
        fetched = fetch_by_id[artifact["artifact_id"]
        ]
        path = root / fetched["output"]
        if _sha256(path) != fetched["sha256"]:
            raise ValueError("prediction ROI archive hash mismatch")
        arrays.append(np.load(path))
    if len(arrays) != 2 or len(validity) != 2:
        raise ValueError("exactly two render/geometry sources are required")

    chunks = receipts["chunk_audit"]["chunks"]
    source_shape = tuple(map(int, cfg["annotation_canvas_shape_yx"]))
    chunk_pixels = int(cfg["chunk_pixels"])
    per_chunk = []
    for index, item in enumerate(chunks):
        derived = np.load(root / item["derived"])
        evaluation = np.asarray(derived["validation_mask"], dtype=bool)
        ink = np.asarray(derived["inklabels"], dtype=bool)
        y, x = map(int, item["chunk_yx"])
        gy = y * chunk_pixels + np.arange(evaluation.shape[0])[:, None]
        gx = x * chunk_pixels + np.arange(evaluation.shape[1])[None, :]
        common = np.logical_and.reduce([
            sample_grid_support(grid, gy, gx, source_shape, "all") for grid in validity
        ])
        eligible = evaluation & common
        scores = []
        for artifact_index, artifact in enumerate(plan_artifacts):
            image = np.asarray(arrays[artifact_index][f"roi_{index:02d}"], dtype=float) / float(cfg["score_scale"])
            scores.append(sample_bilinear_roi(
                image, gy, gx, source_shape, tuple(artifact["shape_yx"]),
                tuple(artifact["mapped_rois_y0_y1_x0_x1"][index]),
            ))
        per_chunk.append({
            "chunk_yx": item["chunk_yx"], "labels": ink[eligible],
            "scores": [score[eligible] for score in scores],
        })

    labels = np.concatenate([item["labels"] for item in per_chunk])
    source_scores = [np.concatenate([item["scores"][i] for item in per_chunk]) for i in range(2)]
    criteria = cfg["go_criteria"]
    chunks_with_both = sum(item["labels"].any() and (~item["labels"]).any() for item in per_chunk)
    support_gates = {
        "eligible_ink_pixels": int(labels.sum()) >= int(criteria["minimum_eligible_ink_pixels"]),
        "eligible_negative_pixels": int((~labels).sum()) >= int(criteria["minimum_eligible_negative_pixels"]),
        "chunks_with_both_classes": chunks_with_both >= int(criteria["minimum_chunks_with_both_classes"]),
    }
    if not all(support_gates.values()):
        status = "NO_GO_EVALUATION_SUPPORT"
        report = {
            "schema_version": cfg["schema_version"], "experiment_id": cfg["experiment_id"],
            "track": "A", "regime": "VALIDATION", "geometry_tier": "G1", "status": status,
            "eligible_pixels": int(labels.size), "eligible_ink_pixels": int(labels.sum()),
            "eligible_negative_pixels": int((~labels).sum()), "chunks_with_both_classes": chunks_with_both,
            "support_gates": support_gates, "score_comparison_performed": False,
            "claim_limit": cfg["claim_limit"],
        }
        _atomic_json(root / cfg["output_report"], report)
        return report

    fusion = (source_scores[0] + source_scores[1]) / 2
    disagreement = np.abs(source_scores[0] - source_scores[1])
    keep = disagreement <= np.quantile(disagreement, 1 - float(cfg["abstention_fraction"]))
    metrics = {
        "source_0": _metric(labels, source_scores[0]),
        "source_1": _metric(labels, source_scores[1]),
        "fusion": _metric(labels, fusion),
        "abstained_fusion": _metric(labels[keep], fusion[keep]),
    }
    best_single = max(metrics["source_0"]["average_precision"], metrics["source_1"]["average_precision"])
    gain = metrics["fusion"]["average_precision"] - best_single
    abstention_gain = metrics["abstained_fusion"]["average_precision"] - metrics["fusion"]["average_precision"]
    rng = np.random.default_rng(int(cfg["seed"]))
    bootstrap_gain, bootstrap_abstention = [], []
    for _ in range(int(cfg["bootstrap_replicates"])):
        sample = rng.integers(0, len(per_chunk), len(per_chunk))
        boot_labels = np.concatenate([per_chunk[i]["labels"] for i in sample])
        if not boot_labels.any() or boot_labels.all():
            continue
        boot_scores = [np.concatenate([per_chunk[i]["scores"][j] for i in sample]) for j in range(2)]
        boot_fusion = (boot_scores[0] + boot_scores[1]) / 2
        boot_disagreement = np.abs(boot_scores[0] - boot_scores[1])
        boot_keep = boot_disagreement <= np.quantile(boot_disagreement, 1 - float(cfg["abstention_fraction"]))
        if not boot_labels[boot_keep].any() or boot_labels[boot_keep].all():
            continue
        bootstrap_gain.append(average_precision(boot_labels, boot_fusion) - max(
            average_precision(boot_labels, boot_scores[0]), average_precision(boot_labels, boot_scores[1])
        ))
        bootstrap_abstention.append(
            average_precision(boot_labels[boot_keep], boot_fusion[boot_keep])
            - average_precision(boot_labels, boot_fusion)
        )
    gain_ci = _percentile_interval(bootstrap_gain)
    abstention_ci = _percentile_interval(bootstrap_abstention)
    decision_gates = {
        "fusion_ap_gain": gain >= float(criteria["fusion_ap_gain_over_best_single_min"]),
        "fusion_ap_gain_ci95_lower": gain_ci is not None and gain_ci[0] > float(criteria["fusion_ap_gain_ci95_lower_gt"]),
        "abstention_ap_gain": abstention_gain >= float(criteria["abstention_ap_gain_min"]),
    }
    status = "GO_CROSS_MODEL_VALUE" if all(decision_gates.values()) else "NO_GO_CROSS_MODEL_VALUE"
    report = {
        "schema_version": cfg["schema_version"], "experiment_id": cfg["experiment_id"],
        "track": "A", "regime": "VALIDATION", "geometry_tier": "G1", "status": status,
        "eligible_pixels": int(labels.size), "eligible_ink_pixels": int(labels.sum()),
        "eligible_negative_pixels": int((~labels).sum()), "chunks_with_both_classes": chunks_with_both,
        "support_gates": support_gates, "score_comparison_performed": True,
        "metrics": metrics, "fusion_ap_gain_over_best_single": gain,
        "fusion_ap_gain_ci95": gain_ci, "abstention_fraction": float(cfg["abstention_fraction"]),
        "abstention_ap_gain": abstention_gain, "abstention_ap_gain_ci95": abstention_ci,
        "bootstrap_valid_replicates": len(bootstrap_gain), "decision_gates": decision_gates,
        "claim_limit": cfg["claim_limit"],
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
