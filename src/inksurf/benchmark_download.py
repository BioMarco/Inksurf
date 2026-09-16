"""Download an exact, budgeted subset of a frozen InkSurf benchmark manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def select_downloads(
    manifest: dict[str, Any],
    *,
    regime: str,
    stage: str,
    max_bytes: int,
    unlock_validation: bool = False,
) -> list[dict[str, Any]]:
    if regime == "VALIDATION" and not unlock_validation:
        raise PermissionError("VALIDATION is locked; freeze the DEV implementation before using --unlock-validation")
    if regime not in {"DEV", "VALIDATION"}:
        raise ValueError(f"unsupported regime: {regime}")
    rows = [row for row in manifest["files"] if row["regime"] == regime and row["stage"] == stage]
    if not rows:
        raise ValueError(f"manifest has no {regime}/{stage} files")
    total = sum(int(row["size_bytes"]) for row in rows)
    if total > max_bytes:
        raise RuntimeError(f"download plan exceeds cap: {total} > {max_bytes}")
    return rows


def sha256_file(path: Path, block_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
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


def run(
    manifest_path: Path,
    *,
    output_dir: Path,
    report_path: Path,
    regime: str,
    stage: str,
    max_bytes: int,
    unlock_validation: bool = False,
) -> dict[str, Any]:
    try:
        from huggingface_hub import download_bucket_files, list_bucket_tree
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("install the optional dependency with: pip install '.[catalog]'") from exc

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = select_downloads(
        manifest,
        regime=regime,
        stage=stage,
        max_bytes=max_bytes,
        unlock_validation=unlock_validation,
    )
    expected_total = sum(int(row["size_bytes"]) for row in rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(output_dir).free
    if free < expected_total * 2:
        raise RuntimeError(f"insufficient disk margin: free={free}, required={expected_total * 2}")

    remote_by_path: dict[str, Any] = {}
    parents = sorted({row["path"].rsplit("/", 1)[0] for row in rows})
    for parent in parents:
        for item in list_bucket_tree(manifest["bucket_id"], prefix=parent, recursive=False):
            if item.type == "file":
                remote_by_path[item.path] = item

    verified: list[tuple[dict[str, Any], Any]] = []
    for row in rows:
        item = remote_by_path.get(row["path"])
        if item is None:
            raise RuntimeError(f"remote file disappeared: {row['path']}")
        if int(item.size) != int(row["size_bytes"]) or str(item.xet_hash) != row["xet_hash"]:
            raise RuntimeError(f"remote object changed after freeze: {row['path']}")
        verified.append((row, item))

    local_rows: list[dict[str, Any]] = []
    for row, item in verified:
        suffix = Path(row["path"]).suffix or ".bin"
        destination = output_dir / row["surface_key"] / f"{row['role']}{suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_suffix(destination.suffix + ".partial")
        if destination.exists() and destination.stat().st_size == int(row["size_bytes"]):
            status = "reused_existing"
        else:
            if partial.exists():
                partial.unlink()
            download_bucket_files(
                manifest["bucket_id"],
                [(item, partial)],
                raise_on_missing_files=True,
                token=False,
            )
            if partial.stat().st_size != int(row["size_bytes"]):
                raise RuntimeError(f"downloaded size mismatch: {row['path']}")
            os.replace(partial, destination)
            status = "downloaded"
        local_rows.append(
            {
                "surface_key": row["surface_key"],
                "role": row["role"],
                "remote_path": row["path"],
                "remote_xet_hash": row["xet_hash"],
                "local_path": str(destination.resolve()),
                "size_bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "status": status,
            }
        )

    report = {
        "experiment_id": manifest["experiment_id"],
        "manifest_snapshot_sha256": manifest["snapshot_sha256"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "regime": regime,
        "stage": stage,
        "expected_bytes": expected_total,
        "downloaded_or_verified_bytes": sum(row["size_bytes"] for row in local_rows),
        "validation_unlocked": bool(unlock_validation),
        "files": local_rows,
    }
    _atomic_json(report_path, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--regime", choices=["DEV", "VALIDATION"], default="DEV")
    parser.add_argument("--stage", choices=["A1", "A2", "G2_CT"], default="A1")
    parser.add_argument("--max-bytes", type=int, required=True)
    parser.add_argument("--unlock-validation", action="store_true")
    args = parser.parse_args(argv)
    report = run(
        args.manifest,
        output_dir=args.output_dir,
        report_path=args.report,
        regime=args.regime,
        stage=args.stage,
        max_bytes=args.max_bytes,
        unlock_validation=args.unlock_validation,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
