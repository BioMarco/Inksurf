"""Download a small frozen DEV asset manifest with strict byte and host caps."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def validate_manifest(manifest: dict[str, Any]) -> int:
    schema = manifest.get("schema_version")
    if schema not in {"inksurf-bounded-http-download/1.0", "inksurf-validation-http-download/1.0"}:
        raise ValueError("unsupported schema_version")
    if manifest.get("track") != "A":
        raise ValueError("bounded downloader is restricted to Track A")
    if schema == "inksurf-bounded-http-download/1.0" and manifest.get("regime") != "DEV":
        raise ValueError("DEV schema is restricted to DEV")
    if schema == "inksurf-validation-http-download/1.0":
        if manifest.get("regime") != "VALIDATION":
            raise ValueError("validation schema requires VALIDATION regime")
        if manifest.get("freeze_state") != "frozen_before_ground_truth":
            raise ValueError("validation download requires frozen_before_ground_truth")
        if not manifest.get("method_source_sha256") or not manifest.get("validation_partition_id"):
            raise ValueError("validation download requires method hash and partition id")
        if int(manifest.get("ground_truth_reveal_count_before", -1)) != 0:
            raise ValueError("validation partition was already revealed")
    files = manifest.get("files") or []
    if not files:
        raise ValueError("files must be non-empty")
    destinations = [row.get("destination") for row in files]
    if any(not item for item in destinations) or len(destinations) != len(set(destinations)):
        raise ValueError("destinations must be non-empty and unique")
    allowed = set(manifest.get("allowed_hosts") or [])
    for row in files:
        if urllib.parse.urlparse(row["url"]).hostname not in allowed:
            raise ValueError(f"host is not allowlisted: {row['url']}")
        if int(row.get("size_bytes", 0)) <= 0:
            raise ValueError("every file needs a positive size_bytes")
    total = sum(int(row["size_bytes"]) for row in files)
    if total > int(manifest.get("max_total_bytes", 0)):
        raise RuntimeError(f"download plan exceeds cap: {total}")
    return total


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def report_destination(root: Path, destination: Path, portable: bool) -> str:
    if portable:
        return str(destination.resolve().relative_to(root.resolve())).replace("\\", "/")
    return str(destination.resolve())


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
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


def run(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_total = validate_manifest(manifest)
    allowed = set(manifest["allowed_hosts"])
    root_relative = manifest.get("project_root_relative")
    root = (
        (manifest_path.resolve().parent / root_relative).resolve()
        if root_relative is not None
        else manifest_path.resolve().parent.parent
    )
    if not (root / "pyproject.toml").is_file():
        raise ValueError(f"resolved project root has no pyproject.toml: {root}")
    output_root = root / manifest["output_root"]
    output_root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output_root).free < expected_total * 2:
        raise RuntimeError("insufficient disk margin")

    results = []
    portable = bool(manifest.get("portable_report_paths", False))
    for row in manifest["files"]:
        destination = output_root / row["destination"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_suffix(destination.suffix + ".partial")
        expected_size = int(row["size_bytes"])
        if destination.exists() and destination.stat().st_size == expected_size:
            status = "reused_existing"
        else:
            if partial.exists():
                partial.unlink()
            request = urllib.request.Request(row["url"], headers={"User-Agent": "InkSurf-bounded-download/1.0"})
            written = 0
            try:
                with urllib.request.urlopen(request, timeout=60) as source, partial.open("wb") as target:
                    final_host = urllib.parse.urlparse(source.geturl()).hostname
                    if final_host not in allowed:
                        raise ValueError(f"redirect host is not allowlisted: {final_host}")
                    while block := source.read(min(4 * 1024 * 1024, expected_size - written + 1)):
                        written += len(block)
                        if written > expected_size:
                            raise RuntimeError(f"remote object exceeds frozen size: {row['url']}")
                        target.write(block)
                    target.flush()
                    os.fsync(target.fileno())
                if written != expected_size:
                    raise RuntimeError(f"downloaded size mismatch: {written} != {expected_size}")
                os.replace(partial, destination)
            except BaseException:
                if partial.exists():
                    partial.unlink()
                raise
            status = "downloaded"
        digest = _sha256(destination)
        expected_hash = row.get("sha256")
        if expected_hash and digest != expected_hash:
            raise RuntimeError(f"SHA256 mismatch: {row['destination']}")
        results.append({
            "destination": report_destination(root, destination, portable),
            "url": row["url"],
            "size_bytes": expected_size,
            "sha256": digest,
            "status": "verified" if portable else status,
        })

    report = {
        "schema_version": manifest["schema_version"],
        "experiment_id": manifest["experiment_id"],
        "track": manifest["track"],
        "regime": manifest["regime"],
        "portable_report_paths": portable,
        "expected_bytes": expected_total,
        "verified_bytes": sum(row["size_bytes"] for row in results),
        "files": results,
    }
    if not portable:
        report["project_root"] = str(root)
    _atomic_json(root / manifest["report_json"], report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.manifest), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
