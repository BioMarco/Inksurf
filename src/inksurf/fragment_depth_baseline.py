"""Build continuous depth-wise CT baselines from a bounded DEV fragment stack."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import numpy as np

from inksurf.benchmark_baseline import average_precision, review_metrics


SCORE_NAMES = ("depth_mean", "depth_max", "depth_std", "central_contrast")


def depth_features(stack: np.ndarray, central_start: int, central_stop: int) -> dict[str, np.ndarray]:
    if stack.ndim != 3 or not 0 <= central_start < central_stop <= stack.shape[0]:
        raise ValueError("invalid depth stack or central offsets")
    values = stack.astype(np.float32, copy=False)
    central = values[central_start:central_stop]
    outer = np.concatenate((values[:central_start], values[central_stop:]), axis=0)
    if outer.shape[0] == 0:
        raise ValueError("central slice leaves no outer layers")
    return {
        "depth_mean": values.mean(axis=0),
        "depth_max": values.max(axis=0),
        "depth_std": values.std(axis=0),
        "central_contrast": central.mean(axis=0) - outer.mean(axis=0),
    }


def histogram_metrics(
    scores: np.ndarray, labels: np.ndarray, valid: np.ndarray, bins: int, direction: str
) -> dict[str, float | int]:
    values = scores[valid].astype(np.float64, copy=False)
    truth = labels[valid]
    low, high = float(values.min()), float(values.max())
    if low == high:
        raise ValueError("constant score inside mask")
    edges = np.linspace(low, high, bins + 1)
    positive, _ = np.histogram(values[truth], bins=edges)
    negative, _ = np.histogram(values[~truth], bins=edges)
    if direction == "high":
        positive = positive[::-1]
        negative = negative[::-1]
    elif direction != "low":
        raise ValueError("direction must be high or low")
    tp = np.cumsum(positive)
    fp = np.cumsum(negative)
    positives = int(positive.sum())
    recall = tp / positives
    precision = np.divide(tp, tp + fp, out=np.zeros_like(tp, dtype=float), where=(tp + fp) > 0)
    ap = float(np.sum(np.diff(np.r_[0.0, recall]) * precision))
    beta2 = 0.25
    f05 = np.divide(
        (1 + beta2) * precision * recall,
        beta2 * precision + recall,
        out=np.zeros_like(precision),
        where=(beta2 * precision + recall) > 0,
    )
    best = int(np.argmax(f05))
    return {
        "direction": direction,
        "histogram_bins": bins,
        "approximate_average_precision": ap,
        "best_f0_5": float(f05[best]),
        "best_threshold_bin": best,
        "score_min": low,
        "score_max": high,
        "positive_pixels": positives,
        "negative_pixels": int(negative.sum()),
    }


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
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
    try:
        import tifffile
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("install benchmark and fragment dependencies") from exc
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("regime") != "DEV":
        raise ValueError("depth baseline is restricted to DEV")
    root = config_path.resolve().parent.parent
    start, stop = (int(value) for value in config["layer_range_inclusive"])
    layer_paths = [root / config["layer_directory"] / f"{layer:02d}.tif" for layer in range(start, stop + 1)]
    if not all(path.is_file() for path in layer_paths):
        raise FileNotFoundError("one or more frozen layers are missing")
    with Image.open(root / config["inklabels"]) as image:
        labels = np.asarray(image) > 0
    with Image.open(root / config["mask"]) as image:
        valid = np.asarray(image) > 0
    if labels.shape != valid.shape:
        raise ValueError("labels and mask differ in shape")
    height, width = valid.shape
    map_dir = root / config["map_directory"]
    map_dir.mkdir(parents=True, exist_ok=True)
    maps = {
        name: np.lib.format.open_memmap(map_dir / f"{name}.npy", mode="w+", dtype=np.float32, shape=(height, width))
        for name in SCORE_NAMES
    }
    central_start, central_stop_inclusive = (int(value) for value in config["central_layer_offsets"])
    central_stop = central_stop_inclusive + 1
    layers = [tifffile.memmap(path, mode="r") for path in layer_paths]
    if any(layer.shape != (height, width) or layer.dtype != np.uint16 for layer in layers):
        raise ValueError("layer shape or dtype differs from frozen header audit")
    band_rows = int(config["band_rows"])
    for y0 in range(0, height, band_rows):
        y1 = min(height, y0 + band_rows)
        stack = np.stack([layer[y0:y1] for layer in layers], axis=0)
        features = depth_features(stack, central_start, central_stop)
        for name, values in features.items():
            maps[name][y0:y1] = values
        print(f"mapped rows {y0}:{y1} of {height}", flush=True)
    for array in maps.values():
        array.flush()

    pixel_results = []
    bins = int(config["pixel_histogram_bins"])
    for name, values in maps.items():
        for direction in ("high", "low"):
            pixel_results.append({"score": name, **histogram_metrics(values, labels, valid, bins, direction)})

    region_size = int(config["region_size"])
    min_valid = float(config["min_valid_fraction"])
    rows: list[dict[str, Any]] = []
    for y0 in range(0, height, region_size):
        y1 = min(height, y0 + region_size)
        for x0 in range(0, width, region_size):
            x1 = min(width, x0 + region_size)
            region_valid = valid[y0:y1, x0:x1]
            valid_pixels = int(region_valid.sum())
            footprint = (y1 - y0) * (x1 - x0)
            row: dict[str, Any] = {
                "region_id": f"y{y0:05d}_x{x0:05d}", "y0": y0, "y1": y1, "x0": x0, "x1": x1,
                "footprint_pixels": footprint, "valid_pixels": valid_pixels,
                "valid_fraction": valid_pixels / footprint, "eligible": valid_pixels / footprint >= min_valid,
                "ink_pixels": int((labels[y0:y1, x0:x1] & region_valid).sum()),
                "chance_score": 0.0,
            }
            for name, values in maps.items():
                selected = values[y0:y1, x0:x1][region_valid]
                for statistic, value in (("mean", selected.mean() if selected.size else np.nan),
                                         ("p95", np.quantile(selected, 0.95) if selected.size else np.nan),
                                         ("max", selected.max() if selected.size else np.nan)):
                    row[f"{name}_{statistic}"] = float(value)
                    row[f"neg_{name}_{statistic}"] = -float(value)
            rows.append(row)

    eligible = [row for row in rows if row["eligible"]]
    threshold = int(config["positive_region_min_ink_pixels"])
    region_labels = np.asarray([row["ink_pixels"] >= threshold for row in eligible])
    ink_pixels = np.asarray([row["ink_pixels"] for row in eligible])
    valid_pixels = np.asarray([row["valid_pixels"] for row in eligible])
    region_results = []
    for column in [key for key in rows[0] if key.endswith(("_mean", "_p95", "_max"))]:
        scores = np.asarray([row[column] for row in eligible])
        item = {"score": column, "average_precision": average_precision(region_labels, scores)}
        item["review"] = [review_metrics(scores, ink_pixels, valid_pixels, fraction) for fraction in (0.01, 0.05, 0.10)]
        region_results.append(item)
    best_region = max(region_results, key=lambda item: item["average_precision"])
    report = {
        "experiment_id": config["experiment_id"], "fragment": config["fragment"], "regime": "DEV",
        "status": "depth_baselines_complete_validation_locked", "geometry_tier": "G0",
        "shape_yx": [height, width], "layers": [start, stop], "pixel_results": pixel_results,
        "regions_total": len(rows), "regions_eligible": len(eligible),
        "positive_regions": int(region_labels.sum()), "negative_regions": int((~region_labels).sum()),
        "region_results": region_results, "best_region_score": best_region["score"],
        "map_files": [f"{name}.npy" for name in SCORE_NAMES],
        "warning": "DEV-only baseline selection. Pixel AP is a 4096-bin approximation; no VALIDATION data accessed.",
    }
    _atomic_text(root / config["outputs"]["report_json"], json.dumps(report, indent=2, sort_keys=True) + "\n")
    from io import StringIO
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    _atomic_text(root / config["outputs"]["regions_csv"], stream.getvalue())
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    report = run(args.config)
    print(json.dumps({key: report[key] for key in ("status", "best_region_score", "regions_eligible")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
