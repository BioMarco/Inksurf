"""Verify extracted-CT support for a frozen set of surface candidates."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from inksurf.benchmark_baseline import _atomic_json
from inksurf.structural_features import _atomic_csv


def decoded_chunk_shape(
    index: tuple[int, int, int], shape: tuple[int, int, int], chunks: tuple[int, int, int]
) -> tuple[int, int, int]:
    return tuple(min(chunks[axis], shape[axis] - index[axis] * chunks[axis]) for axis in range(3))


def run(config_path: Path) -> dict[str, Any]:
    import tifffile
    from numcodecs import get_codec

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["regime"] != "DEV":
        raise PermissionError("CT-support audit currently permits DEV only")
    root = config_path.resolve().parent.parent
    package = json.loads((root / config["candidate_package"]).read_text(encoding="utf-8"))
    manifest = json.loads((root / config["chunk_manifest"]).read_text(encoding="utf-8"))
    download = json.loads((root / config["download_report"]).read_text(encoding="utf-8"))
    zarray = json.loads((root / config["zarray_metadata"]).read_text(encoding="utf-8"))
    if any(value["surface_id"] != config["surface_id"] for value in (package, manifest)):
        raise ValueError("surface mismatch between CT-support inputs")
    if download["manifest_snapshot_sha256"] != manifest["snapshot_sha256"]:
        raise ValueError("download report does not match frozen chunk manifest")
    local_by_role = {row["role"]: Path(row["local_path"]) for row in download["files"]}
    shape = tuple(int(value) for value in zarray["shape"])
    chunks = tuple(int(value) for value in zarray["chunks"])
    codec = get_codec(zarray["compressor"])
    chunk_arrays: dict[tuple[int, int, int], np.ndarray] = {}
    for row in manifest["files"]:
        index = tuple(int(value) for value in row["chunk_index_zyx"])
        path = local_by_role.get(row["role"])
        if path is None or not path.is_file():
            raise FileNotFoundError(f"downloaded chunk missing for {row['role']}")
        decoded = codec.decode(path.read_bytes())
        array = np.frombuffer(decoded, dtype=np.dtype(zarray["dtype"]))
        expected_shape = decoded_chunk_shape(index, shape, chunks)
        if array.size == math.prod(chunks):
            stored = array.reshape(chunks, order=zarray.get("order", "C"))
            chunk_arrays[index] = stored[tuple(slice(0, size) for size in expected_shape)]
        elif array.size == math.prod(expected_shape):
            chunk_arrays[index] = array.reshape(expected_shape, order=zarray.get("order", "C"))
        else:
            raise ValueError(f"decoded chunk shape mismatch for {row['role']}: {array.size} != {expected_shape}")

    mask = tifffile.imread(root / config["supervision_mask"], key=0) > 0
    if tuple(mask.shape) != shape[1:]:
        raise ValueError("supervision mask and surface volume shapes differ")
    central0, central1 = (int(value) for value in config["central_depth_range_half_open"])
    candidate_rows = []
    for candidate in package["candidates"]:
        bounds = candidate["bounds_yx"]
        height, width = bounds["y1"] - bounds["y0"], bounds["x1"] - bounds["x0"]
        volume = np.zeros((shape[0], height, width), dtype=np.dtype(zarray["dtype"]))
        covered = np.zeros_like(volume, dtype=bool)
        for index, chunk in chunk_arrays.items():
            cz, cy, cx = index
            global_start = (cz * chunks[0], cy * chunks[1], cx * chunks[2])
            global_stop = tuple(global_start[axis] + chunk.shape[axis] for axis in range(3))
            overlap_start = (0, max(bounds["y0"], global_start[1]), max(bounds["x0"], global_start[2]))
            overlap_stop = (shape[0], min(bounds["y1"], global_stop[1]), min(bounds["x1"], global_stop[2]))
            if overlap_start[1] >= overlap_stop[1] or overlap_start[2] >= overlap_stop[2]:
                continue
            source = (
                slice(0, chunk.shape[0]),
                slice(overlap_start[1] - global_start[1], overlap_stop[1] - global_start[1]),
                slice(overlap_start[2] - global_start[2], overlap_stop[2] - global_start[2]),
            )
            target = (
                slice(global_start[0], global_stop[0]),
                slice(overlap_start[1] - bounds["y0"], overlap_stop[1] - bounds["y0"]),
                slice(overlap_start[2] - bounds["x0"], overlap_stop[2] - bounds["x0"]),
            )
            volume[target] = chunk[source]
            covered[target] = True
        if not covered.all():
            raise RuntimeError(f"chunk manifest does not completely cover {candidate['candidate_id']}")
        supervised = mask[bounds["y0"]:bounds["y1"], bounds["x0"]:bounds["x1"]]
        count = int(supervised.sum())
        if count == 0:
            raise ValueError(f"candidate has no supervised pixels: {candidate['candidate_id']}")
        any_support = np.any(volume > 0, axis=0)
        central_support = np.any(volume[central0:central1] > 0, axis=0)
        nonzero_depth = np.mean(volume > 0, axis=0)
        any_fraction = float(any_support[supervised].mean())
        central_fraction = float(central_support[supervised].mean())
        passes = (
            any_fraction >= float(config["criteria"]["minimum_any_depth_support_fraction"])
            and central_fraction >= float(config["criteria"]["minimum_central_depth_support_fraction"])
        )
        candidate_rows.append({
            "candidate_id": candidate["candidate_id"], "rank": candidate["rank"],
            "supervised_pixels": count, "any_depth_support_fraction": any_fraction,
            "central_depth_support_fraction": central_fraction,
            "median_nonzero_depth_fraction": float(np.median(nonzero_depth[supervised])),
            "ct_intensity_p50_nonzero": float(np.median(volume[volume > 0])) if np.any(volume > 0) else None,
            "passes": passes,
        })
    all_pass = all(row["passes"] for row in candidate_rows)
    status = "pass" if (all_pass or not config["criteria"]["require_every_candidate_to_pass"]) else "fail"
    report = {
        "experiment_id": config["experiment_id"], "track": config["track"], "regime": "DEV",
        "surface_id": config["surface_id"], "status": status, "support_source": "published extracted surface volume",
        "array": {"shape_zyx": list(shape), "chunks_zyx": list(chunks), "dtype": zarray["dtype"]},
        "central_depth_range_half_open": [central0, central1], "criteria": config["criteria"],
        "candidate_count": len(candidate_rows), "passing_candidates": sum(row["passes"] for row in candidate_rows),
        "minimum_any_depth_support_fraction_observed": min(row["any_depth_support_fraction"] for row in candidate_rows),
        "minimum_central_depth_support_fraction_observed": min(row["central_depth_support_fraction"] for row in candidate_rows),
        "chunk_manifest_snapshot_sha256": manifest["snapshot_sha256"],
        "downloaded_or_verified_bytes": download["downloaded_or_verified_bytes"],
        "candidate_results": candidate_rows,
        "methodological_note": "This verifies nonzero CT evidence in the published extracted surface volume; it does not validate ink or the detector score.",
        "validation_files_accessed": 0,
    }
    _atomic_csv(root / config["outputs"]["candidates_csv"], candidate_rows)
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
