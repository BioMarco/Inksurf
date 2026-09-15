"""Combine aligned evidence without counting correlated variants as independent."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import warnings
from pathlib import Path
from typing import Any

import numpy as np


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "inksurf-evidence-consistency/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("regime") not in {"DEV", "VALIDATION", "DISCOVERY"}:
        raise ValueError("regime must be explicit")
    views = config.get("views", [])
    if len(views) < 2:
        raise ValueError("at least two views are required")
    ids = [view.get("view_id") for view in views]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("view_id values must be non-empty and unique")
    if any(not view.get("independence_group") for view in views):
        raise ValueError("every view requires an independence_group")
    thresholds = config.get("thresholds", {})
    for name in ("evidence", "minimum_support_fraction", "maximum_disagreement"):
        value = float(thresholds.get(name, -1))
        if not 0 <= value <= 1:
            raise ValueError(f"{name} must be in [0, 1]")
    group_count = len({view["independence_group"] for view in views})
    minimum = int(thresholds.get("minimum_independent_groups", 0))
    if minimum < 2 or minimum > group_count:
        raise ValueError("minimum_independent_groups must be between 2 and available groups")


def _normalize(array: np.ndarray, value_range: list[float] | tuple[float, float]) -> np.ndarray:
    if len(value_range) != 2:
        raise ValueError("value_range must contain [minimum, maximum]")
    low, high = map(float, value_range)
    if not np.isfinite([low, high]).all() or high <= low:
        raise ValueError("value_range must be finite and increasing")
    result = (np.asarray(array, dtype=np.float32) - low) / (high - low)
    return np.clip(result, 0.0, 1.0)


def combine_evidence(
    views: list[np.ndarray],
    independence_groups: list[str],
    *,
    evidence_threshold: float,
    minimum_independent_groups: int,
    minimum_support_fraction: float,
    maximum_disagreement: float,
    valid_masks: list[np.ndarray] | None = None,
) -> dict[str, np.ndarray]:
    """Return consensus, disagreement and an abstaining acceptance mask.

    Views in the same ``independence_group`` are collapsed by a median before
    cross-group consensus. Correlated perturbations therefore cannot inflate
    the number of independent confirmations.
    """
    if len(views) != len(independence_groups) or len(views) < 2:
        raise ValueError("views and independence_groups must have equal length >= 2")
    shape = np.asarray(views[0]).shape
    if not shape or any(np.asarray(view).shape != shape for view in views):
        raise ValueError("all aligned views must have the same non-scalar shape")
    if valid_masks is None:
        valid_masks = [np.isfinite(view) for view in views]
    if len(valid_masks) != len(views) or any(np.asarray(mask).shape != shape for mask in valid_masks):
        raise ValueError("valid masks must match views")

    groups: dict[str, list[np.ndarray]] = {}
    for view, mask, group in zip(views, valid_masks, independence_groups):
        values = np.asarray(view, dtype=np.float32)
        valid = np.asarray(mask, dtype=bool) & np.isfinite(values)
        groups.setdefault(group, []).append(np.where(valid, values, np.nan))
    if minimum_independent_groups < 2 or minimum_independent_groups > len(groups):
        raise ValueError("invalid minimum_independent_groups")

    group_maps = []
    for group_views in groups.values():
        stack = np.stack(group_views, axis=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            group_maps.append(np.nanmedian(stack, axis=0))
    grouped = np.stack(group_maps, axis=0)
    valid_group_count = np.sum(np.isfinite(grouped), axis=0).astype(np.uint16)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        consensus = np.nanmedian(grouped, axis=0).astype(np.float32)
        minimum = np.nanmin(grouped, axis=0)
        maximum = np.nanmax(grouped, axis=0)
    disagreement = (maximum - minimum).astype(np.float32)
    supported = np.sum((grouped >= evidence_threshold) & np.isfinite(grouped), axis=0)
    support_fraction = np.divide(
        supported,
        valid_group_count,
        out=np.zeros(shape, dtype=np.float32),
        where=valid_group_count > 0,
    )
    enough = valid_group_count >= minimum_independent_groups
    accepted = (
        enough
        & (consensus >= evidence_threshold)
        & (support_fraction >= minimum_support_fraction)
        & (disagreement <= maximum_disagreement)
    )
    consensus = np.where(valid_group_count > 0, consensus, np.nan).astype(np.float32)
    disagreement = np.where(valid_group_count > 0, disagreement, np.nan).astype(np.float32)
    return {
        "consensus": consensus,
        "support_fraction": support_fraction.astype(np.float32),
        "disagreement": disagreement,
        "valid_independent_groups": valid_group_count,
        "accepted": accepted.astype(bool),
    }


def _load_array(root: Path, specification: dict[str, Any]) -> np.ndarray:
    path = root / specification["path"]
    suffix = path.suffix.lower()
    if suffix == ".npy":
        return np.load(path, mmap_mode="r")
    if suffix == ".npz":
        archive = np.load(path)
        key = specification.get("array_key")
        if not key:
            raise ValueError(f"array_key required for {path}")
        return archive[key]
    if suffix in {".tif", ".tiff"}:
        try:
            import tifffile
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("TIFF input requires pip install '.[benchmark]'") from exc
        return tifffile.memmap(path)
    if suffix == ".zarr" or path.is_dir():
        try:
            import zarr
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("Zarr input requires pip install '.[benchmark]'") from exc
        array = zarr.open(str(path), mode="r")
        key = specification.get("array_key")
        return np.asarray(array[key] if key else array)
    raise ValueError(f"unsupported evidence format: {path}")


def _atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
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


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    root = config_path.resolve().parent.parent
    views = []
    groups = []
    for specification in config["views"]:
        raw = _load_array(root, specification)
        views.append(_normalize(raw, specification["value_range"]))
        groups.append(specification["independence_group"])
    thresholds = config["thresholds"]
    maps = combine_evidence(
        views,
        groups,
        evidence_threshold=float(thresholds["evidence"]),
        minimum_independent_groups=int(thresholds["minimum_independent_groups"]),
        minimum_support_fraction=float(thresholds["minimum_support_fraction"]),
        maximum_disagreement=float(thresholds["maximum_disagreement"]),
    )
    output_path = root / config["outputs"]["maps_npz"]
    _atomic_npz(output_path, maps)
    total = int(maps["accepted"].size)
    report = {
        "schema_version": config["schema_version"],
        "experiment_id": config["experiment_id"],
        "track": config["track"],
        "regime": config["regime"],
        "geometry_tier": config["geometry_tier"],
        "status": "evidence_maps_created_not_validated",
        "shape": list(maps["accepted"].shape),
        "view_count": len(views),
        "independent_group_count": len(set(groups)),
        "accepted_pixels": int(maps["accepted"].sum()),
        "accepted_fraction": float(maps["accepted"].sum() / total),
        "thresholds": thresholds,
        "claim": "Acceptance indicates cross-group consistency under frozen rules, not verified physical ink.",
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
