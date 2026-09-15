"""Download an exact frozen Zarr chunk manifest with resume and sparse-zero handling."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-zarr-chunk-download/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("chunk download must be Track A / DEV")
    root = config_path.resolve().parent.parent
    manifest_path = root / config["chunk_manifest_csv"]
    payload = manifest_path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != config["chunk_manifest_sha256"]:
        raise RuntimeError("chunk manifest SHA256 mismatch")
    rows = list(csv.DictReader(payload.decode("utf-8").splitlines()))
    planned = sum(int(row["raw_bytes"]) for row in rows)
    if planned > int(config["max_total_bytes"]):
        raise RuntimeError(f"chunk plan exceeds cap: {planned}")
    bases = config["volume_base_urls"]
    allowed = set(config["allowed_hosts"])
    cache_root = root / config["cache_root"]

    def download(row: dict[str, str]) -> dict[str, Any]:
        base = bases[row["volume_id"]].rstrip("/") + "/"
        url = base + row["object_key"]
        if urllib.parse.urlparse(url).hostname not in allowed:
            raise ValueError(f"host is not allowlisted: {url}")
        destination = cache_root / row["volume_id"] / row["object_key"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        expected = int(row["raw_bytes"])
        if destination.exists() and destination.stat().st_size == expected:
            status = "reused_existing"
        else:
            partial = destination.with_suffix(".partial")
            if partial.exists(): partial.unlink()
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "InkSurf-chunk-cache/1.0"})
                with urllib.request.urlopen(request, timeout=60) as source, partial.open("wb") as target:
                    written = 0
                    while block := source.read(min(4 * 1024 * 1024, expected - written + 1)):
                        written += len(block)
                        if written > expected: raise RuntimeError(f"chunk exceeds expected size: {url}")
                        target.write(block)
                    target.flush(); os.fsync(target.fileno())
                if written != expected: raise RuntimeError(f"chunk size mismatch: {written} != {expected}")
                os.replace(partial, destination)
                status = "downloaded"
            except urllib.error.HTTPError as exc:
                if partial.exists(): partial.unlink()
                if exc.code != 404: raise
                status = "absent_sparse_zero"
        return {
            "volume_id": row["volume_id"], "object_key": row["object_key"],
            "size_bytes": expected if status != "absent_sparse_zero" else 0,
            "sha256": _sha256(destination) if destination.exists() else None,
            "status": status,
        }

    with ThreadPoolExecutor(max_workers=int(config["workers"])) as executor:
        results = list(executor.map(download, rows))
    report = {
        "schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
        "track": config["track"], "regime": config["regime"], "planned_raw_bytes": planned,
        "materialized_bytes": sum(row["size_bytes"] for row in results),
        "chunk_objects": len(results),
        "downloaded": sum(row["status"] == "downloaded" for row in results),
        "reused_existing": sum(row["status"] == "reused_existing" for row in results),
        "absent_sparse_zero": sum(row["status"] == "absent_sparse_zero" for row in results),
        "status": "complete", "files": results,
    }
    _atomic_json(root / config["report_json"], report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
