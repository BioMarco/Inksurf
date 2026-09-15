"""Create local component/skeleton artifacts and quantify threshold stability."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from inksurf.benchmark_baseline import _atomic_json
from inksurf.structural_features import _atomic_csv


def mask_iou(left: np.ndarray, right: np.ndarray) -> float:
    union = np.logical_or(left, right).sum()
    return float(np.logical_and(left, right).sum() / union) if union else 1.0


def _atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(config_path: Path) -> dict[str, Any]:
    import tifffile
    from scipy.ndimage import binary_closing, label
    from skimage.morphology import disk, remove_small_objects, skeletonize

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["regime"] != "DEV":
        raise PermissionError("candidate artifact development currently permits DEV only")
    root = config_path.resolve().parent.parent
    package = json.loads((root / config["candidate_package"]).read_text(encoding="utf-8"))
    if package["regime"] != "DEV" or package["geometry_tier"] != "G2":
        raise ValueError("artifact extraction requires a DEV G2 candidate package")
    prediction = tifffile.imread(root / config["prediction_tif"], key=0)
    valid = tifffile.imread(root / config["supervision_mask_tif"], key=0) > 0
    if prediction.shape != valid.shape:
        raise ValueError("prediction and supervision mask shapes differ")
    thresholds = [int(value) for value in config["thresholds"]]
    primary = int(config["primary_threshold"])
    if primary not in thresholds or thresholds != sorted(thresholds) or len(thresholds) != 3:
        raise ValueError("thresholds must be three ordered values containing primary")
    footprint = disk(int(config["closing_radius"]))
    artifact_dir = root / config["local_artifact_directory"]
    manifest_candidates = []
    metric_rows = []
    for candidate in package["candidates"]:
        bounds = candidate["bounds_yx"]
        crop = prediction[bounds["y0"]:bounds["y1"], bounds["x0"]:bounds["x1"]]
        crop_valid = valid[bounds["y0"]:bounds["y1"], bounds["x0"]:bounds["x1"]]
        masks = {}
        skeletons = {}
        components = {}
        for threshold in thresholds:
            mask = binary_closing((crop >= threshold) & crop_valid, structure=footprint)
            mask = remove_small_objects(mask, max_size=int(config["minimum_component_pixels"]) - 1)
            skeleton = skeletonize(mask)
            _, component_count = label(mask, structure=np.ones((3, 3), dtype=np.uint8))
            masks[threshold] = mask
            skeletons[threshold] = skeleton
            components[threshold] = int(component_count)
        low, high = thresholds[0], thresholds[-1]
        iou_low = mask_iou(masks[primary], masks[low])
        iou_high = mask_iou(masks[primary], masks[high])
        primary_length = int(skeletons[primary].sum())
        high_retention = float(skeletons[high].sum() / primary_length) if primary_length else 1.0
        passes = (
            iou_low >= float(config["stability_criteria"]["minimum_mask_iou_each_perturbation"])
            and iou_high >= float(config["stability_criteria"]["minimum_mask_iou_each_perturbation"])
            and high_retention >= float(config["stability_criteria"]["minimum_high_threshold_skeleton_retention"])
        )
        artifact_path = artifact_dir / f"{candidate['candidate_id']}.npz"
        _atomic_npz(
            artifact_path,
            component_mask=masks[primary].astype(np.uint8),
            skeleton=skeletons[primary].astype(np.uint8),
            valid_mask=crop_valid.astype(np.uint8),
        )
        relative = str(artifact_path.relative_to(root)).replace("\\", "/")
        row = {
            "candidate_id": candidate["candidate_id"], "rank": candidate["rank"],
            "primary_threshold": primary, "component_pixels": int(masks[primary].sum()),
            "skeleton_pixels": primary_length, "components": components[primary],
            "mask_iou_low": iou_low, "mask_iou_high": iou_high,
            "high_threshold_skeleton_retention": high_retention, "passes_stability": passes,
        }
        metric_rows.append(row)
        manifest_candidates.append({
            "candidate_id": candidate["candidate_id"], "artifact_path": relative,
            "bytes": artifact_path.stat().st_size, "sha256": _sha256(artifact_path),
            "arrays": ["component_mask", "skeleton", "valid_mask"], "metrics": row,
        })
    manifest = {
        "experiment_id": config["experiment_id"], "surface_id": package["surface_id"],
        "regime": "DEV", "geometry_tier": "G2", "format": "compressed NPZ uint8",
        "publication_status": "local_ignored_no_preview", "candidates": manifest_candidates,
    }
    report = {
        "experiment_id": config["experiment_id"], "track": config["track"], "regime": "DEV",
        "geometry_tier": "G2", "surface_id": package["surface_id"], "status": "complete",
        "thresholds": thresholds, "primary_threshold": primary,
        "morphology": {"closing_radius": config["closing_radius"],
                       "minimum_component_pixels": config["minimum_component_pixels"]},
        "stability_criteria": config["stability_criteria"], "candidate_count": len(metric_rows),
        "stable_candidates": sum(row["passes_stability"] for row in metric_rows),
        "median_mask_iou_low": float(np.median([row["mask_iou_low"] for row in metric_rows])),
        "median_mask_iou_high": float(np.median([row["mask_iou_high"] for row in metric_rows])),
        "median_high_threshold_skeleton_retention": float(np.median([row["high_threshold_skeleton_retention"] for row in metric_rows])),
        "label_inputs_used": False, "validation_files_accessed": 0,
        "methodological_note": "Artifacts describe the frozen raw-prediction baseline. They do not rescue the failed InkSurf structural score or establish physical ink.",
    }
    _atomic_json(root / config["outputs"]["manifest_json"], manifest)
    _atomic_csv(root / config["outputs"]["candidates_csv"], metric_rows)
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
