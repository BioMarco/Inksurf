"""Build an exact metadata-only chunk plan for candidate CT-support QA."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any

from inksurf.benchmark_baseline import _atomic_json


def candidate_chunk_indices(
    candidates: list[dict[str, Any]],
    *,
    shape: tuple[int, int, int],
    chunks: tuple[int, int, int],
    depth_range: tuple[int, int],
) -> list[tuple[int, int, int]]:
    z0, z1 = depth_range
    if not (0 <= z0 < z1 <= shape[0]):
        raise ValueError("depth range is outside the surface volume")
    selected: set[tuple[int, int, int]] = set()
    for candidate in candidates:
        bounds = candidate["bounds_yx"]
        if not (0 <= bounds["y0"] < bounds["y1"] <= shape[1] and 0 <= bounds["x0"] < bounds["x1"] <= shape[2]):
            raise ValueError(f"candidate outside surface volume: {candidate['candidate_id']}")
        for cz in range(z0 // chunks[0], math.ceil(z1 / chunks[0])):
            for cy in range(bounds["y0"] // chunks[1], math.ceil(bounds["y1"] / chunks[1])):
                for cx in range(bounds["x0"] // chunks[2], math.ceil(bounds["x1"] / chunks[2])):
                    selected.add((cz, cy, cx))
    return sorted(selected)


def run(config_path: Path) -> dict[str, Any]:
    from huggingface_hub import list_bucket_tree

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["regime"] != "DEV":
        raise PermissionError("CT-support preflight currently permits DEV only")
    root = config_path.resolve().parent.parent
    package_path = root / config["candidate_package"]
    package = json.loads(package_path.read_text(encoding="utf-8"))
    if package["regime"] != "DEV" or package["surface_id"] != config["surface_id"]:
        raise ValueError("candidate package regime/surface mismatch")
    zarray_path = root / config["local_zarray_metadata"]
    zarray = json.loads(zarray_path.read_text(encoding="utf-8"))
    shape = tuple(int(value) for value in zarray["shape"])
    chunks = tuple(int(value) for value in zarray["chunks"])
    depth_range = tuple(int(value) for value in config["depth_range_half_open"])
    indices = candidate_chunk_indices(
        package["candidates"], shape=shape, chunks=chunks, depth_range=depth_range,
    )
    separator = zarray.get("dimension_separator", ".")
    keys = {separator.join(str(value) for value in index): index for index in indices}
    wanted_paths = {f"{config['remote_array_prefix']}/{key}": (key, index) for key, index in keys.items()}
    remote = {}
    listed = 0
    for item in list_bucket_tree(config["bucket_id"], prefix=config["remote_array_prefix"], recursive=False):
        listed += 1
        if item.type == "file" and item.path in wanted_paths:
            remote[item.path] = item
    missing = sorted(set(wanted_paths) - set(remote))
    if missing:
        raise RuntimeError(f"{len(missing)} required chunks missing from remote listing")
    files = []
    for path in sorted(remote):
        key, index = wanted_paths[path]
        item = remote[path]
        files.append({
            "surface_key": "0139_w035_dev_ct_support", "scroll_id": "0139", "regime": "DEV",
            "external_domain": False, "stage": config["stage"], "role": "chunk_" + key.replace(separator, "_"),
            "path": path, "chunk_index_zyx": list(index), "size_bytes": int(item.size),
            "xet_hash": str(item.xet_hash),
        })
    total = sum(row["size_bytes"] for row in files)
    if total > int(config["maximum_download_bytes"]):
        raise RuntimeError(f"chunk plan exceeds cap: {total} > {config['maximum_download_bytes']}")
    free = shutil.disk_usage(root).free
    if free < total * int(config["minimum_free_space_multiplier"]):
        raise RuntimeError("insufficient free-space margin")
    package_sha = hashlib.sha256(package_path.read_bytes()).hexdigest()
    zarray_sha = hashlib.sha256(zarray_path.read_bytes()).hexdigest()
    snapshot_payload = {
        "experiment_id": config["experiment_id"], "bucket_id": config["bucket_id"],
        "surface_id": config["surface_id"], "candidate_package_sha256": package_sha,
        "zarray_sha256": zarray_sha, "files": files,
    }
    snapshot_sha = hashlib.sha256(json.dumps(snapshot_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    manifest = {**snapshot_payload, "snapshot_sha256": snapshot_sha}
    raw_per_chunk = chunks[0] * chunks[1] * chunks[2]
    report = {
        "experiment_id": config["experiment_id"], "track": config["track"], "regime": "DEV",
        "surface_id": config["surface_id"], "status": "download_plan_frozen",
        "candidate_count": len(package["candidates"]), "candidate_package_sha256": package_sha,
        "array": {"shape_zyx": list(shape), "chunks_zyx": list(chunks), "dtype": zarray["dtype"],
                  "dimension_separator": separator, "zarray_sha256": zarray_sha},
        "depth_range_half_open": list(depth_range), "unique_chunks": len(files),
        "remote_compressed_bytes": total, "maximum_download_bytes": int(config["maximum_download_bytes"]),
        "conservative_decoded_bytes": len(files) * raw_per_chunk,
        "free_space_bytes": free, "remote_objects_listed_metadata_only": listed,
        "manifest_snapshot_sha256": snapshot_sha, "downloaded_bytes": 0,
        "validation_files_accessed": 0,
    }
    _atomic_json(root / config["outputs"]["manifest_json"], manifest)
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
