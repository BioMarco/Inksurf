"""Metadata-only preflight for a bounded official ink_9um DEV benchmark."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import requests

from .seating_reproduce import _atomic_json

NEXT = re.compile(r'<([^>]+)>; rel="next"')


def list_bucket_tree(url: str, max_pages: int) -> tuple[list[dict[str, Any]], int]:
    items: list[dict[str, Any]] = []
    transferred = 0
    current: str | None = url
    for _ in range(max_pages):
        if current is None:
            break
        response = requests.get(current, timeout=60)
        response.raise_for_status()
        transferred += len(response.content)
        page = response.json()
        if not isinstance(page, list):
            raise ValueError("bucket API did not return a list")
        items.extend(page)
        match = NEXT.search(response.headers.get("Link", ""))
        current = match.group(1) if match else None
    if current is not None:
        raise RuntimeError("bucket listing exceeded max_api_pages")
    return items, transferred


def chunk_key(path: str) -> tuple[int, int] | None:
    name = path.rsplit("/", 1)[-1]
    match = re.fullmatch(r"0\.(\d+)\.(\d+)", name)
    return (int(match.group(1)), int(match.group(2))) if match else None


def select_validation_chunks(
    items: list[dict[str, Any]], count: int, chunk_bounds_yx: list[list[int]] | None = None,
    minimum_compressed_bytes: int = 0,
) -> list[dict[str, Any]]:
    candidates = []
    marker = "_validation_mask.zarr/0/"
    for item in items:
        key = chunk_key(str(item.get("path", "")))
        if marker in str(item.get("path", "")) and key is not None:
            if chunk_bounds_yx is not None:
                (y0, y1), (x0, x1) = chunk_bounds_yx
                if not (y0 <= key[0] < y1 and x0 <= key[1] < x1):
                    continue
            if int(item["size"]) < minimum_compressed_bytes:
                continue
            candidates.append({"chunk_yx": list(key), "compressed_validation_bytes": int(item["size"])})
    candidates.sort(key=lambda item: (-item["compressed_validation_bytes"], item["chunk_yx"]))
    if len(candidates) < count:
        raise ValueError(f"only {len(candidates)} validation chunks found")
    return candidates[:count]


def raw_chunk_bytes(shape: list[int], chunks: list[int], y: int, x: int) -> int:
    height = min(chunks[1], shape[1] - y * chunks[1])
    width = min(chunks[2], shape[2] - x * chunks[2])
    if height <= 0 or width <= 0:
        raise ValueError("chunk outside source array")
    return shape[0] * height * width


def fetch_json(url: str) -> tuple[dict[str, Any], int]:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json(), len(response.content)


def run(config_path: Path) -> dict[str, Any]:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    if cfg.get("schema_version") != "inksurf-ink9um-validation-preflight/1.0":
        raise ValueError("invalid config schema")
    regime = cfg.get("regime")
    if cfg.get("track") != "A" or regime not in {"DEV", "VALIDATION"}:
        raise ValueError("preflight is restricted to Track A DEV/VALIDATION")
    if regime == "VALIDATION" and (
        cfg.get("freeze_state") != "frozen_before_ground_truth"
        or not cfg.get("method_source_sha256")
        or not cfg.get("validation_partition_id")
        or int(cfg.get("ground_truth_reveal_count_before", -1)) != 0
    ):
        raise ValueError("VALIDATION preflight requires a complete unrevealed method lock")
    if not cfg["annotation_api_url"].startswith("https://huggingface.co/api/buckets/scrollprize/"):
        raise ValueError("unexpected annotation API host")
    if not cfg["source_volume_url"].startswith("https://vesuvius-challenge-open-data.s3.amazonaws.com/"):
        raise ValueError("unexpected volume host")

    items, transferred = list_bucket_tree(cfg["annotation_api_url"], int(cfg["max_api_pages"]))
    prefix = cfg["annotation_prefix"] + "/"
    if any(not str(item.get("path", "")).startswith(prefix) for item in items):
        raise ValueError("listing escaped frozen annotation prefix")
    arrays = {}
    for kind in ("inklabels", "supervision_mask", "validation_mask"):
        relative = f"{prefix}{cfg['segment']}_{kind}.zarr/0/.zarray"
        arrays[kind], size = fetch_json(cfg["annotation_resolve_base"] + relative)
        transferred += size
    shapes = {tuple(meta["shape"]) for meta in arrays.values()}
    chunks = {tuple(meta["chunks"]) for meta in arrays.values()}
    if len(shapes) != 1 or len(chunks) != 1 or next(iter(shapes))[0] != 21:
        raise ValueError("annotation arrays are not aligned 21-slice Zarrs")

    source_meta, size = fetch_json(f"{cfg['source_volume_url']}/{cfg['source_level']}/.zarray")
    transferred += size
    if source_meta.get("dtype") != "|u1" or source_meta.get("chunks", [None])[0] != source_meta.get("shape", [None])[0]:
        raise ValueError("unsupported source layout")
    if list(source_meta["shape"][1:]) != list(next(iter(shapes))[1:]):
        raise ValueError("annotation and source XY shapes differ")

    try:
        selected = select_validation_chunks(
            items, int(cfg["roi_chunk_count"]), cfg.get("selection_chunk_bounds_yx"),
            int(cfg.get("minimum_compressed_validation_bytes", 0)),
        )
    except ValueError as exc:
        report = {
            "schema_version": cfg["schema_version"], "experiment_id": cfg["experiment_id"],
            "status": "NO_GO_NO_LABELED_OVERLAP", "track": "A", "regime": regime,
            "geometry_tier": "G1", "listed_annotation_objects": len(items),
            "metadata_bytes_transferred": transferred,
            "selection_chunk_bounds_yx": cfg.get("selection_chunk_bounds_yx"),
            "minimum_compressed_validation_bytes": int(cfg.get("minimum_compressed_validation_bytes", 0)),
            "selection_error": str(exc), "selected_chunk_count": 0,
            "planned_source_raw_bytes": 0, "planned_annotation_bytes": 0,
            "validation_files_accessed": 0, "discovery_files_accessed": 0,
            "limitations": [
                "The second render coverage does not overlap a non-empty transferred-label validation chunk.",
                "No source, prediction or label pixels were downloaded by this failed preflight.",
            ],
        }
        _atomic_json(root / cfg["report_json"], report)
        return report
    item_index = {str(item["path"]): item for item in items}
    planned_raw = 0
    planned_annotation = 0
    download_files = []
    for entry in selected:
        y, x = entry["chunk_yx"]
        entry["source_chunk_url"] = f"{cfg['source_volume_url']}/{cfg['source_level']}/0/{y}/{x}"
        entry["source_raw_bytes"] = raw_chunk_bytes(source_meta["shape"], source_meta["chunks"], y, x)
        entry["annotation_chunks"] = {}
        download_files.append({
            "url": entry["source_chunk_url"],
            "destination": f"source/{cfg['source_level']}/0/{y}/{x}",
            "size_bytes": entry["source_raw_bytes"],
        })
        for kind in arrays:
            relative = f"{prefix}{cfg['segment']}_{kind}.zarr/0/0.{y}.{x}"
            remote = item_index.get(relative)
            if remote is None:
                raise ValueError(f"annotation chunk missing from listing: {relative}")
            annotation = {
                "url": cfg["annotation_resolve_base"] + relative,
                "size_bytes": int(remote["size"]),
                "xet_hash": remote["xetHash"],
            }
            entry["annotation_chunks"][kind] = annotation
            planned_annotation += annotation["size_bytes"]
            download_files.append({
                "url": annotation["url"],
                "size_bytes": annotation["size_bytes"],
                "xet_hash": annotation["xet_hash"],
                "destination": f"annotations/{kind}/0.{y}.{x}",
            })
        planned_raw += entry["source_raw_bytes"]

    manifest = {
        "schema_version": cfg["schema_version"],
        "experiment_id": cfg["experiment_id"],
        "track": "A",
        "regime": regime,
        "geometry_tier": "G1",
        "selection": cfg["roi_selection"],
        "source_axes": "Z,Y,X",
        "source_shape_zyx": source_meta["shape"],
        "source_chunks_zyx": source_meta["chunks"],
        "annotation_shape_zyx": list(next(iter(shapes))),
        "annotation_chunks_zyx": list(next(iter(chunks))),
        "selected_chunks": selected,
        "planned_source_raw_bytes": planned_raw,
        "planned_annotation_bytes": planned_annotation,
    }
    download_manifest = {
        "schema_version": "inksurf-validation-http-download/1.0" if regime == "VALIDATION" else "inksurf-bounded-http-download/1.0",
        "experiment_id": cfg["experiment_id"] + "-download",
        "track": "A",
        "regime": regime,
        "project_root_relative": "../..",
        "allowed_hosts": [
            "vesuvius-challenge-open-data.s3.amazonaws.com",
            "huggingface.co",
            "us.aws.cdn.hf.co",
            "cdn-lfs.hf.co"
        ],
        "max_total_bytes": cfg["max_download_bytes"],
        "output_root": cfg["download_output_root"],
        "report_json": cfg["download_report_json"],
        "files": download_files,
    }
    if regime == "VALIDATION":
        download_manifest.update({
            "freeze_state": cfg["freeze_state"],
            "method_source_sha256": cfg["method_source_sha256"],
            "validation_partition_id": cfg["validation_partition_id"],
            "ground_truth_reveal_count_before": cfg["ground_truth_reveal_count_before"],
        })
    if planned_raw + planned_annotation > int(cfg["max_download_bytes"]):
        raise RuntimeError("planned bounded download exceeds frozen cap")
    report = {
        "schema_version": cfg["schema_version"],
        "experiment_id": cfg["experiment_id"],
        "status": "bounded_download_ready",
        "track": "A",
        "regime": regime,
        "geometry_tier": "G1",
        "listed_annotation_objects": len(items),
        "metadata_bytes_transferred": transferred,
        "selected_chunk_count": len(selected),
        "selection_chunk_bounds_yx": cfg.get("selection_chunk_bounds_yx"),
        "planned_source_raw_bytes": planned_raw,
        "planned_annotation_bytes": planned_annotation,
        "validation_files_accessed": 0,
        "discovery_files_accessed": 0,
        "limitations": [
            (
                "This is a locally locked VALIDATION partition, but it remains an upstream online-validation case."
                if regime == "VALIDATION"
                else "Official online-validation data is classified DEV, not confirmatory validation."
            ),
            "Labels are transferred annotations/pseudo-labels, not independent IR ground truth.",
            "Compressed validation-chunk size is a deterministic coverage proxy, not an ink score.",
        ],
    }
    _atomic_json(root / cfg["chunk_manifest_json"], manifest)
    _atomic_json(root / cfg["download_manifest_json"], download_manifest)
    _atomic_json(root / cfg["report_json"], report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
