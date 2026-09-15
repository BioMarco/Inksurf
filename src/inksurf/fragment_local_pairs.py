"""Sample unique, locally matched DEV ink/control pixel pairs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from inksurf.benchmark_baseline import _atomic_json
from inksurf.structural_features import _atomic_csv


def match_local_controls(
    ink_points: np.ndarray,
    control_mask: np.ndarray,
    *,
    maximum: int,
    minimum_distance: int,
    maximum_distance: int,
    attempts: int,
    rng: np.random.Generator,
) -> list[tuple[int, int, int, int, float]]:
    if ink_points.ndim != 2 or ink_points.shape[1] != 2:
        raise ValueError("ink_points must have shape N,2 in Y,X order")
    order = rng.permutation(len(ink_points))
    used_controls: set[tuple[int, int]] = set()
    pairs = []
    height, width = control_mask.shape
    for index in order:
        if len(pairs) >= maximum:
            break
        iy, ix = (int(value) for value in ink_points[index])
        for _ in range(attempts):
            dy = int(rng.integers(-maximum_distance, maximum_distance + 1))
            dx = int(rng.integers(-maximum_distance, maximum_distance + 1))
            distance = float(np.hypot(dy, dx))
            if distance < minimum_distance or distance > maximum_distance:
                continue
            cy, cx = iy + dy, ix + dx
            if not (0 <= cy < height and 0 <= cx < width):
                continue
            coordinate = (cy, cx)
            if control_mask[cy, cx] and coordinate not in used_controls:
                used_controls.add(coordinate)
                pairs.append((iy, ix, cy, cx, distance))
                break
    return pairs


def run(config_path: Path) -> dict[str, Any]:
    try:
        from PIL import Image
        from scipy.ndimage import binary_dilation
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("install fragment and structure dependencies") from exc
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("regime") != "DEV":
        raise ValueError("local matching is restricted to DEV")
    root = config_path.resolve().parent.parent
    with Image.open(root / config["inklabels"]) as image:
        ink = np.asarray(image) > 0
    with Image.open(root / config["mask"]) as image:
        valid = np.asarray(image) > 0
    control = valid & ~binary_dilation(ink, iterations=int(config["control_exclusion_radius"]))
    block_size = int(config["block_size"])
    rng = np.random.default_rng(int(config["seed"]))
    rows: list[dict[str, Any]] = []
    blocks = []
    pair_id = 0
    for y0 in range(0, ink.shape[0], block_size):
        y1 = min(ink.shape[0], y0 + block_size)
        for x0 in range(0, ink.shape[1], block_size):
            x1 = min(ink.shape[1], x0 + block_size)
            local_y, local_x = np.nonzero(ink[y0:y1, x0:x1] & valid[y0:y1, x0:x1])
            # Match in block-local coordinates.  This avoids allocating a
            # full-fragment control mask for every spatial block and also
            # guarantees that a pair never crosses a block boundary.
            points = np.column_stack((local_y, local_x))
            pairs = match_local_controls(
                points, control[y0:y1, x0:x1],
                maximum=int(config["max_pairs_per_block"]),
                minimum_distance=int(config["minimum_pair_distance"]),
                maximum_distance=int(config["maximum_pair_distance"]),
                attempts=int(config["attempts_per_ink"]), rng=rng,
            )
            if not pairs:
                continue
            block_id = f"by{y0 // block_size:02d}_bx{x0 // block_size:02d}"
            blocks.append({"block_id": block_id, "pairs": len(pairs)})
            for local_iy, local_ix, local_cy, local_cx, distance in pairs:
                iy, ix = local_iy + y0, local_ix + x0
                cy, cx = local_cy + y0, local_cx + x0
                rows.append({"pair_id": pair_id, "role": "ink", "label": 1, "block_id": block_id,
                             "y": iy, "x": ix, "pair_distance": distance})
                rows.append({"pair_id": pair_id, "role": "control", "label": 0, "block_id": block_id,
                             "y": cy, "x": cx, "pair_distance": distance})
                pair_id += 1
    if not rows:
        raise RuntimeError("no local pairs could be sampled")
    distances = np.asarray([row["pair_distance"] for row in rows[::2]])
    report = {
        "experiment_id": config["experiment_id"], "regime": "DEV",
        "status": "local_pairs_frozen_validation_locked", "coordinate_order": "Y,X",
        "pairs": pair_id, "samples": len(rows), "blocks": len(blocks),
        "blocks_detail": blocks, "minimum_pair_distance": int(config["minimum_pair_distance"]),
        "maximum_pair_distance": int(config["maximum_pair_distance"]),
        "distance_quantiles": {name: float(value) for name, value in zip(
            ("p01", "p50", "p99"), np.quantile(distances, [0.01, 0.5, 0.99]), strict=True)},
        "duplicate_ink_coordinates": pair_id - len({(row["y"], row["x"]) for row in rows if row["label"] == 1}),
        "duplicate_control_coordinates": pair_id - len({(row["y"], row["x"]) for row in rows if row["label"] == 0}),
        "warning": "DEV-only matching. Pair construction used labels and must never run on VALIDATION.",
    }
    _atomic_csv(root / config["outputs"]["pairs_csv"], rows)
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
