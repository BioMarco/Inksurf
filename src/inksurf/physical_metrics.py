"""Measure false-positive burden in physical surface area."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from .evidence_consistency import _atomic_json, _load_array


def _component_areas_um2(mask: np.ndarray, pixel_area_um2: np.ndarray) -> list[float]:
    height, width = mask.shape
    visited = np.zeros(mask.shape, dtype=bool)
    areas: list[float] = []
    for row, column in np.argwhere(mask):
        row, column = int(row), int(column)
        if visited[row, column]:
            continue
        visited[row, column] = True
        stack = [(row, column)]
        area = 0.0
        while stack:
            current_row, current_column = stack.pop()
            area += float(pixel_area_um2[current_row, current_column])
            for next_row, next_column in (
                (current_row - 1, current_column),
                (current_row + 1, current_column),
                (current_row, current_column - 1),
                (current_row, current_column + 1),
            ):
                if (
                    0 <= next_row < height
                    and 0 <= next_column < width
                    and mask[next_row, next_column]
                    and not visited[next_row, next_column]
                ):
                    visited[next_row, next_column] = True
                    stack.append((next_row, next_column))
        areas.append(area)
    return areas


def false_positive_burden(
    accepted: np.ndarray,
    reference_positive: np.ndarray,
    valid_mask: np.ndarray,
    pixel_area_um2: np.ndarray | float,
    *,
    minimum_component_area_mm2: float,
) -> dict[str, float | int]:
    """Compute false-positive area and 4-connected regions per negative cm²."""
    accepted = np.asarray(accepted, dtype=bool)
    reference_positive = np.asarray(reference_positive, dtype=bool)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if accepted.ndim != 2 or accepted.shape != reference_positive.shape or accepted.shape != valid_mask.shape:
        raise ValueError("accepted, reference_positive and valid_mask must be matching 2D arrays")
    areas = np.asarray(pixel_area_um2, dtype=np.float64)
    if areas.ndim == 0:
        areas = np.full(accepted.shape, float(areas), dtype=np.float64)
    if areas.shape != accepted.shape:
        raise ValueError("pixel_area_um2 must be scalar or match the masks")
    if minimum_component_area_mm2 < 0:
        raise ValueError("minimum_component_area_mm2 must be non-negative")
    if np.any(~np.isfinite(areas[valid_mask])) or np.any(areas[valid_mask] <= 0):
        raise ValueError("valid pixels require finite positive physical area")

    negative = valid_mask & ~reference_positive
    negative_area_um2 = float(areas[negative].sum())
    if negative_area_um2 <= 0:
        raise ValueError("evaluation mask contains no negative reference area")
    false_positive = accepted & negative
    false_area_um2 = float(areas[false_positive].sum())
    component_areas = _component_areas_um2(false_positive, areas)
    threshold_um2 = float(minimum_component_area_mm2) * 1_000_000.0
    retained = [area for area in component_areas if area >= threshold_um2]
    negative_area_cm2 = negative_area_um2 / 100_000_000.0
    return {
        "evaluated_negative_pixels": int(negative.sum()),
        "evaluated_negative_area_cm2": negative_area_cm2,
        "false_positive_pixels": int(false_positive.sum()),
        "false_positive_area_cm2": false_area_um2 / 100_000_000.0,
        "false_positive_area_fraction": false_area_um2 / negative_area_um2,
        "false_positive_components_all": len(component_areas),
        "false_positive_components_retained": len(retained),
        "false_positive_components_per_cm2": len(retained) / negative_area_cm2,
        "minimum_component_area_mm2": float(minimum_component_area_mm2),
    }


def _load_mask(root: Path, specification: dict[str, Any]) -> np.ndarray:
    return np.asarray(_load_array(root, specification), dtype=bool)


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-physical-fp-audit/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") not in {"A", "B", "C"}:
        raise ValueError("track must be explicit")
    if config.get("regime") not in {"DEV", "VALIDATION", "DISCOVERY"}:
        raise ValueError("regime must be explicit")
    if config.get("geometry_tier") not in {"G2", "G3"}:
        raise ValueError("physical false-positive metrics require G2 or G3 geometry")
    root = config_path.resolve().parent.parent
    inputs = config["inputs"]
    accepted = _load_mask(root, inputs["accepted"])
    reference = _load_mask(root, inputs["reference_positive"])
    valid = _load_mask(root, inputs["valid_mask"])
    area_spec = inputs["pixel_area_um2"]
    if "constant" in area_spec:
        pixel_area: np.ndarray | float = float(area_spec["constant"])
        area_source = "constant_um2"
    else:
        pixel_area = np.asarray(_load_array(root, area_spec), dtype=np.float64)
        area_source = "per_pixel_map_um2"
    metrics = false_positive_burden(
        accepted,
        reference,
        valid,
        pixel_area,
        minimum_component_area_mm2=float(config["thresholds"]["minimum_component_area_mm2"]),
    )
    report = {
        "schema_version": config["schema_version"],
        "experiment_id": config["experiment_id"],
        "track": config["track"],
        "regime": config["regime"],
        "geometry_tier": config["geometry_tier"],
        "status": "physical_false_positive_metrics_complete",
        "area_source": area_source,
        "connectivity": 4,
        "metrics": metrics,
        "claim": "These metrics quantify burden against the supplied reference; they do not verify physical ink or reference independence.",
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
