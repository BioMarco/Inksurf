"""Conservatively audit declared evidence groups from source provenance."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
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


def audit_independence(
    views: list[dict],
    required_distinct_fields: list[str],
    minimum_effective_groups: int = 2,
) -> dict:
    if len(views) < 2:
        raise ValueError("at least two views are required")
    if not required_distinct_fields:
        raise ValueError("required_distinct_fields must not be empty")
    if minimum_effective_groups < 2:
        raise ValueError("minimum_effective_groups must be at least 2")
    view_ids = [item.get("view_id") for item in views]
    if any(not item for item in view_ids) or len(set(view_ids)) != len(view_ids):
        raise ValueError("view_id values must be unique and non-empty")
    groups = [item.get("independence_group") for item in views]
    if any(not item for item in groups):
        raise ValueError("every view requires independence_group")

    unique_groups = list(dict.fromkeys(groups))
    parent = {group: group for group in unique_groups}

    def find(group: str) -> str:
        while parent[group] != group:
            parent[group] = parent[parent[group]]
            group = parent[group]
        return group

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    dependencies = []
    for left_index, left in enumerate(views):
        for right in views[left_index + 1:]:
            left_group = left["independence_group"]
            right_group = right["independence_group"]
            if left_group == right_group:
                continue
            reasons = []
            for field in required_distinct_fields:
                left_value = left.get("provenance", {}).get(field)
                right_value = right.get("provenance", {}).get(field)
                if left_value is None or right_value is None:
                    reasons.append({"field": field, "reason": "missing_provenance"})
                elif left_value == right_value:
                    reasons.append({"field": field, "reason": "shared_value", "value": left_value})
            if reasons:
                union(left_group, right_group)
                dependencies.append({
                    "left_view": left["view_id"],
                    "right_view": right["view_id"],
                    "declared_groups": [left_group, right_group],
                    "reasons": reasons,
                })

    effective_roots = {group: find(group) for group in unique_groups}
    root_labels: dict[str, str] = {}
    for group in unique_groups:
        root = effective_roots[group]
        root_labels.setdefault(root, f"effective-group-{len(root_labels) + 1}")
    mapping = {group: root_labels[effective_roots[group]] for group in unique_groups}
    effective_count = len(set(mapping.values()))
    return {
        "declared_group_count": len(unique_groups),
        "effective_group_count": effective_count,
        "minimum_effective_groups": minimum_effective_groups,
        "independence_gate_passed": effective_count >= minimum_effective_groups,
        "required_distinct_fields": required_distinct_fields,
        "declared_to_effective_group": mapping,
        "dependency_edges": dependencies,
    }


def run(config_path: Path) -> dict:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    if cfg.get("schema_version") != "inksurf-independence-audit/1.0":
        raise ValueError("invalid config schema")
    if cfg.get("regime") not in {"DEV", "VALIDATION", "DISCOVERY"}:
        raise ValueError("regime must be explicit")
    if cfg.get("track") not in {"A", "B", "C"}:
        raise ValueError("track must be A, B or C")
    result = audit_independence(
        cfg["views"],
        list(cfg["policy"]["required_distinct_fields"]),
        int(cfg["policy"].get("minimum_effective_groups", 2)),
    )
    report = {
        "schema_version": cfg["schema_version"],
        "experiment_id": cfg["experiment_id"],
        "track": cfg["track"],
        "regime": cfg["regime"],
        "status": "PASS_INDEPENDENCE" if result["independence_gate_passed"] else "NO_GO_DEPENDENT_EVIDENCE",
        **result,
        "claim": "Effective groups are a conservative provenance audit, not proof of statistical independence.",
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
