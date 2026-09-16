"""Audit aligned DEV fragment IR, ink labels and mask without rendering them."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


def _bbox(mask: np.ndarray) -> list[int] | None:
    y, x = np.nonzero(mask)
    if y.size == 0:
        return None
    return [int(y.min()), int(y.max()) + 1, int(x.min()), int(x.max()) + 1]


def summarize(ir: np.ndarray, labels: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    if ir.shape != labels.shape or ir.shape != mask.shape or ir.ndim != 2:
        raise ValueError("IR, labels and mask must be aligned 2D arrays")
    valid = mask > 0
    ink = labels > 0
    if not valid.any():
        raise ValueError("fragment mask is empty")
    valid_ir = ir[valid].astype(np.float64, copy=False)
    quantiles = np.quantile(valid_ir, [0.01, 0.05, 0.5, 0.95, 0.99])
    ink_inside = ink & valid
    return {
        "shape_yx": list(ir.shape),
        "coordinate_order": "Y,X surface pixels",
        "valid_pixels": int(valid.sum()),
        "ink_pixels_inside_mask": int(ink_inside.sum()),
        "ink_pixels_outside_mask": int((ink & ~valid).sum()),
        "ink_fraction_inside_mask": float(ink_inside.sum() / valid.sum()),
        "mask_bbox_yx_half_open": _bbox(valid),
        "ink_bbox_yx_half_open": _bbox(ink_inside),
        "ir_valid_quantiles": {
            name: float(value)
            for name, value in zip(["p01", "p05", "p50", "p95", "p99"], quantiles, strict=True)
        },
    }


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
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
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("install fragment dependencies with pip install '.[fragment]'") from exc
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("regime") != "DEV":
        raise ValueError("asset audit is restricted to DEV")
    root = config_path.resolve().parent.parent
    arrays = {}
    modes = {}
    for role, relative in config["inputs"].items():
        with Image.open(root / relative) as image:
            modes[role] = image.mode
            arrays[role] = np.asarray(image)
    report = {
        "experiment_id": config["experiment_id"],
        "fragment": config["fragment"],
        "regime": "DEV",
        "status": "dev_assets_audited_no_visual_inspection",
        "image_modes": modes,
        **summarize(arrays["ir"], arrays["inklabels"], arrays["mask"]),
        "warning": "This audit establishes alignment and label support only; it is not a model result.",
    }
    _atomic_json(root / config["output_report"], report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
