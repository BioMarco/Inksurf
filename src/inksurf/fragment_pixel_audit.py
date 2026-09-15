"""Block-matched DEV audit of CT features at ink and control pixels."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from inksurf.benchmark_baseline import _atomic_json
from inksurf.structural_features import _atomic_csv


def paired_block_interval(differences: np.ndarray, samples: int, seed: int) -> dict[str, float]:
    if differences.ndim != 1 or differences.size < 2:
        raise ValueError("at least two block differences are required")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, differences.size, size=(samples, differences.size))
    means = differences[indices].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return {"low": float(low), "high": float(high), "replicates": samples}


def run(config_path: Path) -> dict[str, Any]:
    try:
        from PIL import Image
        from scipy.ndimage import binary_dilation
        from sklearn.metrics import roc_auc_score
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("install fragment and structure dependencies") from exc
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("regime") != "DEV":
        raise ValueError("pixel audit is restricted to DEV")
    root = config_path.resolve().parent.parent
    with Image.open(root / config["inklabels"]) as image:
        ink = np.asarray(image) > 0
    with Image.open(root / config["mask"]) as image:
        valid = np.asarray(image) > 0
    excluded = binary_dilation(ink, iterations=int(config["control_exclusion_radius"]))
    control = valid & ~excluded
    maps = {name: np.load(root / relative, mmap_mode="r") for name, relative in config["feature_maps"].items()}
    if any(values.shape != ink.shape for values in maps.values()):
        raise ValueError("feature map shape mismatch")
    rng = np.random.default_rng(int(config["seed"]))
    block_size = int(config["block_size"])
    maximum = int(config["max_pairs_per_block"])
    rows: list[dict[str, Any]] = []
    block_summaries: dict[str, dict[str, list[float]]] = {name: {"ink": [], "control": []} for name in maps}
    pair_id = 0
    for y0 in range(0, ink.shape[0], block_size):
        y1 = min(ink.shape[0], y0 + block_size)
        for x0 in range(0, ink.shape[1], block_size):
            x1 = min(ink.shape[1], x0 + block_size)
            iy, ix = np.nonzero(ink[y0:y1, x0:x1] & valid[y0:y1, x0:x1])
            cy, cx = np.nonzero(control[y0:y1, x0:x1])
            count = min(maximum, iy.size, cy.size)
            if count == 0:
                continue
            ink_choice = rng.choice(iy.size, size=count, replace=False)
            control_choice = rng.choice(cy.size, size=count, replace=False)
            ink_y, ink_x = iy[ink_choice] + y0, ix[ink_choice] + x0
            control_y, control_x = cy[control_choice] + y0, cx[control_choice] + x0
            block_id = f"by{y0 // block_size:02d}_bx{x0 // block_size:02d}"
            for name, values in maps.items():
                block_summaries[name]["ink"].append(float(np.mean(values[ink_y, ink_x])))
                block_summaries[name]["control"].append(float(np.mean(values[control_y, control_x])))
            for label, ys, xs in ((1, ink_y, ink_x), (0, control_y, control_x)):
                for y, x in zip(ys, xs, strict=True):
                    row = {"sample_id": pair_id, "block_id": block_id, "label": label, "y": int(y), "x": int(x)}
                    row.update({name: float(values[y, x]) for name, values in maps.items()})
                    rows.append(row)
                    pair_id += 1
    labels = np.asarray([row["label"] for row in rows])
    feature_results = []
    for name in maps:
        scores = np.asarray([row[name] for row in rows])
        auc = float(roc_auc_score(labels, scores))
        ink_means = np.asarray(block_summaries[name]["ink"])
        control_means = np.asarray(block_summaries[name]["control"])
        differences = ink_means - control_means
        pooled = float(np.sqrt((np.var(scores[labels == 1]) + np.var(scores[labels == 0])) / 2))
        feature_results.append({
            "feature": name, "auc_high": auc, "auc_absolute": max(auc, 1.0 - auc),
            "direction": "high" if auc >= 0.5 else "low",
            "ink_median": float(np.median(scores[labels == 1])),
            "control_median": float(np.median(scores[labels == 0])),
            "standardized_mean_difference": float((scores[labels == 1].mean() - scores[labels == 0].mean()) / pooled) if pooled else 0.0,
            "block_mean_difference": float(differences.mean()),
            "block_mean_difference_bootstrap_95ci": paired_block_interval(
                differences, int(config["bootstrap_samples"]), int(config["seed"])
            ),
        })
    report = {
        "experiment_id": config["experiment_id"], "regime": "DEV",
        "status": "matched_pixel_audit_complete_validation_locked",
        "blocks": len({row["block_id"] for row in rows}), "samples": len(rows),
        "ink_samples": int(labels.sum()), "control_samples": int((labels == 0).sum()),
        "control_exclusion_radius": int(config["control_exclusion_radius"]),
        "duplicates": len(rows) - len({(row["label"], row["y"], row["x"]) for row in rows}),
        "features": feature_results,
        "warning": "DEV diagnostic only. Controls are matched by 1024-pixel block, not by local fiber or CT texture.",
    }
    _atomic_csv(root / config["outputs"]["samples_csv"], rows)
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
