"""Reproduce the seating metric on a bounded DEV crop from a frozen local chunk cache."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .seating_io_plan import _central, densest_square


def probe_and_score(
    points_zyx: np.ndarray,
    normals_zyx: np.ndarray,
    reader: Callable[[np.ndarray], np.ndarray],
    span: int,
) -> dict[str, float]:
    steps = np.arange(2.0, float(span), 2.0)
    means = []
    for step in steps:
        positive = reader(np.rint(points_zyx + normals_zyx * step).astype(np.int64))
        negative = reader(np.rint(points_zyx - normals_zyx * step).astype(np.int64))
        means.append(0.5 * (positive.mean() + negative.mean()))
    smooth = np.convolve(np.asarray(means), np.ones(3) / 3, mode="same")
    gap = float(steps[int(np.argmin(smooth))])
    for index in range(1, len(smooth) - 1):
        if smooth[index] <= smooth[index - 1] and smooth[index] <= smooth[index + 1]:
            gap = float(steps[index]); break
    centre = reader(np.rint(points_zyx).astype(np.int64))
    before = reader(np.rint(points_zyx - normals_zyx * gap).astype(np.int64))
    after = reader(np.rint(points_zyx + normals_zyx * gap).astype(np.int64))
    on = centre > 40
    coverage = float(on.mean())
    if coverage < 0.25:
        score = -1.0
        contrast = float("nan")
        surface_mean = float(centre.mean())
    else:
        contrast = float((centre[on] - 0.5 * (before[on] + after[on])).mean())
        score = contrast * coverage
        surface_mean = float(centre[on].mean())
    return {"score": score, "coverage": coverage, "contrast": contrast,
            "surface_mean": surface_mean, "gap_level_voxels": gap}


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=True); stream.write("\n")
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def run(config_path: Path) -> dict[str, Any]:
    import tifffile
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-seating-reproduction/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("seating reproduction must be Track A / DEV")
    root = config_path.resolve().parent.parent
    x, y, z = [
        tifffile.imread(root / config["mesh"][axis]).astype(np.float64) for axis in "xyz"
    ]
    valid = (x > 0) & (y > 0) & (z > 0)
    size = int(config["crop_pixels"])
    row0, col0, _ = densest_square(valid, size)
    ux, uy, uz = _central(x, 1), _central(y, 1), _central(z, 1)
    vx, vy, vz = _central(x, 0), _central(y, 0), _central(z, 0)
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    norm = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-9
    indexes = np.argwhere(valid[row0:row0 + size, col0:col0 + size]) + [row0, col0]
    rng = np.random.default_rng(int(config["seed"]))
    indexes = indexes[rng.choice(len(indexes), size=int(config["sample_count"]), replace=False)]
    rows, cols = indexes[:, 0], indexes[:, 1]
    divisor = 2 ** int(config["level"])
    points = np.stack([z[rows, cols], y[rows, cols], x[rows, cols]], 1) / divisor
    normals = np.stack([nz[rows, cols], ny[rows, cols], nx[rows, cols]], 1) / norm[rows, cols, None]
    chunk_size = int(config["chunk_shape_zyx"][0])

    results = []
    for volume in config["volumes"]:
        cache = root / config["cache_root"] / volume["volume_id"] / str(config["level"])
        loaded: dict[tuple[int, int, int], np.ndarray] = {}
        def reader(coordinates: np.ndarray) -> np.ndarray:
            values = np.zeros(len(coordinates), dtype=np.float32)
            for index, coordinate in enumerate(coordinates):
                key = tuple((coordinate // chunk_size).tolist())
                if key not in loaded:
                    path = cache.joinpath(*(str(item) for item in key))
                    if not path.exists():
                        loaded[key] = np.zeros((chunk_size,) * 3, dtype=np.uint8)
                    else:
                        loaded[key] = np.fromfile(path, dtype=np.uint8).reshape((chunk_size,) * 3)
                local = coordinate % chunk_size
                values[index] = loaded[key][tuple(local)]
            return values
        metrics = probe_and_score(points, normals, reader, int(config["probe_span_level_voxels"]))
        results.append({"volume_id": volume["volume_id"], **metrics, "chunks_read": len(loaded)})
    report = {
        "schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
        "track": config["track"], "regime": config["regime"],
        "status": "bounded_dev_reproduction_complete", "crop_origin_row_col": [row0, col0],
        "crop_pixels": size, "sample_count": int(config["sample_count"]),
        "seed": int(config["seed"]), "results": results,
        "claim": "A bounded DEV seating measurement is geometry QA, not evidence of ink.",
    }
    _atomic_json(root / config["report_json"], report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
