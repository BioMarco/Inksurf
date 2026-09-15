"""Audit official catalog metadata for an evidence-consistency pilot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
import urllib.request
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class CatalogDocument:
    payload: bytes
    source_url: str


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


def fetch_catalog(url: str, max_bytes: int) -> CatalogDocument:
    """Fetch one bounded JSON document without touching volumetric artifacts."""
    request = urllib.request.Request(url, headers={"User-Agent": "InkSurf-evidence-preflight/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        declared = response.headers.get("Content-Length")
        if declared is not None and int(declared) > max_bytes:
            raise RuntimeError(f"catalog exceeds max_bytes before transfer: {declared} > {max_bytes}")
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise RuntimeError(f"catalog exceeds max_bytes: > {max_bytes}")
    return CatalogDocument(payload=payload, source_url=url)


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "inksurf-evidence-preflight/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("phase-0 evidence preflight must be Track A / DEV")
    catalog = config.get("catalog", {})
    if not catalog.get("url") or not catalog.get("sha256"):
        raise ValueError("catalog url and sha256 are required")
    if int(catalog.get("max_bytes", 0)) <= 0:
        raise ValueError("catalog max_bytes must be positive")
    targets = config.get("development_targets", [])
    if not targets or len(targets) != len(set(targets)):
        raise ValueError("development_targets must be non-empty and unique")
    rules = config.get("gate", {})
    if int(rules.get("minimum_scans", 0)) < 2:
        raise ValueError("minimum_scans must be at least two")
    if int(rules.get("minimum_pair_dimensions", 0)) < 1:
        raise ValueError("minimum_pair_dimensions must be positive")


def _facility(scan: dict[str, Any]) -> str:
    return str(scan.get("loc") or "unknown")


def _pair_row(sample_id: str, first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    dimensions = {
        "acquisition": str(first.get("id")) != str(second.get("id")),
        "energy": first.get("energy") != second.get("energy"),
        "resolution": first.get("px") != second.get("px"),
        "facility": _facility(first) != _facility(second),
    }
    # Acquisition identity is mandatory but is not enough: at least one physical
    # acquisition dimension must also differ.
    physical_dimensions = sum(dimensions[name] for name in ("energy", "resolution", "facility"))
    return {
        "sample_id": sample_id,
        "scan_a": str(first.get("id")),
        "scan_b": str(second.get("id")),
        "px_a_um": float(first["px"]),
        "px_b_um": float(second["px"]),
        "energy_a_kev": float(first["energy"]),
        "energy_b_kev": float(second["energy"]),
        "facility_a": _facility(first),
        "facility_b": _facility(second),
        "distinct_acquisition": dimensions["acquisition"],
        "cross_energy": dimensions["energy"],
        "cross_resolution": dimensions["resolution"],
        "cross_facility": dimensions["facility"],
        "physical_independence_dimensions": physical_dimensions,
    }


def _base_volume_id(url: Any) -> str | None:
    match = re.search(r"volume-(\d+)", str(url or ""))
    return match.group(1) if match else None


def _artifact_pair_rows(sample_id: str, sample: dict[str, Any]) -> list[dict[str, Any]]:
    """Find same-label surfaces backed by distinct source volumes.

    A shared label is only a catalog-level correspondence hint. It does not
    establish pixel alignment or independence of the derived ink predictions.
    """
    by_label: dict[str, list[dict[str, Any]]] = {}
    for segment in sample.get("inkSegments") or []:
        label = str(segment.get("label") or "")
        if label:
            by_label.setdefault(label, []).append(segment)

    rows: list[dict[str, Any]] = []
    for label, segments in sorted(by_label.items()):
        for first, second in combinations(segments, 2):
            surface_a = _base_volume_id(first.get("layers"))
            surface_b = _base_volume_id(second.get("layers"))
            if not surface_a or not surface_b or surface_a == surface_b:
                continue
            ink_a = _base_volume_id(first.get("full"))
            ink_b = _base_volume_id(second.get("full"))
            rows.append({
                "sample_id": sample_id,
                "label": label,
                "segment_a": str(first.get("id")),
                "segment_b": str(second.get("id")),
                "surface_volume_a": surface_a,
                "surface_volume_b": surface_b,
                "ink_volume_a": ink_a or "",
                "ink_volume_b": ink_b or "",
                "both_ink_outputs_present": bool(first.get("full") and second.get("full")),
                "distinct_ink_source_volumes": bool(ink_a and ink_b and ink_a != ink_b),
                "layers_a": str(first.get("layers") or ""),
                "layers_b": str(second.get("layers") or ""),
                "ink_output_a": str(first.get("full") or ""),
                "ink_output_b": str(second.get("full") or ""),
                "alignment_status": "same_label_only_transform_unverified",
            })
    return rows


def audit_catalog(
    config: dict[str, Any], document: CatalogDocument
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    validate_config(config)
    digest = hashlib.sha256(document.payload).hexdigest()
    expected = config["catalog"]["sha256"].lower()
    if digest != expected:
        raise RuntimeError(f"catalog SHA256 mismatch: {digest} != {expected}")
    catalog = json.loads(document.payload)
    samples = {item["id"]: item for item in catalog.get("scrolls", [])}
    missing = sorted(set(config["development_targets"]) - samples.keys())
    if missing:
        raise RuntimeError("catalog is missing development targets: " + ", ".join(missing))

    gate = config["gate"]
    rows: list[dict[str, Any]] = []
    artifact_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for sample_id in config["development_targets"]:
        sample = samples[sample_id]
        scans = list(sample.get("scans") or [])
        pairs = [_pair_row(sample_id, a, b) for a, b in combinations(scans, 2)]
        qualified = [
            row for row in pairs
            if row["distinct_acquisition"]
            and row["physical_independence_dimensions"] >= int(gate["minimum_pair_dimensions"])
        ]
        for row in pairs:
            row["pair_qualifies_metadata_gate"] = row in qualified
        rows.extend(pairs)
        artifact_rows.extend(_artifact_pair_rows(sample_id, sample))
        stages = sample.get("stages") or {}
        ink_segments = list(sample.get("inkSegments") or [])
        summary = {
            "sample_id": sample_id,
            "known_text_dev": bool(stages.get("text")),
            "scan_count": len(scans),
            "segment_count": int(sample.get("n_segments") or 0),
            "ink_segment_count": int(sample.get("n_inkSegments") or 0),
            "ink_segment_entries": len(ink_segments),
            "ink_outputs_present": sum(bool(item.get("full")) for item in ink_segments),
            "prediction_count": int(sample.get("n_predictions") or 0),
            "has_surface_prediction": bool(sample.get("hasSurfacePred")),
            "has_ink3d": bool(sample.get("hasInk3d")),
            "qualified_scan_pairs": len(qualified),
            "legal_notice_present": bool(sample.get("legalNotice")),
        }
        summary["metadata_ready"] = bool(
            summary["known_text_dev"]
            and summary["scan_count"] >= int(gate["minimum_scans"])
            and summary["segment_count"] >= int(gate["minimum_segments"])
            and summary["ink_segment_count"] >= int(gate["minimum_ink_segments"])
            and summary["qualified_scan_pairs"] >= int(gate["minimum_qualified_pairs"])
        )
        summaries.append(summary)

    ready = [item for item in summaries if item["metadata_ready"]]
    independent_ink_pairs = sum(bool(row["distinct_ink_source_volumes"]) for row in artifact_rows)
    if not ready:
        status = "no_go_metadata"
    elif independent_ink_pairs:
        status = "conditional_go_alignment_unverified"
    elif artifact_rows:
        status = "conditional_go_raw_evidence_only"
    else:
        status = "conditional_go_metadata_only"
    report = {
        "schema_version": config["schema_version"],
        "experiment_id": config["experiment_id"],
        "track": config["track"],
        "regime": config["regime"],
        "status": status,
        "catalog": {
            "url": document.source_url,
            "bytes": len(document.payload),
            "sha256": digest,
            "catalog_updated": catalog.get("updated"),
        },
        "samples": summaries,
        "metadata_ready_samples": [item["sample_id"] for item in ready],
        "same_label_cross_volume_artifact_pairs": len(artifact_rows),
        "independent_ink_output_pairs": independent_ink_pairs,
        "downloaded_volumetric_bytes": 0,
        "validation_files_accessed": 0,
        "discovery_files_accessed": 0,
        "blockers": (
            [
                "same-surface overlap across scans is not established by catalog metadata",
                "cross-scan transforms and registration error are not yet verified",
                "the same-label cross-volume candidates provide zero independent ink-output pairs",
                "a held-out evaluation unit has not yet been frozen",
            ]
            if ready else ["no development sample satisfies the preregistered metadata gate"]
        ),
        "claim": (
            "The official catalog contains plausible DEV sources for a bounded consistency pilot; "
            "this does not establish co-registration, ink evidence, or prize readiness."
        ),
    }
    return report, rows, artifact_rows


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    from io import StringIO

    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows({field: row[field] for field in fields} for row in rows)
    _atomic_write(path, stream.getvalue())


def write_outputs(
    config_path: Path,
    report: dict[str, Any],
    rows: list[dict[str, Any]],
    artifact_rows: list[dict[str, Any]],
) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    outputs = config["outputs"]
    _atomic_write(root / outputs["report_json"], json.dumps(report, indent=2, sort_keys=True) + "\n")
    fields = [
        "sample_id", "scan_a", "scan_b", "px_a_um", "px_b_um", "energy_a_kev",
        "energy_b_kev", "facility_a", "facility_b", "distinct_acquisition", "cross_energy",
        "cross_resolution", "cross_facility", "physical_independence_dimensions",
        "pair_qualifies_metadata_gate",
    ]
    _write_csv(root / outputs["pairs_csv"], fields, rows)
    artifact_fields = [
        "sample_id", "label", "segment_a", "segment_b", "surface_volume_a",
        "surface_volume_b", "ink_volume_a", "ink_volume_b", "both_ink_outputs_present",
        "distinct_ink_source_volumes", "layers_a", "layers_b", "ink_output_a",
        "ink_output_b", "alignment_status",
    ]
    _write_csv(root / outputs["artifact_pairs_csv"], artifact_fields, artifact_rows)


def run(config_path: Path, fetcher: Callable[[str, int], CatalogDocument] = fetch_catalog) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    document = fetcher(config["catalog"]["url"], int(config["catalog"]["max_bytes"]))
    report, rows, artifact_rows = audit_catalog(config, document)
    write_outputs(config_path, report, rows, artifact_rows)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
