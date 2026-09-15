"""Create an exact raw-byte chunk manifest for a rectangular Zarr window."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np


def plan_window(shape: list[int], chunks: list[int], start: list[int], size: list[int]) -> list[dict[str, int]]:
    arrays = [np.asarray(value, dtype=np.int64) for value in (shape, chunks, start, size)]
    shape_a, chunks_a, start_a, size_a = arrays
    if any(len(value) != 3 for value in arrays) or np.any(chunks_a <= 0) or np.any(size_a <= 0):
        raise ValueError("shape, chunks, start and size must be positive Z,Y,X triples")
    stop = start_a + size_a
    if np.any(start_a < 0) or np.any(stop > shape_a):
        raise ValueError("window is outside array")
    ranges = [range(int(start_a[i] // chunks_a[i]), int((stop[i] - 1) // chunks_a[i]) + 1) for i in range(3)]
    rows = []
    for key in product(*ranges):
        chunk_start = np.asarray(key) * chunks_a
        chunk_stop = np.minimum(chunk_start + chunks_a, shape_a)
        rows.append({"z_chunk": key[0], "y_chunk": key[1], "x_chunk": key[2],
                     "raw_bytes": int(np.prod(chunk_stop - chunk_start))})
    return rows


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-zarr-window-plan/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("window planning must be Track A / DEV")
    rows = plan_window(config["shape_zyx"], config["chunks_zyx"], config["start_zyx"], config["size_zyx"])
    for row in rows:
        row["volume_id"] = config["volume_id"]
        row["object_key"] = f"{config['level']}/{row['z_chunk']}/{row['y_chunk']}/{row['x_chunk']}"
    total = sum(row["raw_bytes"] for row in rows)
    report = {"schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
              "track": config["track"], "regime": config["regime"], "status": "planned_not_downloaded",
              "chunk_objects": len(rows), "maximum_raw_bytes": total, "volumetric_bytes_downloaded": 0,
              "start_zyx": config["start_zyx"], "size_zyx": config["size_zyx"]}
    root = config_path.resolve().parent.parent
    _atomic_write(root / config["report_json"], json.dumps(report, indent=2, sort_keys=True) + "\n")
    from io import StringIO
    fields = ["volume_id", "z_chunk", "y_chunk", "x_chunk", "raw_bytes", "object_key"]
    stream = StringIO(newline=""); writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader(); writer.writerows(rows)
    _atomic_write(root / config["chunk_manifest_csv"], stream.getvalue())
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv); print(json.dumps(run(args.config), indent=2, sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
