"""Build and validate a provenance-first InkSurf candidate package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from inksurf.benchmark_baseline import _atomic_json
from inksurf.structural_features import _atomic_csv


REQUIRED_TOP_LEVEL = {
    "schema_version", "experiment_id", "track", "regime", "geometry_tier",
    "surface_id", "coordinate_frame", "ranking", "provenance", "candidates",
    "submission_readiness",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_package(package: dict[str, Any]) -> list[str]:
    errors = [f"missing top-level field: {name}" for name in sorted(REQUIRED_TOP_LEVEL - package.keys())]
    frame = package.get("coordinate_frame", {})
    if frame.get("axes") not in {"Y,X", "X,Y", "Z,Y,X", "X,Y,Z", "U,V"}:
        errors.append("coordinate_frame.axes must be explicit")
    candidates = package.get("candidates", [])
    ranks = [candidate.get("rank") for candidate in candidates]
    if ranks != list(range(1, len(candidates) + 1)):
        errors.append("candidate ranks must be consecutive from 1")
    for candidate in candidates:
        bounds = candidate.get("bounds_yx")
        if not isinstance(bounds, dict) or not all(name in bounds for name in ("y0", "y1", "x0", "x1")):
            errors.append(f"candidate {candidate.get('candidate_id')} has incomplete YX bounds")
        elif not (bounds["y0"] < bounds["y1"] and bounds["x0"] < bounds["x1"]):
            errors.append(f"candidate {candidate.get('candidate_id')} has invalid half-open bounds")
        if package.get("geometry_tier") in {"G1", "G2", "G3"}:
            if not candidate.get("bounds_uv"):
                errors.append(f"candidate {candidate.get('candidate_id')} lacks UV bounds for {package.get('geometry_tier')}")
            if not candidate.get("bounds_xyz"):
                errors.append(f"candidate {candidate.get('candidate_id')} lacks XYZ bounds for {package.get('geometry_tier')}")
    return errors


def _geometry_context(root: Path, config: dict[str, Any]) -> dict[str, Any] | None:
    specification = config.get("geometry")
    if not specification:
        return None
    import numpy as np
    import tifffile

    audit = json.loads((root / specification["audit_report"]).read_text(encoding="utf-8"))
    if audit["surface_id"] != config["surface_id"]:
        raise ValueError("geometry audit surface does not match candidate package")
    tiers = {"G0": 0, "G1": 1, "G2": 2, "G3": 3}
    if tiers[audit["recommended_geometry_tier"]] < tiers[config["geometry_tier"]]:
        raise ValueError("configured geometry tier exceeds audit recommendation")
    arrays = {
        name: tifffile.imread(root / relative, key=0)
        for name, relative in specification["coordinate_files"].items()
    }
    valid = (
        np.isfinite(arrays["x"]) & np.isfinite(arrays["y"]) & np.isfinite(arrays["z"])
        & ~((arrays["x"] == -1) | (arrays["y"] == -1) | (arrays["z"] == -1))
        & (arrays["z"] > 0)
    )
    return {
        "audit": audit, "arrays": arrays, "valid": valid,
        "ratio_yx": tuple(float(value) for value in audit["raster_mapping"]["reference_pixels_per_grid_step_yx"]),
    }


def _candidate_geometry(bounds: dict[str, int], context: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    ratio_y, ratio_x = context["ratio_yx"]
    grid_shape = context["valid"].shape
    gy0 = max(0, math.floor(bounds["y0"] / ratio_y))
    gy1 = min(grid_shape[0], math.ceil(bounds["y1"] / ratio_y))
    gx0 = max(0, math.floor(bounds["x0"] / ratio_x))
    gx1 = min(grid_shape[1], math.ceil(bounds["x1"] / ratio_x))
    local_valid = context["valid"][gy0:gy1, gx0:gx1]
    if not local_valid.any():
        raise ValueError(f"candidate bounds have no valid TIFXYZ vertices: {bounds}")
    xyz_min = []
    xyz_max = []
    for name in ("x", "y", "z"):
        values = context["arrays"][name][gy0:gy1, gx0:gx1][local_valid]
        xyz_min.append(float(np.min(values)))
        xyz_max.append(float(np.max(values)))
    return {
        "bounds_uv": {
            "u0": bounds["x0"], "u1": bounds["x1"], "v0": bounds["y0"], "v1": bounds["y1"],
            "units": "surface_raster_pixels", "convention": "half-open",
        },
        "tifxyz_grid_bounds_uv": {
            "u0": gx0, "u1": gx1, "v0": gy0, "v1": gy1, "convention": "half-open",
        },
        "bounds_xyz": {"min": xyz_min, "max": xyz_max, "coordinate_order": "X,Y,Z"},
        "valid_tifxyz_vertices": int(local_valid.sum()),
    }


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    with (root / config["candidate_table"]).open(encoding="utf-8", newline="") as stream:
        source_rows = list(csv.DictReader(stream))
    field = config["eligibility_field"]
    eligible = [row for row in source_rows if str(row[field]).strip().lower() in {"1", "true", "yes"}]
    ranking_score = config["ranking_score"]
    eligible.sort(key=lambda row: float(row[ranking_score]), reverse=True)
    selected = eligible[: int(config["candidate_limit"])]
    geometry_context = _geometry_context(root, config)
    artifact_by_candidate = None
    if config.get("candidate_artifact_manifest"):
        artifact_manifest = json.loads((root / config["candidate_artifact_manifest"]).read_text(encoding="utf-8"))
        if artifact_manifest["surface_id"] != config["surface_id"]:
            raise ValueError("candidate artifact manifest surface mismatch")
        artifact_by_candidate = {item["candidate_id"]: item for item in artifact_manifest["candidates"]}
    candidates = []
    csv_rows = []
    for rank, row in enumerate(selected, 1):
        bounds = {name: int(row[name]) for name in ("y0", "y1", "x0", "x1")}
        geometry_fields = _candidate_geometry(bounds, geometry_context) if geometry_context else {}
        candidate_id = f"{config['experiment_id']}-r{rank:03d}"
        artifact = artifact_by_candidate.get(candidate_id) if artifact_by_candidate is not None else None
        if artifact_by_candidate is not None and artifact is None:
            raise ValueError(f"candidate artifact missing for {candidate_id}")
        if artifact:
            artifact_path = root / artifact["artifact_path"]
            if not artifact_path.is_file() or _sha256(artifact_path) != artifact["sha256"]:
                raise ValueError(f"candidate artifact failed SHA256 verification: {candidate_id}")
        candidate = {
            "candidate_id": candidate_id,
            "rank": rank,
            "source_region_id": row["region_id"],
            "bounds_yx": bounds,
            "baseline_score": {"name": ranking_score, "value": float(row[ranking_score])},
            "inksurf_score": (
                {"name": config["inksurf_score"], "value": float(row[config["inksurf_score"]])}
                if config.get("inksurf_score") else None
            ),
            **geometry_fields,
            "artifacts": ({
                "local_npz": artifact["artifact_path"], "sha256": artifact["sha256"],
                "bytes": artifact["bytes"], "arrays": artifact["arrays"],
            } if artifact else None),
            "stability": artifact["metrics"] if artifact else None,
            "artifact_status": {
                "continuous_score_map": "available_local_ignored",
                "component_mask": "available_local_ignored" if artifact else "missing",
                "skeleton": "available_local_ignored" if artifact else "missing",
                "uv_xyz_mapping": f"available_{config['geometry_tier']}" if geometry_context else "missing_G0",
                "human_review": "not_performed",
            },
        }
        candidates.append(candidate)
        csv_rows.append({
            "candidate_id": candidate["candidate_id"], "rank": rank,
            "source_region_id": row["region_id"], **candidate["bounds_yx"],
            "score_name": ranking_score, "score_value": float(row[ranking_score]),
            "geometry_tier": config["geometry_tier"], "regime": config["regime"],
        })
    provenance = []
    for relative in config["provenance_files"]:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"provenance file missing: {relative}")
        provenance.append({"path": relative, "bytes": path.stat().st_size, "sha256": _sha256(path)})
    available = {}
    for name, relative in config["available_artifacts"].items():
        path = root / relative
        available[name] = {"path": relative, "exists": path.is_file()}
    package = {
        "schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
        "track": config["track"], "regime": config["regime"], "geometry_tier": config["geometry_tier"],
        "surface_id": config["surface_id"], "coordinate_frame": config["coordinate_frame"],
        "ranking": {
            "score": ranking_score, "direction": "higher_is_better", "eligible_candidates": len(eligible),
            "exported_candidates": len(candidates), "label_used_for_ranking": False,
        },
        "provenance": provenance, "available_artifacts": available,
        "geometry_audit": ({
            "report": config["geometry"]["audit_report"],
            "local_grid_checks_pass": geometry_context["audit"]["local_grid_checks_pass"],
            "g2_blockers": geometry_context["audit"]["g2_blockers"],
        } if geometry_context else None),
        "candidates": candidates,
        "submission_readiness": {
            "status": "exploratory_only",
            "missing": config["missing_submission_artifacts"],
            "claim": config.get(
                "submission_claim",
                f"Ranked {config['regime']} regions from {ranking_score}; not verified physical ink and not submission-ready.",
            ),
        },
    }
    errors = validate_package(package)
    report = {
        "experiment_id": config["experiment_id"], "status": "valid" if not errors else "invalid",
        "schema_version": config["schema_version"], "candidate_count": len(candidates),
        "provenance_files_verified": len(provenance), "validation_errors": errors,
        "candidate_artifacts_verified": sum(candidate.get("artifacts") is not None for candidate in candidates),
        "stable_candidates": sum(bool((candidate.get("stability") or {}).get("passes_stability")) for candidate in candidates),
        "submission_readiness": "exploratory_only", "validation_files_accessed": 0,
    }
    _atomic_json(root / config["outputs"]["package_json"], package)
    _atomic_csv(root / config["outputs"]["candidates_csv"], csv_rows)
    _atomic_json(root / config["outputs"]["validation_report_json"], report)
    if errors:
        raise RuntimeError("candidate package validation failed: " + "; ".join(errors))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
