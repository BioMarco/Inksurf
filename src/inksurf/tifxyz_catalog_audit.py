"""Bounded metadata-only audit for published TIFXYZ candidates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import requests

from .coordinates import level_scale


class DownloadBudget:
    def __init__(self, *, max_requests: int, max_bytes: int) -> None:
        self.max_requests = max_requests
        self.max_bytes = max_bytes
        self.requests = 0
        self.bytes = 0

    def get(self, session: requests.Session, url: str, *, item_max_bytes: int, timeout: int) -> bytes:
        if self.requests >= self.max_requests:
            raise RuntimeError("network request budget exhausted")
        self.requests += 1
        with session.get(url, timeout=timeout, stream=True) as response:
            response.raise_for_status()
            declared = response.headers.get("content-length")
            if declared and int(declared) > item_max_bytes:
                raise RuntimeError(f"response exceeds item cap: {declared} > {item_max_bytes}")
            blocks: list[bytes] = []
            size = 0
            for block in response.iter_content(65536):
                if not block:
                    continue
                size += len(block)
                if size > item_max_bytes or self.bytes + size > self.max_bytes:
                    raise RuntimeError("network byte budget exhausted")
                blocks.append(block)
            self.bytes += size
            return b"".join(blocks)


def s3_to_https(url: str) -> str:
    if not url.startswith("s3://"):
        return url
    bucket, _, key = url[5:].partition("/")
    if not bucket or not key:
        raise ValueError(f"invalid S3 URL: {url}")
    return f"https://{bucket}.s3.amazonaws.com/{key}"


def tifxyz_meta_url(folder: str, segment_id: str, volume_id: str, voxel_size_um: float) -> str:
    suffix = f"{segment_id}-on-{volume_id}-{voxel_size_um:g}um.tifxyz/meta.json"
    return s3_to_https(folder.rstrip("/") + "/mesh/" + suffix)


def point_bbox_distance_xyz(point_xyz: np.ndarray, bbox: Any) -> float:
    bounds = np.asarray(bbox, dtype=np.float64)
    if bounds.shape != (2, 3) or not np.all(np.isfinite(bounds)) or np.any(bounds[1] < bounds[0]):
        raise ValueError("bbox must be finite [[xmin,ymin,zmin],[xmax,ymax,zmax]]")
    delta = np.maximum(np.maximum(bounds[0] - point_xyz, 0.0), point_xyz - bounds[1])
    return float(np.linalg.norm(delta))


def bbox_volume_xyz(bbox: Any) -> float:
    bounds = np.asarray(bbox, dtype=np.float64)
    if bounds.shape != (2, 3) or not np.all(np.isfinite(bounds)) or np.any(bounds[1] < bounds[0]):
        raise ValueError("bbox must be finite [[xmin,ymin,zmin],[xmax,ymax,zmax]]")
    return float(np.prod(bounds[1] - bounds[0]))


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


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    limits = config["network_limits"]
    budget = DownloadBudget(max_requests=int(limits["max_requests"]), max_bytes=int(limits["total_max_bytes"]))
    session = requests.Session()
    session.headers["User-Agent"] = "InkSurf/0.1 metadata-audit"
    timeout = int(limits["timeout_seconds"])
    catalog_raw = budget.get(
        session,
        config["catalog_url"],
        item_max_bytes=int(limits["catalog_max_bytes"]),
        timeout=timeout,
    )
    catalog = json.loads(catalog_raw)
    scroll = next(item for item in catalog["scrolls"] if item["id"] == config["scroll_id"])
    segments = [
        item
        for item in scroll["inkSegments"]
        if item.get("um") is not None
        and float(item["um"]) == float(config["voxel_size_um"])
    ]
    metas: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for segment in segments:
        url = tifxyz_meta_url(segment["folder"], segment["id"], config["volume_id"], float(config["voxel_size_um"]))
        last_error: Exception | None = None
        for attempt in range(int(limits["retries"]) + 1):
            try:
                raw = budget.get(session, url, item_max_bytes=int(limits["meta_max_bytes"]), timeout=timeout)
                meta = json.loads(raw)
                metas.append({"id": segment["id"], "label": segment.get("label", ""), "folder": segment["folder"], "url": url, "bbox": meta.get("bbox")})
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt < int(limits["retries"]):
                    time.sleep(0.2 * (attempt + 1))
        if last_error is not None:
            errors.append({"id": segment["id"], "url": url, "error": f"{type(last_error).__name__}: {last_error}"})

    candidate_report_path = root / config["candidate_report"]
    candidate_report = json.loads(candidate_report_path.read_text(encoding="utf-8"))
    scale = level_scale(int(config["candidate_level"]))
    rows: list[dict[str, Any]] = []
    for candidate in candidate_report["candidates"]:
        point_xyz_l0 = np.asarray(candidate["center_zyx_l3"], dtype=float)[::-1] * scale
        distances = []
        for meta in metas:
            try:
                distance = point_bbox_distance_xyz(point_xyz_l0, meta["bbox"])
                volume = bbox_volume_xyz(meta["bbox"])
            except (TypeError, ValueError):
                continue
            distances.append((distance, volume, meta))
        distances.sort(key=lambda item: (item[0], item[1], item[2]["id"]))
        for rank, (distance, volume, meta) in enumerate(distances[: int(config["shortlist_per_candidate"])], 1):
            rows.append(
                {
                    "candidate_rank": candidate["rank"],
                    "segment_rank": rank,
                    "segment_id": meta["id"],
                    "segment_label": meta["label"],
                    "bbox_distance_l0_voxels": round(distance, 6),
                    "bbox_contains_center": distance == 0.0,
                    "bbox_volume_l0_voxels3": round(volume, 3),
                    "meta_url": meta["url"],
                    "verification_status": "bbox_shortlist_only",
                }
            )
    report = {
        "experiment_id": config["experiment_id"],
        "status": "bbox_shortlist_only",
        "coordinate_order": {"candidates": "Z,Y,X", "tifxyz_bbox": "X,Y,Z"},
        "catalog": {"url": config["catalog_url"], "sha256": hashlib.sha256(catalog_raw).hexdigest(), "updated": catalog.get("updated")},
        "segments_in_catalog": len(segments),
        "metadata_loaded": len(metas),
        "metadata_errors": errors,
        "network_usage": {"requests": budget.requests, "bytes": budget.bytes, "limits": limits},
        "shortlist_rows": len(rows),
        "warning": "meta.json bboxes are only a shortlist device; ties prefer smaller boxes, but finite TIFXYZ coordinate pixels must be audited before ROI freeze",
    }
    output_dir = root / config["outputs"]["directory"]
    _atomic_write(output_dir / config["outputs"]["report_json"], json.dumps(report, indent=2, sort_keys=True) + "\n")
    fields = list(rows[0]) if rows else []
    from io import StringIO
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    _atomic_write(output_dir / config["outputs"]["shortlist_csv"], stream.getvalue())
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
