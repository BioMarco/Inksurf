"""Audit normalized-UV correspondence between two TIFXYZ coordinate frames."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .evidence_consistency import _atomic_json


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def paired_uv_samples(
    source_xyz: np.ndarray, target_xyz: np.ndarray, stride: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if source_xyz.ndim != 3 or target_xyz.ndim != 3 or source_xyz.shape[2] != 3 or target_xyz.shape[2] != 3:
        raise ValueError("TIFXYZ arrays must have shape Y,X,3")
    if min(source_xyz.shape[:2]) < 2 or min(target_xyz.shape[:2]) < 2 or stride <= 0:
        raise ValueError("TIFXYZ grids need at least two rows/columns and positive stride")
    rows = np.arange(0, source_xyz.shape[0], stride, dtype=np.int64)
    columns = np.arange(0, source_xyz.shape[1], stride, dtype=np.int64)
    yy, xx = np.meshgrid(rows, columns, indexing="ij")
    ty = np.rint(yy * (target_xyz.shape[0] - 1) / (source_xyz.shape[0] - 1)).astype(np.int64)
    tx = np.rint(xx * (target_xyz.shape[1] - 1) / (source_xyz.shape[1] - 1)).astype(np.int64)
    source = source_xyz[yy, xx]
    target = target_xyz[ty, tx]
    valid = (
        np.isfinite(source).all(axis=-1) & np.isfinite(target).all(axis=-1)
        & ~np.all(source == -1, axis=-1) & ~np.all(target == -1, axis=-1)
        & (source[..., 2] > 0) & (target[..., 2] > 0)
    )
    return source[valid], target[valid], yy[valid], xx[valid]


def fit_affine(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    design = np.column_stack((source, np.ones(source.shape[0])))
    transform, _, rank, _ = np.linalg.lstsq(design, target, rcond=None)
    if rank < 4:
        raise ValueError("affine registration design is rank deficient")
    return transform


def apply_affine(points: np.ndarray, transform: np.ndarray) -> np.ndarray:
    return np.column_stack((points, np.ones(points.shape[0]))) @ transform


def run(config_path: Path) -> dict:
    import tifffile

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-cross-tifxyz-registration/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("cross-TIFXYZ registration audit is Track A DEV only")
    root = config_path.resolve().parent.parent
    download_path = root / config["download_report"]
    if _sha256(download_path) != config["download_report_sha256"]:
        raise ValueError("TIFXYZ download report hash mismatch")
    download = json.loads(download_path.read_text(encoding="utf-8"))
    verified = {
        ((root / row["destination"]).resolve() if not Path(row["destination"]).is_absolute() else Path(row["destination"]).resolve()): row["sha256"]
        for row in download["files"]
    }
    arrays = []
    for specification in config["coordinate_sets"]:
        channels = []
        for axis in ("x", "y", "z"):
            path = root / specification[axis]
            if verified.get(path.resolve()) != _sha256(path):
                raise ValueError("coordinate file is not bound to the download receipt")
            channels.append(tifffile.imread(path, key=0))
        xyz = np.stack(channels, axis=-1).astype(np.float64)
        xyz *= float(specification["voxel_um"])
        arrays.append(xyz)
    source, target, rows, columns = paired_uv_samples(arrays[0], arrays[1], int(config["sample_stride_vertices"]))
    block = int(config["spatial_block_vertices"])
    fold = (rows // block + columns // block) % int(config["spatial_fold_count"])
    holdout = fold == int(config["holdout_fold"])
    if holdout.sum() < int(config["minimum_holdout_points"]) or (~holdout).sum() < int(config["minimum_holdout_points"]):
        raise ValueError("insufficient spatial train/holdout correspondences")
    transform = fit_affine(source[~holdout], target[~holdout])
    residual = np.linalg.norm(apply_affine(source[holdout], transform) - target[holdout], axis=1)
    quantiles = dict(zip(
        ("min", "p50", "p90", "p95", "p99", "max"),
        map(float, np.quantile(residual, [0, 0.5, 0.9, 0.95, 0.99, 1])), strict=True,
    ))
    passes = (
        quantiles["p50"] <= float(config["maximum_median_residual_um"])
        and quantiles["p90"] <= float(config["maximum_p90_residual_um"])
    )
    report = {
        "schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
        "track": "A", "regime": "DEV", "geometry_tier": "G1",
        "download_report": config["download_report"],
        "download_report_sha256": config["download_report_sha256"],
        "coordinate_sets": [
            {"volume_id": item["volume_id"], "voxel_um": float(item["voxel_um"])}
            for item in config["coordinate_sets"]
        ],
        "status": "GO_UV_CORRESPONDENCE" if passes else "NO_GO_UV_CORRESPONDENCE",
        "coordinate_order": "X,Y,Z", "source_grid_shape_yx": list(arrays[0].shape[:2]),
        "target_grid_shape_yx": list(arrays[1].shape[:2]), "valid_correspondence_count": int(source.shape[0]),
        "train_count": int((~holdout).sum()), "holdout_count": int(holdout.sum()),
        "sample_stride_vertices": int(config["sample_stride_vertices"]),
        "spatial_split": {
            "block_vertices": block, "fold_count": int(config["spatial_fold_count"]),
            "holdout_fold": int(config["holdout_fold"]),
        },
        "affine_source_um_to_target_um": transform.tolist(),
        "holdout_residual_um": quantiles,
        "gates": {
            "maximum_median_residual_um": float(config["maximum_median_residual_um"]),
            "maximum_p90_residual_um": float(config["maximum_p90_residual_um"]),
            "passes": passes,
        },
        "threshold_note": config.get("threshold_note"),
        "limitation": "This tests shared normalized UV plus a global affine between scan frames; it does not prove local non-rigid registration or ink validity.",
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
