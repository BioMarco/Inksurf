"""Audit physical TIFXYZ support only on frozen bounded evaluation pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

from .evidence_consistency import _atomic_json


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_npy(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            np.save(stream, array)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def evaluation_geometry(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    evaluation_mask: np.ndarray,
    *,
    chunk_yx: tuple[int, int],
    chunk_pixels: int,
    grid_step_pixels: int,
    voxel_um: float,
) -> tuple[dict, np.ndarray]:
    coordinates = np.stack((x, y, z), axis=-1).astype(np.float64, copy=False)
    valid_vertex = np.isfinite(coordinates).all(axis=-1) & ~np.all(coordinates == -1, axis=-1) & (z > 0)
    edge_u = coordinates[:-1, 1:] - coordinates[:-1, :-1]
    edge_v = coordinates[1:, :-1] - coordinates[:-1, :-1]
    normals = np.cross(edge_u, edge_v)
    quad_area_voxels2 = np.linalg.norm(normals, axis=-1)
    quad_valid = valid_vertex[:-1, :-1] & valid_vertex[:-1, 1:] & valid_vertex[1:, :-1] & valid_vertex[1:, 1:]

    rows, columns = np.indices(evaluation_mask.shape)
    global_rows = rows + int(chunk_yx[0]) * chunk_pixels
    global_columns = columns + int(chunk_yx[1]) * chunk_pixels
    cell_rows = global_rows // grid_step_pixels
    cell_columns = global_columns // grid_step_pixels
    selected = np.asarray(evaluation_mask, dtype=bool)
    if not selected.any():
        raise ValueError("evaluation mask is empty")
    if cell_rows[selected].max() >= quad_valid.shape[0] or cell_columns[selected].max() >= quad_valid.shape[1]:
        raise ValueError("evaluation pixels fall outside the TIFXYZ grid")
    selected_cells = np.zeros(quad_valid.shape, dtype=bool)
    selected_cells[cell_rows[selected], cell_columns[selected]] = True
    supported = quad_valid[cell_rows, cell_columns]
    areas_um2 = (
        quad_area_voxels2[cell_rows, cell_columns]
        * float(voxel_um) ** 2
        / float(grid_step_pixels ** 2)
    )
    selected_areas = areas_um2[selected]
    median_quad_area = float(np.median(quad_area_voxels2[quad_valid]))
    degenerate = selected_cells & (quad_area_voxels2 <= median_quad_area * 0.01)

    unit = np.zeros_like(normals)
    usable = quad_valid & (quad_area_voxels2 > 0)
    unit[usable] = normals[usable] / quad_area_voxels2[usable, None]
    flips = 0
    for left, right in (
        ((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
        ((slice(None, -1), slice(None)), (slice(1, None), slice(None))),
    ):
        pair_selected = selected_cells[left] & selected_cells[right] & usable[left] & usable[right]
        dots = np.sum(unit[left] * unit[right], axis=-1)
        flips += int((pair_selected & (dots < 0)).sum())
    report = {
        "chunk_yx": list(chunk_yx),
        "evaluated_pixels": int(selected.sum()),
        "unsupported_pixels": int((selected & ~supported).sum()),
        "selected_tifxyz_cells": int(selected_cells.sum()),
        "degenerate_selected_cells": int(degenerate.sum()),
        "adjacent_normal_flips_selected": flips,
        "pixel_area_um2_quantiles": dict(zip(
            ("min", "p01", "p50", "p99", "max"),
            map(float, np.quantile(selected_areas, [0, 0.01, 0.5, 0.99, 1])),
            strict=True,
        )),
        "evaluated_area_cm2": float(selected_areas.sum() / 100_000_000.0),
    }
    report["passes"] = (
        report["unsupported_pixels"] == 0
        and report["degenerate_selected_cells"] == 0
        and report["adjacent_normal_flips_selected"] == 0
    )
    return report, areas_um2.astype(np.float32)


def run(config_path: Path) -> dict:
    import tifffile

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-roi-geometry-audit/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("bounded ROI geometry audit is Track A DEV only")
    root = config_path.resolve().parent.parent
    upstream_path = root / config["whole_surface_geometry_report"]
    if _sha256(upstream_path) != config["whole_surface_geometry_sha256"]:
        raise ValueError("whole-surface geometry report hash mismatch")
    upstream = json.loads(upstream_path.read_text(encoding="utf-8"))
    if not upstream["volume_bounds"]["verified"] or not upstream["ct_support_verified"]:
        raise ValueError("upstream bounds and CT support must pass")
    geometry = upstream["geometry"]
    continuity_passes = all(
        item["within_spacing_tolerance"] and item["abrupt_jumps"] == 0
        for item in geometry["continuity"].values()
    )
    if not (
        geometry["nonfinite_vertices"] == 0
        and geometry["partial_sentinel_vertices"] == 0
        and geometry["largest_component_fraction"] >= 0.99
        and continuity_passes
        and upstream["raster_mapping"]["integer_aligned"]
    ):
        raise ValueError("whole-surface continuity and mapping preconditions failed")
    coordinate_paths = {key: root / value for key, value in config["coordinate_files"].items()}
    arrays = {key: tifffile.imread(path, key=0) for key, path in coordinate_paths.items()}
    chunk_report_path = root / config["chunk_audit_report"]
    if _sha256(chunk_report_path) != config["chunk_audit_sha256"]:
        raise ValueError("chunk audit report hash mismatch")
    chunks = json.loads(chunk_report_path.read_text(encoding="utf-8"))["chunks"]
    rows = []
    area_root = root / config["area_output_directory"]
    area_root.mkdir(parents=True, exist_ok=True)
    for item in chunks:
        derived_path = root / item["derived"]
        with np.load(derived_path) as archive:
            mask = np.asarray(archive["validation_mask"], dtype=bool)
        chunk_yx = tuple(int(value) for value in item["chunk_yx"])
        row, area = evaluation_geometry(
            arrays["x"], arrays["y"], arrays["z"], mask,
            chunk_yx=chunk_yx,
            chunk_pixels=int(config["chunk_pixels"]),
            grid_step_pixels=int(config["grid_step_level2_pixels"]),
            voxel_um=float(config["voxel_um"]),
        )
        area_path = area_root / f"chunk_{chunk_yx[0]}_{chunk_yx[1]}.npy"
        _atomic_npy(area_path, area)
        row["pixel_area_map"] = str(area_path.relative_to(root)).replace("\\", "/")
        row["pixel_area_sha256"] = _sha256(area_path)
        rows.append(row)
    all_pass = all(row["passes"] for row in rows)
    report = {
        "schema_version": config["schema_version"],
        "experiment_id": config["experiment_id"],
        "track": "A", "regime": "DEV",
        "surface_id": config["surface_id"],
        "geometry_scope": "frozen_bounded_evaluation_pixels",
        "recommended_geometry_tier": "G2" if all_pass else "G1",
        "status": "pass" if all_pass else "fail",
        "chunks": rows,
        "evaluated_pixels": sum(row["evaluated_pixels"] for row in rows),
        "evaluated_area_cm2": sum(row["evaluated_area_cm2"] for row in rows),
        "coordinate_sha256": {key: _sha256(path) for key, path in coordinate_paths.items()},
        "whole_surface_geometry_report": config["whole_surface_geometry_report"],
        "whole_surface_geometry_sha256": config["whole_surface_geometry_sha256"],
        "claim": "G2 applies only to the frozen bounded evaluation pixels, not to the whole surface or to ink validity.",
    }
    _atomic_json(root / config["output_report"], report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
