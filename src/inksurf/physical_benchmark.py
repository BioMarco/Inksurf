"""Evaluate bounded prediction policies in physical surface units."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .evidence_consistency import _atomic_json
from .physical_metrics import false_positive_burden


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evaluate_policy(
    accepted_chunks: list[np.ndarray],
    label_chunks: list[np.ndarray],
    valid_chunks: list[np.ndarray],
    area_chunks: list[np.ndarray],
    *,
    minimum_component_area_mm2: float,
) -> dict:
    totals = {
        "evaluated_pixels": 0, "positive_pixels": 0, "accepted_pixels": 0,
        "true_positive_pixels": 0, "evaluated_negative_area_cm2": 0.0,
        "false_positive_area_cm2": 0.0, "false_positive_components_chunk_clipped": 0,
    }
    for accepted, labels, valid, area in zip(
        accepted_chunks, label_chunks, valid_chunks, area_chunks, strict=True
    ):
        accepted = np.asarray(accepted, dtype=bool)
        labels = np.asarray(labels, dtype=bool)
        valid = np.asarray(valid, dtype=bool)
        fp = false_positive_burden(
            accepted, labels, valid, area,
            minimum_component_area_mm2=minimum_component_area_mm2,
        )
        totals["evaluated_pixels"] += int(valid.sum())
        totals["positive_pixels"] += int((labels & valid).sum())
        totals["accepted_pixels"] += int((accepted & valid).sum())
        totals["true_positive_pixels"] += int((accepted & labels & valid).sum())
        totals["evaluated_negative_area_cm2"] += float(fp["evaluated_negative_area_cm2"])
        totals["false_positive_area_cm2"] += float(fp["false_positive_area_cm2"])
        totals["false_positive_components_chunk_clipped"] += int(fp["false_positive_components_retained"])
    accepted = totals["accepted_pixels"]
    positive = totals["positive_pixels"]
    negative_area = totals["evaluated_negative_area_cm2"]
    totals.update({
        "accepted_fraction": accepted / totals["evaluated_pixels"],
        "pixel_precision": totals["true_positive_pixels"] / accepted if accepted else None,
        "pixel_recall": totals["true_positive_pixels"] / positive if positive else None,
        "false_positive_area_fraction": totals["false_positive_area_cm2"] / negative_area,
        "false_positive_components_per_cm2_chunk_clipped": (
            totals["false_positive_components_chunk_clipped"] / negative_area
        ),
        "minimum_component_area_mm2": minimum_component_area_mm2,
    })
    return totals


def run(config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-physical-benchmark/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV" or config.get("geometry_tier") != "G2":
        raise ValueError("this bounded benchmark requires Track A / DEV / G2")
    root = config_path.resolve().parent.parent
    geometry_path = root / config["roi_geometry_report"]
    if _sha256(geometry_path) != config["roi_geometry_sha256"]:
        raise ValueError("ROI geometry report hash mismatch")
    geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
    if geometry.get("status") != "pass" or geometry.get("recommended_geometry_tier") != "G2":
        raise ValueError("ROI geometry did not pass G2")
    prediction_path = root / config["predictions"]
    if _sha256(prediction_path) != config["predictions_sha256"]:
        raise ValueError("prediction hash mismatch")
    with np.load(prediction_path) as archive:
        scores = np.asarray(archive["predictions"], dtype=np.float32).mean(axis=0)
        prediction_chunks = [tuple(map(int, row)) for row in archive["chunk_yx"]]
    geometry_by_chunk = {tuple(item["chunk_yx"]): item for item in geometry["chunks"]}
    labels, valid, areas = [], [], []
    for chunk in prediction_chunks:
        derived_path = root / config["derived_pattern"].format(y=chunk[0], x=chunk[1])
        with np.load(derived_path) as archive:
            labels.append(np.asarray(archive["inklabels"], dtype=bool))
            valid.append(np.asarray(archive["validation_mask"], dtype=bool))
        area_item = geometry_by_chunk[chunk]
        area_path = root / area_item["pixel_area_map"]
        if _sha256(area_path) != area_item["pixel_area_sha256"]:
            raise ValueError(f"pixel-area hash mismatch for {chunk}")
        areas.append(np.load(area_path, mmap_mode="r"))
    valid_scores = np.concatenate([score[mask] for score, mask in zip(scores, valid, strict=True)])
    policies: dict[str, list[np.ndarray]] = {
        "inksurf_fail_closed_one_effective_group": [np.zeros_like(mask) for mask in valid],
        "naive_score_gte_0_5": [score >= 0.5 for score in scores],
    }
    for fraction in config["top_fractions"]:
        count = max(1, int(math.ceil(valid_scores.size * float(fraction))))
        cutoff = float(np.partition(valid_scores, valid_scores.size - count)[valid_scores.size - count])
        policies[f"naive_top_{float(fraction):g}"] = [score >= cutoff for score in scores]
    minimum_area = float(config["minimum_component_area_mm2"])
    results = {
        name: evaluate_policy(masks, labels, valid, areas, minimum_component_area_mm2=minimum_area)
        for name, masks in policies.items()
    }
    report = {
        "schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
        "track": "A", "regime": "DEV", "geometry_tier": "G2",
        "status": "bounded_physical_diagnostic_complete", "policies": results,
        "component_metric_limitation": "Components are clipped at the 12 chunk boundaries and are not a continuous-ROI estimate.",
        "interpretation": "Naive policies quantify review burden; InkSurf abstains because only one effective evidence group exists. Zero false positives with zero yield is not detector superiority.",
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
