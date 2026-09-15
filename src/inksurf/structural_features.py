"""Compute label-blind structural scores for frozen surface review regions."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import numpy as np


def structural_map(
    prediction: np.ndarray,
    *,
    intensity_low: float,
    intensity_high: float,
    gradient_sigma: float,
    tensor_sigma: float,
    contrast_sigma: float,
) -> np.ndarray:
    from scipy.ndimage import gaussian_filter

    if intensity_high <= intensity_low:
        raise ValueError("intensity_high must exceed intensity_low")
    image = prediction.astype(np.float32, copy=False)
    normalized = np.clip((image - intensity_low) / (intensity_high - intensity_low), 0.0, 1.0)
    smooth = gaussian_filter(normalized, gradient_sigma, mode="reflect")
    gy, gx = np.gradient(smooth)
    jxx = gaussian_filter(gx * gx, tensor_sigma, mode="reflect")
    jyy = gaussian_filter(gy * gy, tensor_sigma, mode="reflect")
    jxy = gaussian_filter(gx * gy, tensor_sigma, mode="reflect")
    coherence = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy**2) / (jxx + jyy + 1e-6)
    background = gaussian_filter(normalized, contrast_sigma, mode="reflect")
    positive_contrast = np.clip(normalized - background, 0.0, 1.0)
    return normalized * (0.25 + 0.75 * np.sqrt(np.clip(coherence, 0.0, 1.0))) * (
        0.5 + 0.5 * positive_contrast
    )


def component_score(
    score: np.ndarray,
    prediction: np.ndarray,
    valid: np.ndarray,
    *,
    threshold: float,
    min_component_pixels: int,
    closing_radius: int,
    min_skeleton_pixels: int,
) -> tuple[float, int, int]:
    from skimage.measure import label, regionprops
    from skimage.morphology import closing, disk, skeletonize

    binary = (prediction >= threshold) & valid
    if closing_radius > 0:
        binary = closing(binary, footprint=disk(closing_radius))
    initial = label(binary, connectivity=2)
    counts = np.bincount(initial.ravel())
    keep = counts >= min_component_pixels
    keep[0] = False
    components = label(keep[initial], connectivity=2)
    best = 0.0
    kept = 0
    longest = 0
    for region in regionprops(components):
        region_mask = components == region.label
        skeleton_pixels = int(skeletonize(region_mask).sum())
        longest = max(longest, skeleton_pixels)
        if skeleton_pixels < min_skeleton_pixels:
            continue
        kept += 1
        values = score[region_mask]
        evidence = float(np.quantile(values, 0.95))
        elongation = float(region.eccentricity)
        continuity = min(1.0, skeleton_pixels / max(1, min_skeleton_pixels * 4))
        best = max(best, evidence * (0.5 + 0.5 * elongation) * continuity)
    return best, kept, longest


def _atomic_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
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
    with (root / config["regions_csv"]).open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row["eligible"].lower() == "true"]
    prefix = config.get("score_prefix", "inksurf")
    halo = int(config["halo"])
    parameters = config["parameters"]

    output_rows: list[dict[str, Any]] = []
    with ExitStack() as stack:
        if "prediction_npy" in config:
            from PIL import Image

            prediction = np.load(root / config["prediction_npy"], mmap_mode="r")
            mask_image = stack.enter_context(Image.open(root / config["supervision_mask_png"]))
            mask = np.asarray(mask_image)
        else:
            try:
                import tifffile
                import zarr
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("install: pip install '.[benchmark,structure]'") from exc
            pred_tiff = stack.enter_context(tifffile.TiffFile(root / config["prediction_tif"]))
            mask_tiff = stack.enter_context(tifffile.TiffFile(root / config["supervision_mask_tif"]))
            pred_store = stack.enter_context(pred_tiff.pages[0].aszarr())
            mask_store = stack.enter_context(mask_tiff.pages[0].aszarr())
            prediction = zarr.open(pred_store, mode="r")
            mask = zarr.open(mask_store, mode="r")
        height, width = prediction.shape
        if mask.shape != prediction.shape:
            raise ValueError("prediction and mask shapes differ")

        for row in rows:
            y0, y1, x0, x1 = (int(row[key]) for key in ("y0", "y1", "x0", "x1"))
            hy0, hy1 = max(0, y0 - halo), min(height, y1 + halo)
            hx0, hx1 = max(0, x0 - halo), min(width, x1 + halo)
            patch = np.asarray(prediction[hy0:hy1, hx0:hx1])
            valid_patch = np.asarray(mask[hy0:hy1, hx0:hx1]) > 0
            score_patch = structural_map(
                patch,
                intensity_low=float(parameters["intensity_low"]),
                intensity_high=float(parameters["intensity_high"]),
                gradient_sigma=float(parameters["gradient_sigma"]),
                tensor_sigma=float(parameters["tensor_sigma"]),
                contrast_sigma=float(parameters["contrast_sigma"]),
            )
            sy0, sy1 = y0 - hy0, y1 - hy0
            sx0, sx1 = x0 - hx0, x1 - hx0
            core = score_patch[sy0:sy1, sx0:sx1]
            raw_core = patch[sy0:sy1, sx0:sx1]
            valid = valid_patch[sy0:sy1, sx0:sx1]
            values = core[valid]
            if not values.size:
                raise RuntimeError(f"eligible region has no valid pixels: {row['region_id']}")
            best, components, longest = component_score(
                core,
                raw_core,
                valid,
                threshold=float(parameters["component_threshold"]),
                min_component_pixels=int(parameters["min_component_pixels"]),
                closing_radius=int(parameters["closing_radius"]),
                min_skeleton_pixels=int(parameters["min_skeleton_pixels"]),
            )
            row.update(
                {
                    f"{prefix}_mean": float(values.mean()),
                    f"{prefix}_p95": float(np.quantile(values, 0.95)),
                    f"{prefix}_p99": float(np.quantile(values, 0.99)),
                    f"{prefix}_max": float(values.max()),
                    f"{prefix}_component_max": best,
                    f"{prefix}_components": components,
                    f"{prefix}_longest_skeleton": longest,
                }
            )
            output_rows.append(row)

    output = root / config["output_regions_csv"]
    _atomic_csv(output, output_rows)
    report = {
        "experiment_id": config["experiment_id"],
        "status": "dev_label_blind_structural_features_complete",
        "track": "A",
        "regime": "DEV",
        "geometry_tier": "G0",
        "regions": len(output_rows),
        "parameters": parameters,
        "score_prefix": prefix,
        "score_inputs": config.get("score_inputs", ["prediction", "supervision_mask"]),
        "excluded_score_inputs": ["ink_labels", "infrared", "known_render", "validation_data"],
        "output_regions_csv": config["output_regions_csv"],
    }
    report_path = root / config["output_report"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = report_path.with_suffix(report_path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, report_path)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
