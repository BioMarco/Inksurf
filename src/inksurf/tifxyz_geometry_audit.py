"""Audit a local TIFXYZ grid without claiming unverified CT support."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from inksurf.benchmark_baseline import _atomic_json


def _bounded_get_json(url: str, *, maximum_bytes: int, timeout: int) -> tuple[dict[str, Any], str, int]:
    import requests

    with requests.get(url, timeout=timeout, stream=True) as response:
        response.raise_for_status()
        declared = response.headers.get("content-length")
        if declared and int(declared) > maximum_bytes:
            raise RuntimeError(f"metadata response exceeds cap: {declared} > {maximum_bytes}")
        chunks = []
        size = 0
        for chunk in response.iter_content(65536):
            if not chunk:
                continue
            size += len(chunk)
            if size > maximum_bytes:
                raise RuntimeError(f"metadata response exceeds cap: {size} > {maximum_bytes}")
            chunks.append(chunk)
    raw = b"".join(chunks)
    return json.loads(raw), hashlib.sha256(raw).hexdigest(), len(raw)


def audit_geometry_arrays(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    *,
    expected_spacing: float,
    spacing_tolerance: float,
    maximum_jump_factor: float,
) -> tuple[dict[str, Any], np.ndarray]:
    if x.shape != y.shape or x.shape != z.shape or x.ndim != 2:
        raise ValueError("x/y/z must be same-shape 2D arrays")
    finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    all_sentinel = (x == -1) & (y == -1) & (z == -1)
    any_sentinel = (x == -1) | (y == -1) | (z == -1)
    partial_sentinel = any_sentinel & ~all_sentinel
    valid = finite & ~all_sentinel & ~partial_sentinel & (z > 0)
    if not valid.any():
        raise ValueError("TIFXYZ contains no valid vertices")

    from scipy.ndimage import label

    components, count = label(valid, structure=np.ones((3, 3), dtype=np.uint8))
    sizes = np.bincount(components.ravel())[1:]
    coordinate_stack = np.stack((x, y, z), axis=-1).astype(np.float64, copy=False)
    direction_results: dict[str, Any] = {}
    distances_by_direction: dict[str, np.ndarray] = {}
    for name, (left, right) in {
        "u": ((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
        "v": ((slice(None, -1), slice(None)), (slice(1, None), slice(None))),
    }.items():
        edge_valid = valid[left] & valid[right]
        distances = np.linalg.norm(coordinate_stack[right] - coordinate_stack[left], axis=-1)[edge_valid]
        distances_by_direction[name] = distances
        median = float(np.median(distances))
        quantiles = np.quantile(distances, [0.0, 0.01, 0.5, 0.99, 1.0])
        direction_results[name] = {
            "valid_edges": int(distances.size),
            "distance_quantiles_voxels": dict(zip(("min", "p01", "p50", "p99", "max"), map(float, quantiles), strict=True)),
            "median_relative_error": abs(median - expected_spacing) / expected_spacing,
            "within_spacing_tolerance": abs(median - expected_spacing) / expected_spacing <= spacing_tolerance,
            "abrupt_jumps": int((distances > expected_spacing * maximum_jump_factor).sum()),
        }

    quad_valid = valid[:-1, :-1] & valid[:-1, 1:] & valid[1:, :-1] & valid[1:, 1:]
    edge_u = coordinate_stack[:-1, 1:] - coordinate_stack[:-1, :-1]
    edge_v = coordinate_stack[1:, :-1] - coordinate_stack[:-1, :-1]
    normals = np.cross(edge_u, edge_v)
    areas = np.linalg.norm(normals, axis=-1)
    valid_areas = areas[quad_valid]
    median_area = float(np.median(valid_areas)) if valid_areas.size else 0.0
    degenerate = quad_valid & (areas <= median_area * 0.01) if valid_areas.size else np.zeros_like(quad_valid)
    unit_normals = np.zeros_like(normals)
    usable = quad_valid & (areas > 0)
    unit_normals[usable] = normals[usable] / areas[usable][:, None]
    normal_pairs = []
    for left, right in (
        ((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
        ((slice(None, -1), slice(None)), (slice(1, None), slice(None))),
    ):
        pair_valid = usable[left] & usable[right]
        dots = np.sum(unit_normals[left] * unit_normals[right], axis=-1)[pair_valid]
        normal_pairs.append(dots)
    normal_dots = np.concatenate(normal_pairs)

    bounds = [[float(values[valid].min()) for values in (x, y, z)],
              [float(values[valid].max()) for values in (x, y, z)]]
    report = {
        "grid_shape_uv": list(x.shape), "vertices": int(x.size), "valid_vertices": int(valid.sum()),
        "invalid_vertices": int((~valid).sum()), "nonfinite_vertices": int((~finite & ~all_sentinel).sum()),
        "partial_sentinel_vertices": int(partial_sentinel.sum()), "actual_bounds_xyz": bounds,
        "valid_components_8_connected": int(count),
        "largest_component_fraction": float(sizes.max() / valid.sum()),
        "continuity": direction_results,
        "topology": {
            "valid_quads": int(quad_valid.sum()), "degenerate_quads": int(degenerate.sum()),
            "median_parallelogram_area_voxels2": median_area,
            "adjacent_normal_pairs": int(normal_dots.size),
            "adjacent_normal_flips": int((normal_dots < 0).sum()),
            "adjacent_normal_dot_p01": float(np.quantile(normal_dots, 0.01)) if normal_dots.size else None,
        },
    }
    return report, valid


def run(config_path: Path) -> dict[str, Any]:
    import tifffile

    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    arrays = {
        name: tifffile.imread(root / relative, key=0)
        for name, relative in config["coordinate_files"].items()
    }
    geometry, valid = audit_geometry_arrays(
        arrays["x"], arrays["y"], arrays["z"],
        expected_spacing=float(config["expected_grid_spacing_voxels"]),
        spacing_tolerance=float(config["spacing_relative_tolerance"]),
        maximum_jump_factor=float(config["maximum_jump_factor"]),
    )
    if config.get("reference_shape_yx"):
        reference_shape = tuple(int(value) for value in config["reference_shape_yx"])
    else:
        with tifffile.TiffFile(root / config["reference_raster"]) as tif:
            reference_shape = tuple(int(value) for value in tif.pages[0].shape)
    grid_shape = tuple(int(value) for value in arrays["x"].shape)
    ratios = tuple(reference_shape[index] / grid_shape[index] for index in range(2))
    integer_mapping = all(float(value).is_integer() and value > 0 for value in ratios)
    mapping: dict[str, Any] = {
        "reference_shape_yx": list(reference_shape), "grid_shape_uv": list(grid_shape),
        "reference_pixels_per_grid_step_yx": list(ratios), "integer_aligned": integer_mapping,
    }
    if config.get("supervision_mask"):
        mask = tifffile.imread(root / config["supervision_mask"], key=0) > 0
        if tuple(mask.shape) != reference_shape:
            raise ValueError("supervision mask does not match reference raster")
        if not integer_mapping:
            raise ValueError("cannot audit mask coverage without integer raster/grid ratio")
        ry, rx = (int(value) for value in ratios)
        cell_counts = mask.reshape(grid_shape[0], ry, grid_shape[1], rx).sum(axis=(1, 3))
        supervised = int(cell_counts.sum())
        unsupported = int(cell_counts[~valid].sum())
        mapping["supervised_reference_pixels"] = supervised
        mapping["supervised_pixels_mapped_to_invalid_vertex_cell"] = unsupported
        mapping["supervision_geometry_coverage_fraction"] = float((supervised - unsupported) / supervised) if supervised else None
        del mask, cell_counts

    parent = config.get("parent_volume")
    parent_provenance = None
    volume_shape = None
    association_verified = False
    if parent:
        timeout = int(parent["timeout_seconds"])
        catalog, catalog_sha, catalog_bytes = _bounded_get_json(
            parent["catalog_url"], maximum_bytes=int(parent["catalog_max_bytes"]), timeout=timeout,
        )
        scroll = next(item for item in catalog["scrolls"] if item["id"] == parent["scroll_id"])
        segment = next(item for item in scroll["inkSegments"] if item.get("label") == parent["segment_label"])
        target = str(parent["target_volume_id"])
        association_verified = target in str(segment.get("layers", "")) or any(
            str(render.get("targetVolume")) == target for render in segment.get("renders", [])
        )
        zarray, zarray_sha, zarray_bytes = _bounded_get_json(
            parent["zarray_url"], maximum_bytes=int(parent["metadata_max_bytes"]), timeout=timeout,
        )
        volume_shape = [int(value) for value in zarray["shape"]]
        parent_provenance = {
            "catalog_url": parent["catalog_url"], "catalog_sha256": catalog_sha,
            "catalog_bytes": catalog_bytes, "catalog_updated": catalog.get("updated"),
            "segment_label": parent["segment_label"], "target_volume_id": target,
            "segment_to_volume_association_verified": association_verified,
            "zarr_url": parent["zarr_url"], "zarray_url": parent["zarray_url"],
            "zarray_sha256": zarray_sha, "zarray_bytes": zarray_bytes,
            "shape_zyx": volume_shape, "chunks_zyx": zarray.get("chunks"), "dtype": zarray.get("dtype"),
        }
    volume_bounds_verified = False
    out_of_bounds_vertices = None
    if volume_shape is not None:
        zyx_shape = np.asarray(volume_shape, dtype=np.float64)
        inside = (
            (arrays["z"] >= 0) & (arrays["z"] < zyx_shape[0]) &
            (arrays["y"] >= 0) & (arrays["y"] < zyx_shape[1]) &
            (arrays["x"] >= 0) & (arrays["x"] < zyx_shape[2])
        )
        out_of_bounds_vertices = int((valid & ~inside).sum())
        volume_bounds_verified = association_verified and out_of_bounds_vertices == 0

    grid_checks_pass = (
        geometry["nonfinite_vertices"] == 0
        and geometry["partial_sentinel_vertices"] == 0
        and geometry["largest_component_fraction"] >= 0.99
        and all(item["within_spacing_tolerance"] and item["abrupt_jumps"] == 0 for item in geometry["continuity"].values())
        and geometry["topology"]["degenerate_quads"] == 0
        and geometry["topology"]["adjacent_normal_flips"] == 0
        and mapping["integer_aligned"]
        and mapping.get("supervised_pixels_mapped_to_invalid_vertex_cell", 0) == 0
    )
    ct_support_provenance = None
    ct_support_verified = False
    if config.get("ct_support"):
        ct_support_path = root / config["ct_support"]
        ct_support_report = json.loads(ct_support_path.read_text(encoding="utf-8"))
        ct_support_verified = (
            ct_support_report.get("surface_id") == config["surface_id"]
            and ct_support_report.get("status") == "pass"
            and ct_support_report.get("validation_files_accessed") == 0
        )
        ct_support_provenance = {
            "report": config["ct_support"], "sha256": hashlib.sha256(ct_support_path.read_bytes()).hexdigest(),
            "status": ct_support_report.get("status"),
            "candidate_count": ct_support_report.get("candidate_count"),
            "passing_candidates": ct_support_report.get("passing_candidates"),
        }
    self_intersection_verified = bool(config.get("external_self_intersection_qa"))
    blockers = []
    if not volume_bounds_verified:
        blockers.append("parent volume shape/bounds not verified")
    if not ct_support_verified:
        blockers.append("CT-support not verified")
    if not grid_checks_pass:
        blockers.append("one or more local TIFXYZ grid checks failed")
    recommended_tier = "G2" if grid_checks_pass and not blockers else "G1"
    report = {
        "experiment_id": config["experiment_id"], "track": config["track"], "regime": config["regime"],
        "surface_id": config["surface_id"], "coordinate_order": config["coordinate_order"],
        "source_download_report": config["source_download_report"], "geometry": geometry,
        "raster_mapping": mapping, "volume_bounds": {
            "volume_shape_zyx": volume_shape, "verified": volume_bounds_verified,
            "out_of_bounds_vertices": out_of_bounds_vertices,
        },
        "parent_volume_provenance": parent_provenance,
        "ct_support_verified": ct_support_verified,
        "ct_support_provenance": ct_support_provenance,
        "external_self_intersection_qa_supplied": self_intersection_verified,
        "local_grid_checks_pass": grid_checks_pass, "recommended_geometry_tier": recommended_tier,
        "g2_blockers": blockers,
        "methodological_note": "G2 requires the verified local grid, parent-volume bounds, and CT support. External winding/self-intersection QA remains recommended and is required before G3.",
        "validation_files_accessed": 0,
    }
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
