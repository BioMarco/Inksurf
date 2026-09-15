"""Combine registration and common-support receipts into a fail-closed decision."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .evidence_consistency import _atomic_json


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def decide(registration: dict, support: dict) -> str:
    if registration.get("status") != "GO_UV_CORRESPONDENCE":
        return "NO_GO_REGISTRATION"
    if int(support["totals"]["any"]["eligible_pixels"]) == 0:
        return "NO_GO_NO_LABELED_COMMON_SUPPORT"
    if int(support["center_supported_chunk_count"]) < int(support["minimum_supported_chunks"]):
        return "NO_GO_INSUFFICIENT_COMMON_SUPPORT"
    return "GO_SCORE_COMPARISON"


def run(config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-cross-model-candidate-decision/1.0":
        raise ValueError("unsupported schema_version")
    root = config_path.resolve().parent.parent
    receipts = {}
    for name in ("registration", "support"):
        specification = config[name]
        path = root / specification["report"]
        digest = _sha256(path)
        if digest != specification["sha256"]:
            raise ValueError(f"{name} report hash mismatch")
        receipts[name] = json.loads(path.read_text(encoding="utf-8"))
    status = decide(receipts["registration"], receipts["support"])
    score_allowed = status == "GO_SCORE_COMPARISON"
    report = {
        "schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
        "track": "A", "regime": "DEV", "status": status,
        "registration": {
            "report": config["registration"]["report"], "sha256": config["registration"]["sha256"],
            "status": receipts["registration"]["status"],
            "holdout_residual_um": receipts["registration"]["holdout_residual_um"],
        },
        "common_support": {
            "report": config["support"]["report"], "sha256": config["support"]["sha256"],
            "status": receipts["support"]["status"], "roi_count": receipts["support"]["roi_count"],
            "center_supported_chunk_count": receipts["support"]["center_supported_chunk_count"],
            "totals": receipts["support"]["totals"],
        },
        "score_comparison_performed": False,
        "score_comparison_allowed": score_allowed,
        "claim": (
            "The candidate is eligible for a separately configured score comparison; no ink claim follows from eligibility."
            if score_allowed else
            "No ink or model-quality claim: the candidate pair fails a prerequisite for score comparison."
        ),
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
