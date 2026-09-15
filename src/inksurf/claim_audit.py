"""Audit a ledger of scientific receipts and compute a fail-closed claim ceiling."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .seating_reproduce import _atomic_json


ROLES = {"compatibility", "repeatability", "development", "locked_validation", "post_hoc"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_entry(root: Path, specification: dict) -> dict:
    role = specification.get("role")
    if role not in ROLES:
        raise ValueError(f"unsupported evidence role: {role}")
    path = root / specification["artifact"]
    actual_hash = sha256(path)
    if actual_hash != specification["sha256"]:
        raise ValueError(f"hash mismatch for {path}")
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact.get("schema_version") != specification["expected_schema"]:
        raise ValueError(f"schema mismatch for {path}")
    regime = artifact.get("regime")
    tier = artifact.get("geometry_tier")
    if role == "locked_validation" and regime != "VALIDATION":
        raise ValueError("locked_validation receipt must declare VALIDATION")
    if role == "development" and regime != "DEV":
        raise ValueError("development receipt must declare DEV")
    if role == "post_hoc" and artifact.get("analysis_type") != "post_hoc_diagnostic":
        raise ValueError("post_hoc receipt must declare post_hoc_diagnostic")

    checks = artifact.get("go_checks", {})
    passed = sum(bool(value) for value in checks.values())
    groups = int(specification.get("independent_groups", 0))
    ground_truth_independent = bool(specification.get("ground_truth_independent", False))
    confirmation_eligible = (
        role == "locked_validation"
        and bool(checks)
        and passed == len(checks)
        and tier in {"G2", "G3"}
        and groups >= 2
        and ground_truth_independent
    )
    return {
        "evidence_id": specification["evidence_id"],
        "artifact": specification["artifact"],
        "sha256": actual_hash,
        "role": role,
        "status": artifact.get("status"),
        "regime": regime,
        "geometry_tier": tier,
        "independent_groups": groups,
        "ground_truth_independent": ground_truth_independent,
        "go_checks_passed": passed,
        "go_checks_total": len(checks),
        "confirmation_eligible": confirmation_eligible,
        "permitted_claim": specification["permitted_claim"],
    }


def run(config_path: Path) -> dict:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    if cfg.get("schema_version") != "inksurf-claim-audit/1.0":
        raise ValueError("invalid config schema")
    if cfg.get("track") != "A" or cfg.get("regime") != "DEV":
        raise ValueError("claim-ledger audit is a Track A DEV packaging operation")
    entries = [audit_entry(root, item) for item in cfg.get("evidence", [])]
    if not entries:
        raise ValueError("at least one evidence receipt is required")
    confirmations = [item for item in entries if item["confirmation_eligible"]]
    locked = [item for item in entries if item["role"] == "locked_validation"]
    post_hoc = [item for item in entries if item["role"] == "post_hoc"]
    guardrail_demonstrated = bool(locked and post_hoc and not confirmations)
    report = {
        "schema_version": cfg["schema_version"],
        "experiment_id": cfg["experiment_id"],
        "track": "A",
        "regime": "DEV",
        "status": "CLAIM_READY" if confirmations else "NO_GO_SUBMISSION_CLAIM",
        "software_guardrail_demonstrated": guardrail_demonstrated,
        "confirmation_eligible_receipts": len(confirmations),
        "evidence": entries,
        "claim_ceiling": (
            "locked_confirmatory_result"
            if confirmations
            else "failure-diagnostic software; no validated ink or structural claim"
        ),
        "next_requirement": (
            None
            if confirmations
            else "A G2/G3 locked result with at least two independent groups and independent ground truth."
        ),
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
