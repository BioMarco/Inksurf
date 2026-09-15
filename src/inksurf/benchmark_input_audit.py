"""Stream a frozen DEV surface into region-level input statistics."""

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


def summarize_region(prediction: np.ndarray, labels: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    if prediction.shape != labels.shape or prediction.shape != mask.shape:
        raise ValueError("prediction, labels and mask shapes differ")
    valid = mask > 0
    valid_pixels = int(valid.sum())
    ink_pixels = int(((labels > 0) & valid).sum())
    if valid_pixels == 0:
        return {
            "valid_pixels": 0,
            "ink_pixels": 0,
            "ink_fraction": None,
            "prediction_mean": None,
            "prediction_p95": None,
            "prediction_p99": None,
            "prediction_max": None,
        }
    values = prediction[valid].astype(np.float64, copy=False)
    return {
        "valid_pixels": valid_pixels,
        "ink_pixels": ink_pixels,
        "ink_fraction": ink_pixels / valid_pixels,
        "prediction_mean": float(values.mean()),
        "prediction_p95": float(np.quantile(values, 0.95)),
        "prediction_p99": float(np.quantile(values, 0.99)),
        "prediction_max": int(values.max()),
    }


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
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


def _percentiles_from_histogram(histogram: np.ndarray, percentiles: list[float]) -> dict[str, int]:
    total = int(histogram.sum())
    if total == 0:
        return {f"p{int(q * 100):02d}": 0 for q in percentiles}
    cumulative = np.cumsum(histogram)
    return {
        f"p{int(q * 100):02d}": int(np.searchsorted(cumulative, q * (total - 1) + 1, side="left"))
        for q in percentiles
    }


def run(config_path: Path) -> dict[str, Any]:
    try:
        import tifffile
        import zarr
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("install the benchmark dependencies with: pip install '.[benchmark]'") from exc

    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    paths = {role: root / relative for role, relative in config["inputs"].items()}
    region_size = int(config["region_size"])
    min_valid_fraction = float(config["min_valid_fraction"])
    rows: list[dict[str, Any]] = []
    hist_prediction = np.zeros(256, dtype=np.int64)
    total_valid = 0
    total_ink = 0
    valid_y0: int | None = None
    valid_y1: int | None = None
    valid_x0: int | None = None
    valid_x1: int | None = None

    with ExitStack() as stack:
        tiffs = {role: stack.enter_context(tifffile.TiffFile(path)) for role, path in paths.items()}
        stores = {role: stack.enter_context(tiff.pages[0].aszarr()) for role, tiff in tiffs.items()}
        arrays = {role: zarr.open(store, mode="r") for role, store in stores.items()}
        shapes = {role: tuple(array.shape) for role, array in arrays.items()}
        dtypes = {role: str(array.dtype) for role, array in arrays.items()}
        if len(set(shapes.values())) != 1:
            raise ValueError(f"input shapes differ: {shapes}")
        height, width = next(iter(shapes.values()))

        for y0 in range(0, height, region_size):
            y1 = min(height, y0 + region_size)
            bands = {role: np.asarray(array[y0:y1, :]) for role, array in arrays.items()}
            band_valid = bands["supervision_mask"] > 0
            if band_valid.any():
                local_y, local_x = np.nonzero(band_valid)
                band_y0 = y0 + int(local_y.min())
                band_y1 = y0 + int(local_y.max()) + 1
                band_x0 = int(local_x.min())
                band_x1 = int(local_x.max()) + 1
                valid_y0 = band_y0 if valid_y0 is None else min(valid_y0, band_y0)
                valid_y1 = band_y1 if valid_y1 is None else max(valid_y1, band_y1)
                valid_x0 = band_x0 if valid_x0 is None else min(valid_x0, band_x0)
                valid_x1 = band_x1 if valid_x1 is None else max(valid_x1, band_x1)
            for x0 in range(0, width, region_size):
                x1 = min(width, x0 + region_size)
                pieces = {role: band[:, x0:x1] for role, band in bands.items()}
                stats = summarize_region(pieces["prediction"], pieces["ink_labels"], pieces["supervision_mask"])
                footprint = (y1 - y0) * (x1 - x0)
                valid_fraction = stats["valid_pixels"] / footprint
                eligible = valid_fraction >= min_valid_fraction
                rows.append(
                    {
                        "region_id": f"y{y0:05d}_x{x0:05d}",
                        "y0": y0,
                        "y1": y1,
                        "x0": x0,
                        "x1": x1,
                        "footprint_pixels": footprint,
                        "valid_fraction": valid_fraction,
                        "eligible": eligible,
                        **stats,
                    }
                )
                if stats["valid_pixels"]:
                    valid = pieces["supervision_mask"] > 0
                    hist_prediction += np.bincount(pieces["prediction"][valid], minlength=256)
                    total_valid += stats["valid_pixels"]
                    total_ink += stats["ink_pixels"]

    eligible_rows = [row for row in rows if row["eligible"]]
    ink_counts = np.asarray([row["ink_pixels"] for row in eligible_rows], dtype=np.int64)
    thresholds = [int(value) for value in config["diagnostic_positive_pixel_thresholds"]]
    report = {
        "experiment_id": config["experiment_id"],
        "status": "dev_inputs_audited_no_validation_access",
        "surface_key": config["surface_key"],
        "regime": "DEV",
        "coordinate_order": "Y,X surface pixels",
        "shapes": shapes,
        "dtypes": dtypes,
        "region_size": region_size,
        "min_valid_fraction": min_valid_fraction,
        "regions_total": len(rows),
        "regions_eligible": len(eligible_rows),
        "valid_pixels": total_valid,
        "ink_pixels": total_ink,
        "ink_fraction": total_ink / total_valid if total_valid else None,
        "supervision_bbox_yx_half_open": (
            [valid_y0, valid_y1, valid_x0, valid_x1] if valid_y0 is not None else None
        ),
        "eligible_region_ink_pixel_quantiles": {
            f"p{int(q * 100):02d}": float(np.quantile(ink_counts, q)) if ink_counts.size else None
            for q in [0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0]
        },
        "eligible_positive_region_counts": {
            str(threshold): int((ink_counts >= threshold).sum()) for threshold in thresholds
        },
        "prediction_valid_pixel_quantiles": _percentiles_from_histogram(
            hist_prediction, [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]
        ),
        "warning": "This is a DEV-only input audit. It does not validate physical ink, geometry, or structural enrichment.",
    }
    output_dir = root / config["outputs"]["directory"]
    _atomic_write(output_dir / config["outputs"]["report_json"], json.dumps(report, indent=2, sort_keys=True) + "\n")
    fields = list(rows[0])
    from io import StringIO
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    _atomic_write(output_dir / config["outputs"]["regions_csv"], stream.getvalue())
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
