"""Fail closed when a revealed validation partition cannot meet frozen support gates."""

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


def decide(chunk_audit: dict, protocol: dict) -> dict:
    criteria = protocol["go_criteria"]
    chunks = chunk_audit["chunks"]
    total = int(chunk_audit["total_validation_pixels"])
    positive = int(chunk_audit["total_ink_pixels_in_validation"])
    negative = total - positive
    raw_both = sum(
        int(item["ink_pixels_in_validation"]) > 0
        and int(item["ink_pixels_in_validation"]) < int(item["validation_pixels"])
        for item in chunks
    )
    gates = {
        "maximum_possible_eligible_ink_pixels": positive >= int(criteria["minimum_eligible_ink_pixels"]),
        "maximum_possible_eligible_negative_pixels": negative >= int(criteria["minimum_eligible_negative_pixels"]),
        "maximum_possible_chunks_with_both_classes": raw_both >= int(criteria["minimum_chunks_with_both_classes"]),
    }
    return {
        "status": "CONTINUE_GEOMETRY_GATES" if all(gates.values()) else "NO_GO_LABEL_DIVERSITY_UPPER_BOUND",
        "validation_pixels": total,
        "ink_pixels": positive,
        "negative_pixels": negative,
        "chunks_with_both_classes_before_geometry": raw_both,
        "required_chunks_with_both_classes": int(criteria["minimum_chunks_with_both_classes"]),
        "gates": gates,
    }


def run(config_path: Path) -> dict:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    if cfg.get("schema_version") != "inksurf-validation-partition-gate/1.0":
        raise ValueError("unsupported schema_version")
    if cfg.get("track") != "A" or cfg.get("regime") != "VALIDATION":
        raise ValueError("partition gate requires Track A VALIDATION")
    root = config_path.resolve().parent.parent
    loaded = {}
    for name in ("protocol", "chunk_audit"):
        specification = cfg[name]
        path = root / specification["report"]
        if _sha256(path) != specification["sha256"]:
            raise ValueError(f"{name} hash mismatch")
        loaded[name] = json.loads(path.read_text(encoding="utf-8"))
    if loaded["protocol"].get("freeze_state") != "frozen_before_ground_truth":
        raise ValueError("protocol was not frozen before reveal")
    decision = decide(loaded["chunk_audit"], loaded["protocol"])
    report = {
        "schema_version": cfg["schema_version"], "experiment_id": cfg["experiment_id"],
        "track": "A", "regime": "VALIDATION", "geometry_tier": "G1",
        **decision,
        "score_comparison_allowed": decision["status"] == "CONTINUE_GEOMETRY_GATES",
        "additional_pixel_download_allowed": decision["status"] == "CONTINUE_GEOMETRY_GATES",
        "reason": (
            "Common-geometry filtering can only remove pixels and cannot increase the number of chunks containing both classes."
        ),
        "claim_limit": loaded["protocol"]["claim_limit"],
    }
    _atomic_json(root / cfg["output_report"], report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
