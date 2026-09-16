"""Measure labeled common support from TIFXYZ validity, independent of model scores."""

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


def sample_grid_support(
    valid: np.ndarray, global_y: np.ndarray, global_x: np.ndarray,
    canvas_shape_yx: tuple[int, int], policy: str,
) -> np.ndarray:
    if valid.ndim != 2:
        raise ValueError("validity grid must be 2D")
    height, width = canvas_shape_yx
    gy = (global_y + 0.5) * valid.shape[0] / height - 0.5
    gx = (global_x + 0.5) * valid.shape[1] / width - 0.5
    if policy == "nearest":
        iy = np.clip(np.rint(gy).astype(int), 0, valid.shape[0] - 1)
        ix = np.clip(np.rint(gx).astype(int), 0, valid.shape[1] - 1)
        return valid[iy, ix]
    if policy not in {"all", "any"}:
        raise ValueError("policy must be all, nearest or any")
    y0 = np.clip(np.floor(gy).astype(int), 0, valid.shape[0] - 1)
    y1 = np.clip(np.ceil(gy).astype(int), 0, valid.shape[0] - 1)
    x0 = np.clip(np.floor(gx).astype(int), 0, valid.shape[1] - 1)
    x1 = np.clip(np.ceil(gx).astype(int), 0, valid.shape[1] - 1)
    values = np.stack((valid[y0, x0], valid[y0, x1], valid[y1, x0], valid[y1, x1]))
    return values.all(axis=0) if policy == "all" else values.any(axis=0)


def run(config_path: Path) -> dict:
    import tifffile

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-tifxyz-common-support/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("TIFXYZ common-support audit is Track A DEV only")
    root = config_path.resolve().parent.parent
    chunk_path = root / config["chunk_audit_report"]
    download_path = root / config["tifxyz_download_report"]
    if _sha256(chunk_path) != config["chunk_audit_sha256"]:
        raise ValueError("chunk audit hash mismatch")
    if _sha256(download_path) != config["tifxyz_download_sha256"]:
        raise ValueError("TIFXYZ download hash mismatch")
    download = json.loads(download_path.read_text(encoding="utf-8"))
    verified = {
        ((root / row["destination"]).resolve() if not Path(row["destination"]).is_absolute() else Path(row["destination"]).resolve()): row["sha256"]
        for row in download["files"]
    }
    validity = []
    for specification in config["coordinate_sets"]:
        channels = []
        for axis in ("x", "y", "z"):
            path = root / specification[axis]
            if verified.get(path.resolve()) != _sha256(path):
                raise ValueError("coordinate file is not bound to download receipt")
            channels.append(tifffile.imread(path, key=0))
        xyz = np.stack(channels, axis=-1)
        validity.append(np.isfinite(xyz).all(-1) & ~np.all(xyz == -1, axis=-1) & (xyz[..., 2] > 0))
    chunks = json.loads(chunk_path.read_text(encoding="utf-8"))["chunks"]
    canvas_shape = tuple(map(int, config["annotation_canvas_shape_yx"]))
    chunk_pixels = int(config["chunk_pixels"])
    policies = ("all", "nearest", "any")
    totals = {policy: {"eligible_pixels": 0, "eligible_ink_pixels": 0, "eligible_negative_pixels": 0} for policy in policies}
    rows = []
    for item in chunks:
        archive = np.load(root / item["derived"])
        evaluation = np.asarray(archive["validation_mask"], dtype=bool)
        ink = np.asarray(archive["inklabels"], dtype=bool)
        y, x = map(int, item["chunk_yx"])
        gy = y * chunk_pixels + np.arange(evaluation.shape[0])[:, None]
        gx = x * chunk_pixels + np.arange(evaluation.shape[1])[None, :]
        metrics = {}
        for policy in policies:
            common = np.logical_and.reduce([
                sample_grid_support(grid, gy, gx, canvas_shape, policy) for grid in validity
            ])
            eligible = evaluation & common
            values = {
                "eligible_pixels": int(eligible.sum()),
                "eligible_ink_pixels": int((eligible & ink).sum()),
                "eligible_negative_pixels": int((eligible & ~ink).sum()),
            }
            metrics[policy] = values
            for key, value in values.items():
                totals[policy][key] += value
        rows.append({"chunk_yx": item["chunk_yx"], "metrics": metrics})
    permissive = totals["any"]
    status = (
        "NO_GO_NO_COMMON_GEOMETRY_SUPPORT" if permissive["eligible_pixels"] == 0
        else "NO_GO_SINGLE_CLASS_COMMON_SUPPORT"
        if permissive["eligible_ink_pixels"] == 0 or permissive["eligible_negative_pixels"] == 0
        else "GO_LABELED_COMMON_SUPPORT"
    )
    report = {
        "schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
        "track": "A", "regime": "DEV", "geometry_tier": "G1", "status": status,
        "annotation_canvas_shape_yx": list(canvas_shape), "roi_count": len(rows),
        "tifxyz_valid_fraction": [float(grid.mean()) for grid in validity],
        "totals": totals, "chunks": rows,
        "claim_limit": "Geometry-valid labeled support only; this does not validate registration residuals, model scores, label independence or ink.",
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
