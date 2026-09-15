"""Import a pinned external seating audit and screen cross-scan evidence pairs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
import urllib.request
from itertools import combinations
from pathlib import Path
from typing import Any, Callable


VOLUME_RE = re.compile(r"^(?P<id>\d+)-(?P<um>\d+(?:\.\d+)?)um-")
ENERGY_RE = re.compile(r"-(?P<kev>\d+)keV-")


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def fetch(url: str, max_bytes: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "InkSurf-seating-import/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        declared = response.headers.get("Content-Length")
        if declared is not None and int(declared) > max_bytes:
            raise RuntimeError(f"seating report exceeds max_bytes: {declared} > {max_bytes}")
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise RuntimeError(f"seating report exceeds max_bytes: > {max_bytes}")
    return payload


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "inksurf-seating-import/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("seating import must be Track A / DEV")
    source = config.get("source", {})
    if not source.get("url") or not source.get("sha256") or int(source.get("max_bytes", 0)) <= 0:
        raise ValueError("pinned source url, sha256 and max_bytes are required")
    gate = config.get("gate", {})
    if float(gate.get("minimum_score", -1)) < 0:
        raise ValueError("minimum_score must be non-negative")
    if not 0 <= float(gate.get("minimum_coverage", -1)) <= 1:
        raise ValueError("minimum_coverage must be in [0, 1]")
    if float(gate.get("maximum_voxel_um", 0)) <= 0:
        raise ValueError("maximum_voxel_um must be positive")


def _parse_volume(name: str) -> dict[str, Any]:
    match = VOLUME_RE.match(name)
    if not match:
        raise ValueError(f"cannot parse volume provenance: {name}")
    energy = ENERGY_RE.search(name)
    return {
        "acquisition_id": match.group("id"),
        "voxel_um": float(match.group("um")),
        "energy_kev": int(energy.group("kev")) if energy else None,
    }


def screen_rows(config: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    validate_config(config)
    gate = config["gate"]
    normalized = []
    for row in rows:
        required = {"scroll", "segment", "mesh", "volume", "score", "coverage"}
        missing = required - row.keys()
        if missing:
            raise ValueError("seating row missing: " + ", ".join(sorted(missing)))
        parsed = _parse_volume(str(row["volume"]))
        normalized.append({**row, **parsed})

    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in normalized:
        groups.setdefault((str(row["scroll"]), str(row["mesh"])), []).append(row)

    pairs: list[dict[str, Any]] = []
    for (scroll, mesh), candidates in sorted(groups.items()):
        resolution_eligible = [
            row for row in candidates
            if float(row["voxel_um"]) <= float(gate["maximum_voxel_um"])
        ]
        for first, second in combinations(resolution_eligible, 2):
            if first["acquisition_id"] == second["acquisition_id"]:
                continue
            pair_passes = bool(
                min(float(first["score"]), float(second["score"])) >= float(gate["minimum_score"])
                and min(float(first["coverage"]), float(second["coverage"]))
                >= float(gate["minimum_coverage"])
            )
            pairs.append({
                "scroll": scroll,
                "mesh": mesh,
                "segment": str(first["segment"]),
                "volume_a": str(first["volume"]),
                "volume_b": str(second["volume"]),
                "acquisition_a": first["acquisition_id"],
                "acquisition_b": second["acquisition_id"],
                "voxel_a_um": first["voxel_um"],
                "voxel_b_um": second["voxel_um"],
                "energy_a_kev": first["energy_kev"],
                "energy_b_kev": second["energy_kev"],
                "score_a": float(first["score"]),
                "score_b": float(second["score"]),
                "coverage_a": float(first["coverage"]),
                "coverage_b": float(second["coverage"]),
                "score_shortfall": round(max(
                    0.0,
                    float(gate["minimum_score"]) - float(first["score"]),
                    float(gate["minimum_score"]) - float(second["score"]),
                ), 6),
                "coverage_shortfall": round(max(
                    0.0,
                    float(gate["minimum_coverage"]) - float(first["coverage"]),
                    float(gate["minimum_coverage"]) - float(second["coverage"]),
                ), 6),
                "pair_passes_gate": pair_passes,
                "status": (
                    "eligible_from_external_audit_not_reproduced"
                    if pair_passes else "screened_below_gate"
                ),
            })

    passing_rows = sum(
        float(row["score"]) >= float(gate["minimum_score"])
        and float(row["coverage"]) >= float(gate["minimum_coverage"])
        and float(row["voxel_um"]) <= float(gate["maximum_voxel_um"])
        for row in normalized
    )
    passing_pairs = sum(bool(pair["pair_passes_gate"]) for pair in pairs)
    report = {
        "schema_version": config["schema_version"],
        "experiment_id": config["experiment_id"],
        "track": config["track"],
        "regime": config["regime"],
        "status": (
            "go_external_pair_requires_reproduction"
            if passing_pairs else "no_go_no_strict_cross_scan_pair"
        ),
        "gate": gate,
        "rows_imported": len(normalized),
        "scrolls_imported": len({row["scroll"] for row in normalized}),
        "rows_passing_individual_gate": passing_rows,
        "cross_scan_pairs_screened": len(pairs),
        "cross_scan_pairs_passing_gate": passing_pairs,
        "claim": (
            "Imported measurements are third-party evidence. A pair cannot enter InkSurf "
            "VALIDATION or DISCOVERY until the seating result is independently reproduced."
        ),
    }
    return report, pairs


def run(config_path: Path, fetcher: Callable[[str, int], bytes] = fetch) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    payload = fetcher(config["source"]["url"], int(config["source"]["max_bytes"]))
    digest = hashlib.sha256(payload).hexdigest()
    if digest != str(config["source"]["sha256"]).lower():
        raise RuntimeError(f"seating report SHA256 mismatch: {digest}")
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError("seating report must be a JSON list")
    report, pairs = screen_rows(config, rows)
    report["source"] = {
        "url": config["source"]["url"],
        "upstream_commit": config["source"]["upstream_commit"],
        "bytes": len(payload),
        "sha256": digest,
    }
    root = config_path.resolve().parent.parent
    _atomic_write(root / config["outputs"]["report_json"], json.dumps(report, indent=2, sort_keys=True) + "\n")
    fields = list(pairs[0]) if pairs else ["scroll", "mesh", "segment", "status"]
    from io import StringIO
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(pairs)
    _atomic_write(root / config["outputs"]["pairs_csv"], stream.getvalue())
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
