"""Plan exact chunks for a bounded, deterministic seating reproduction."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def densest_square(mask: np.ndarray, size: int) -> tuple[int, int, int]:
    if mask.ndim != 2 or size <= 0 or size > min(mask.shape):
        raise ValueError("invalid mask or square size")
    integral = np.pad(mask.astype(np.int64), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    sums = integral[size:, size:] - integral[:-size, size:] - integral[size:, :-size] + integral[:-size, :-size]
    row, col = np.unravel_index(np.argmax(sums), sums.shape)
    return int(row), int(col), int(sums[row, col])


def chunk_keys(points_zyx: np.ndarray, normals_zyx: np.ndarray, offsets: np.ndarray, chunk: int) -> np.ndarray:
    samples = np.rint(
        points_zyx[:, None, :] + normals_zyx[:, None, :] * offsets[None, :, None]
    ).astype(np.int64)
    return np.unique(samples.reshape(-1, 3) // int(chunk), axis=0)


def _central(values: np.ndarray, axis: int) -> np.ndarray:
    gradient = np.zeros_like(values)
    if axis == 1:
        gradient[:, 1:-1] = values[:, 2:] - values[:, :-2]
        gradient[:, 0] = 2 * (values[:, 1] - values[:, 0])
        gradient[:, -1] = 2 * (values[:, -1] - values[:, -2])
    else:
        gradient[1:-1] = values[2:] - values[:-2]
        gradient[0] = 2 * (values[1] - values[0])
        gradient[-1] = 2 * (values[-1] - values[-2])
    return gradient


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def run(config_path: Path) -> dict[str, Any]:
    try:
        import tifffile
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("TIFF support requires the benchmark dependencies") from exc
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-seating-io-plan/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("seating I/O planning must be Track A / DEV")
    root = config_path.resolve().parent.parent
    arrays = []
    for axis in "xyz":
        spec = config["mesh"][axis]
        path = root / spec["path"]
        digest = _sha256(path)
        if digest != spec["sha256"]:
            raise RuntimeError(f"mesh SHA256 mismatch: {axis}")
        arrays.append(tifffile.imread(path).astype(np.float64))
    x, y, z = arrays
    if x.shape != y.shape or x.shape != z.shape:
        raise ValueError("TIFXYZ shapes differ")
    valid = (x > 0) & (y > 0) & (z > 0)

    edge_lengths = []
    for dr, dc in ((0, 1), (1, 0)):
        a = np.stack([x[dr:, dc:], y[dr:, dc:], z[dr:, dc:]], axis=-1)
        b = np.stack([x[: x.shape[0] - dr or None, : x.shape[1] - dc or None],
                      y[: y.shape[0] - dr or None, : y.shape[1] - dc or None],
                      z[: z.shape[0] - dr or None, : z.shape[1] - dc or None]], axis=-1)
        mask = valid[dr:, dc:] & valid[: valid.shape[0] - dr or None, : valid.shape[1] - dc or None]
        edge_lengths.append(np.linalg.norm(a - b, axis=-1)[mask])
    grid_step_voxels = float(np.median(np.concatenate(edge_lengths)))
    crop_pixels = int(round(float(config["crop_size_mm"]) * 1000 / (
        grid_step_voxels * float(config["mesh"]["voxel_um"])
    )))
    crop_pixels = min(crop_pixels, min(valid.shape))
    row0, col0, valid_count = densest_square(valid, crop_pixels)

    ux, uy, uz = _central(x, 1), _central(y, 1), _central(z, 1)
    vx, vy, vz = _central(x, 0), _central(y, 0), _central(z, 0)
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    norm = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-9
    indexes = np.argwhere(valid[row0:row0 + crop_pixels, col0:col0 + crop_pixels])
    indexes += np.array([row0, col0])
    count = min(int(config["sample_count"]), len(indexes))
    rng = np.random.default_rng(int(config["seed"]))
    indexes = indexes[rng.choice(len(indexes), size=count, replace=False)]
    rows, cols = indexes[:, 0], indexes[:, 1]
    level_divisor = 2 ** int(config["level"])
    points = np.stack([z[rows, cols], y[rows, cols], x[rows, cols]], axis=1) / level_divisor
    normals = np.stack([nz[rows, cols], ny[rows, cols], nx[rows, cols]], axis=1) / norm[rows, cols, None]
    span = int(config["probe_span_level_voxels"])
    offsets = np.r_[0.0, np.arange(2.0, span, 2.0), -np.arange(2.0, span, 2.0)]
    keys = chunk_keys(points, normals, offsets, int(config["chunk_shape_zyx"][0]))

    manifest_rows = []
    for volume in config["volumes"]:
        shape = np.asarray(volume["shape_zyx"], dtype=np.int64)
        chunk_shape = np.asarray(config["chunk_shape_zyx"], dtype=np.int64)
        for key in keys:
            start = key * chunk_shape
            stop = np.minimum(start + chunk_shape, shape)
            if np.any(start < 0) or np.any(start >= shape):
                continue
            manifest_rows.append({
                "volume_id": volume["volume_id"], "z_chunk": int(key[0]),
                "y_chunk": int(key[1]), "x_chunk": int(key[2]),
                "raw_bytes": int(np.prod(stop - start)),
                "object_key": f"{config['level']}/{key[0]}/{key[1]}/{key[2]}",
            })
    raw_bytes = sum(row["raw_bytes"] for row in manifest_rows)
    report = {
        "schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
        "track": config["track"], "regime": config["regime"], "status": "planned_not_downloaded",
        "axes": "Z,Y,X", "mesh_shape": list(x.shape), "valid_mesh_points": int(valid.sum()),
        "grid_step_voxels_median": grid_step_voxels, "crop_pixels": crop_pixels,
        "crop_origin_row_col": [row0, col0], "crop_valid_fraction": valid_count / crop_pixels**2,
        "sample_count": count, "seed": int(config["seed"]), "probe_offsets": len(offsets),
        "unique_chunks_per_volume": len(keys), "total_chunk_objects": len(manifest_rows),
        "maximum_raw_bytes": raw_bytes, "volumetric_bytes_downloaded": 0,
    }
    _atomic_write(root / config["outputs"]["report_json"], json.dumps(report, indent=2, sort_keys=True) + "\n")
    from io import StringIO
    stream = StringIO(newline="")
    fields = ["volume_id", "z_chunk", "y_chunk", "x_chunk", "raw_bytes", "object_key"]
    writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(manifest_rows)
    _atomic_write(root / config["outputs"]["chunk_manifest_csv"], stream.getvalue())
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
