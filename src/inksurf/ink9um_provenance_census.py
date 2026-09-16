"""Census ink_9um provenance and exact-source ink renders without pixel access."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import tempfile
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests

from .evidence_consistency import _atomic_json


VOLUME = re.compile(r"volume-(\d+)")
MODEL = re.compile(r"-(new_canon_autoresearch_recipe|mrg20736-1um-s1z2)-")


def source_segment_prefix(source_volume_url: str) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(source_volume_url)
    if parsed.hostname != "vesuvius-challenge-open-data.s3.amazonaws.com":
        raise ValueError("unexpected source volume host")
    key = parsed.path.lstrip("/")
    marker = "/surface-volumes/"
    if marker not in key:
        raise ValueError("source volume URL does not identify a segment surface volume")
    prefix = key.split(marker, 1)[0]
    sample = prefix.split("/", 1)[0]
    return sample, prefix


def parse_ink_render(key: str, size: int, etag: str, bucket_base: str) -> dict[str, Any]:
    name = key.rsplit("/", 1)[-1]
    volume = VOLUME.search(name)
    model = MODEL.search(name)
    return {
        "url": bucket_base.rstrip("/") + "/" + key,
        "size_bytes": size,
        "etag": etag.strip('"'),
        "source_volume_id": volume.group(1) if volume else None,
        "model_id": model.group(1).replace("-", "_") if model else None,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", newline="", encoding="utf-8") as stream:
            fields = [
                "case_id", "sample_id", "source_segment_prefix", "source_volume_url", "source_level",
                "online_validation", "annotation_arrays", "validation_mask_present", "ink_render_count",
                "distinct_render_volume_count", "distinct_model_count", "candidate_status",
            ]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows({key: row[key] for key in fields} for row in rows)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def run(config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-ink9um-provenance-census/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("provenance census is Track A DEV only")
    root = config_path.resolve().parent.parent
    transferred = 0
    session = requests.Session()
    config_digest = hashlib.sha256(config_path.read_bytes()).hexdigest()
    cache_path = root / config["cache_json"]
    cache = {"config_sha256": config_digest, "root_metadata_bytes": 0, "cases": {}}
    if cache_path.is_file():
        loaded = json.loads(cache_path.read_text(encoding="utf-8"))
        if loaded.get("config_sha256") == config_digest:
            cache = loaded

    def get(url: str, **kwargs) -> requests.Response:
        nonlocal transferred
        for attempt in range(int(config["maximum_retries"]) + 1):
            try:
                response = session.get(url, timeout=int(config["timeout_seconds"]), **kwargs)
                response.raise_for_status()
                transferred += len(response.content)
                if transferred > int(config["maximum_metadata_bytes"]):
                    raise RuntimeError("metadata census exceeded byte cap")
                return response
            except requests.RequestException:
                if attempt >= int(config["maximum_retries"]):
                    raise
                time.sleep(min(2 ** attempt, 4))
        raise AssertionError("unreachable retry state")

    directory_url = config["annotation_root_api"] + "?recursive=false&limit=1000"
    root_response = get(directory_url)
    cases_page = root_response.json()
    cache["root_metadata_bytes"] = len(root_response.content)
    cases = sorted(item["path"].rsplit("/", 1)[-1] for item in cases_page if item.get("type") == "directory")
    if not cases or len(cases) > int(config["maximum_cases"]):
        raise RuntimeError("unexpected annotation case count")
    rows = []
    reused = 0
    for case in cases:
        if case in cache["cases"]:
            rows.append(cache["cases"][case]["row"])
            reused += 1
            continue
        before_case = transferred
        prefix = config["annotation_root_prefix"].rstrip("/") + "/" + case
        arrays_page = get(
            config["annotation_api_base"].rstrip("/") + "/" + prefix + "?recursive=false&limit=100"
        ).json()
        arrays = sorted(
            item["path"].rsplit("/", 1)[-1].removeprefix(case + "_").removesuffix(".zarr")
            for item in arrays_page if item.get("type") == "directory"
        )
        attrs_url = config["annotation_resolve_base"].rstrip("/") + "/" + prefix + f"/{case}_inklabels.zarr/.zattrs"
        attrs = get(attrs_url).json()
        sample, segment_prefix = source_segment_prefix(attrs["source_surface_volume"])
        listing = get(
            config["s3_list_url"],
            params={"list-type": "2", "prefix": segment_prefix + "/ink-detection/"},
        )
        xml = ET.fromstring(listing.content)
        namespace = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
        renders = []
        for item in xml.findall("s:Contents", namespace):
            key = item.find("s:Key", namespace).text
            if key.endswith(".tif") and "/downsampled/" not in key:
                renders.append(parse_ink_render(
                    key, int(item.find("s:Size", namespace).text), item.find("s:ETag", namespace).text,
                    config["s3_object_base"],
                ))
        volumes = {item["source_volume_id"] for item in renders if item["source_volume_id"]}
        models = {item["model_id"] for item in renders if item["model_id"]}
        has_validation = "validation_mask" in arrays
        status = (
            "candidate_validation_registration_support_unverified"
            if has_validation and len(volumes) >= 2 and len(models) >= 2
            else "candidate_dev_supervision_only"
            if len(volumes) >= 2 and len(models) >= 2
            else "no_distinct_render_pair"
        )
        row = {
            "case_id": case, "sample_id": sample, "source_segment_prefix": segment_prefix,
            "source_volume_url": attrs["source_surface_volume"],
            "source_level": int(attrs["source_surface_volume_level"]),
            "online_validation": bool(attrs.get("online_validation")),
            "annotation_arrays": ";".join(arrays), "validation_mask_present": has_validation,
            "ink_render_count": len(renders), "distinct_render_volume_count": len(volumes),
            "distinct_model_count": len(models), "candidate_status": status, "renders": renders,
        }
        rows.append(row)
        cache["cases"][case] = {"metadata_bytes": transferred - before_case, "row": row}
        _atomic_json(cache_path, cache)
    accounted = int(cache["root_metadata_bytes"]) + sum(int(item["metadata_bytes"]) for item in cache["cases"].values())
    if accounted > int(config["maximum_metadata_bytes"]):
        raise RuntimeError("accounted metadata census exceeds byte cap")
    candidates = [row for row in rows if row["candidate_status"].startswith("candidate_")]
    validation_candidates = [row for row in rows if row["candidate_status"].startswith("candidate_validation")]
    report = {
        "schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
        "track": "A", "regime": "DEV", "status": "metadata_census_complete",
        "case_count": len(rows), "metadata_bytes_transferred_this_run": transferred,
        "metadata_bytes_accounted": accounted, "metadata_cache_reused_cases": reused,
        "distinct_render_pair_cases": len(candidates), "validation_candidate_cases": len(validation_candidates),
        "cases": rows, "pixel_files_accessed": 0,
        "claim_limit": "Catalog candidates only; registration, common support, training independence and reference independence remain unverified.",
    }
    _atomic_json(root / config["output_report"], report)
    _write_csv(root / config["output_csv"], rows)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    report = run(args.config)
    print(json.dumps({key: report[key] for key in (
        "status", "case_count", "metadata_bytes_accounted", "metadata_bytes_transferred_this_run",
        "metadata_cache_reused_cases", "distinct_render_pair_cases",
        "validation_candidate_cases", "pixel_files_accessed",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
