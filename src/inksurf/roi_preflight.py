"""Deterministic blind ROI proposal and I/O preflight.

This command never opens Ink3D, Surface Prediction, CT, or the Grand Prize
banner. It only transforms the preserved Grand Prize chunk mask and proposes
spatially separated centers that must later be verified against a real TIFXYZ.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from .coordinates import apply_affine_zyx, chunk_centers_zyx, level0_to_level
from .io_plan import centered_bounds_zyx, intersecting_chunks_zyx, raw_chunk_bytes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
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


def _atomic_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
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


def select_density_candidates(
    points_zyx: np.ndarray,
    *,
    bin_shape_zyx: tuple[int, int, int],
    limit: int,
    minimum_separation: float,
) -> list[dict[str, Any]]:
    """Select dense occupied bins with deterministic non-maximum suppression."""
    points = np.asarray(points_zyx, dtype=np.float64)
    bins = np.asarray(bin_shape_zyx, dtype=np.int64)
    keys = np.floor_divide(points.astype(np.int64), bins)
    unique, inverse, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    order = sorted(range(len(unique)), key=lambda i: (-int(counts[i]), *map(int, unique[i])))
    selected: list[dict[str, Any]] = []
    for index in order:
        members = points[inverse == index]
        center = np.median(members, axis=0)
        if any(np.linalg.norm(center - np.asarray(item["center_zyx_l3"])) < minimum_separation for item in selected):
            continue
        selected.append(
            {
                "rank": len(selected) + 1,
                "density_count": int(counts[index]),
                "density_bin_zyx": unique[index].astype(int).tolist(),
                "center_zyx_l3": np.rint(center).astype(int).tolist(),
            }
        )
        if len(selected) == limit:
            break
    return selected


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    source = root / config["gp_chunk_mask"]["path"]
    source_sha256 = sha256_file(source)
    expected_sha256 = config["gp_chunk_mask"].get("expected_sha256")
    if expected_sha256 and source_sha256.lower() != expected_sha256.lower():
        raise ValueError(
            f"GP chunk mask checksum mismatch: {source_sha256} != {expected_sha256}"
        )
    points_2023 = chunk_centers_zyx(
        np.load(source, allow_pickle=False), tuple(config["gp_chunk_mask"]["chunk_shape_zyx_l0"])
    )
    points_2026_l0 = apply_affine_zyx(points_2023, np.asarray(config["transform"]["matrix_zyx"], dtype=float))
    level = int(config["target_arrays"]["level"])
    points_l3 = level0_to_level(points_2026_l0, level, rounding=False)
    proposal = config["proposal"]
    candidates = select_density_candidates(
        points_l3,
        bin_shape_zyx=tuple(proposal["density_bin_shape_zyx_l3"]),
        limit=int(proposal["candidate_count"]),
        minimum_separation=float(proposal["minimum_separation_l3_voxels"]),
    )
    array_shape = tuple(config["target_arrays"]["shape_zyx_l3"])
    chunk_shape = tuple(config["target_arrays"]["chunk_shape_zyx_l3"])
    roi_shape = tuple(proposal["provisional_roi_shape_zyx_l3"])
    arrays = int(config["target_arrays"]["array_count_for_budget"])
    dtype = config["target_arrays"]["dtype"]
    all_chunks: set[tuple[int, int, int]] = set()
    for candidate in candidates:
        lo, hi = centered_bounds_zyx(candidate["center_zyx_l3"], roi_shape, array_shape)
        chunks = intersecting_chunks_zyx(lo, hi, chunk_shape)
        all_chunks.update(chunks)
        candidate["provisional_bounds_lo_zyx_l3"] = lo.tolist()
        candidate["provisional_bounds_hi_zyx_l3"] = hi.tolist()
        candidate["intersecting_chunks_per_array"] = len(chunks)
        candidate["surface_status"] = "awaiting_verified_tifxyz"

    free_bytes = shutil.disk_usage(root).free
    estimated = raw_chunk_bytes(len(all_chunks), chunk_shape, dtype, arrays)
    payload: dict[str, Any] = {
        "experiment_id": config["experiment_id"],
        "status": "awaiting_surface_verification",
        "blind_selection": True,
        "selection_inputs": ["Grand Prize chunk occupancy mask", "documented 2023-to-2026 affine"],
        "excluded_selection_inputs": ["Grand Prize banner", "Ink3D values", "Surface Prediction values", "visual letter labels"],
        "coordinate_order": "Z,Y,X",
        "source": {
            "path": str(source.relative_to(root)).replace("\\", "/"),
            "sha256": source_sha256,
            "chunk_count": int(points_2023.shape[0]),
        },
        "config": {
            "path": str(config_path.resolve().relative_to(root)).replace("\\", "/"),
            "sha256": sha256_file(config_path),
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
        "io_budget": {
            "unique_chunks_across_candidates_per_array": len(all_chunks),
            "array_count": arrays,
            "conservative_raw_bytes": estimated,
            "free_disk_bytes_at_preflight": free_bytes,
            "fits_free_disk_at_2x_margin": estimated * 2 <= free_bytes,
            "download_performed": False,
            "ct_budget_status": "pending_ct_array_metadata",
        },
        "freeze_gate": config["freeze_gate"],
        "evaluation": config["evaluation"],
    }
    output_dir = root / config["outputs"]["directory"]
    _atomic_json(output_dir / config["outputs"]["report_json"], payload)
    flat_rows = [
        {
            "rank": c["rank"],
            "density_count": c["density_count"],
            "center_z_l3": c["center_zyx_l3"][0],
            "center_y_l3": c["center_zyx_l3"][1],
            "center_x_l3": c["center_zyx_l3"][2],
            "lo_z_l3": c["provisional_bounds_lo_zyx_l3"][0],
            "lo_y_l3": c["provisional_bounds_lo_zyx_l3"][1],
            "lo_x_l3": c["provisional_bounds_lo_zyx_l3"][2],
            "hi_z_l3": c["provisional_bounds_hi_zyx_l3"][0],
            "hi_y_l3": c["provisional_bounds_hi_zyx_l3"][1],
            "hi_x_l3": c["provisional_bounds_hi_zyx_l3"][2],
            "chunks_per_array": c["intersecting_chunks_per_array"],
            "surface_status": c["surface_status"],
        }
        for c in candidates
    ]
    _atomic_csv(output_dir / config["outputs"]["candidates_csv"], flat_rows)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = run(args.config)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
