"""Build a bounded, metadata-only manifest for a labelled InkSurf benchmark."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class RemoteFile:
    path: str
    size: int
    xet_hash: str
    uploaded_at: str | None = None


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


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def hf_bucket_lister(bucket_id: str, prefix: str) -> Iterable[RemoteFile]:
    """List direct files through the official client without downloading content."""
    try:
        from huggingface_hub import list_bucket_tree
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("install the optional dependency with: pip install '.[catalog]'") from exc
    for item in list_bucket_tree(bucket_id, prefix=prefix, recursive=False):
        if item.type == "file":
            yield RemoteFile(
                path=item.path,
                size=int(item.size),
                xet_hash=str(item.xet_hash),
                uploaded_at=_iso(getattr(item, "uploaded_at", None)),
            )


def validate_config(config: dict[str, Any]) -> None:
    surfaces = config.get("surfaces", [])
    if not surfaces:
        raise ValueError("at least one surface is required")
    keys = [surface["key"] for surface in surfaces]
    if len(keys) != len(set(keys)):
        raise ValueError("surface keys must be unique")
    allowed = {"DEV", "VALIDATION"}
    for surface in surfaces:
        if surface["regime"] not in allowed:
            raise ValueError(f"invalid regime for {surface['key']}: {surface['regime']}")
        roles = surface.get("files", {})
        for required in ("prediction", "ink_labels", "supervision_mask"):
            if required not in roles:
                raise ValueError(f"{surface['key']} is missing required role {required}")
    external = [s for s in surfaces if s.get("external_domain")]
    if not external or any(s["regime"] != "VALIDATION" for s in external):
        raise ValueError("at least one external-domain surface must be locked to VALIDATION")


def build_manifest(
    config: dict[str, Any],
    *,
    lister: Callable[[str, str], Iterable[RemoteFile]] = hf_bucket_lister,
) -> dict[str, Any]:
    validate_config(config)
    bucket_id = config["bucket_id"]
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for surface in config["surfaces"]:
        by_parent: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for role, relative_path in surface["files"].items():
            path = f"{surface['prefix'].rstrip('/')}/{relative_path.lstrip('/')}"
            parent = path.rsplit("/", 1)[0]
            by_parent[parent].append((role, path))
        remote: dict[str, RemoteFile] = {}
        for parent in sorted(by_parent):
            remote.update({item.path: item for item in lister(bucket_id, parent)})
        for role, relative_path in surface["files"].items():
            path = f"{surface['prefix'].rstrip('/')}/{relative_path.lstrip('/')}"
            item = remote.get(path)
            if item is None:
                errors.append(f"{surface['key']}:{role}: missing {path}")
                continue
            rows.append(
                {
                    "surface_key": surface["key"],
                    "scroll_id": surface["scroll_id"],
                    "regime": surface["regime"],
                    "external_domain": bool(surface.get("external_domain", False)),
                    "stage": "A1" if role in {"prediction", "ink_labels", "supervision_mask"} else "A2",
                    "role": role,
                    "path": item.path,
                    "size_bytes": item.size,
                    "xet_hash": item.xet_hash,
                    "uploaded_at": item.uploaded_at,
                }
            )
    if errors:
        raise RuntimeError("benchmark manifest is incomplete: " + "; ".join(errors))

    summaries: dict[str, dict[str, int]] = {}
    for surface in config["surfaces"]:
        selected = [row for row in rows if row["surface_key"] == surface["key"]]
        summaries[surface["key"]] = {
            "a1_files": sum(row["stage"] == "A1" for row in selected),
            "a1_bytes": sum(row["size_bytes"] for row in selected if row["stage"] == "A1"),
            "a2_geometry_files": sum(row["stage"] == "A2" for row in selected),
            "a2_geometry_bytes": sum(row["size_bytes"] for row in selected if row["stage"] == "A2"),
        }
    dev_bytes = sum(row["size_bytes"] for row in rows if row["stage"] == "A1" and row["regime"] == "DEV")
    validation_bytes = sum(
        row["size_bytes"] for row in rows if row["stage"] == "A1" and row["regime"] == "VALIDATION"
    )
    manifest = {
        "experiment_id": config["experiment_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "metadata_verified_download_not_started",
        "bucket_id": bucket_id,
        "dataset_url": config["dataset_url"],
        "annotation_semantics": config["annotation_semantics"],
        "split_policy": config["split_policy"],
        "evaluation": config["evaluation"],
        "budget": {
            "a1_dev_bytes": dev_bytes,
            "a1_validation_locked_bytes": validation_bytes,
            "a1_total_bytes": dev_bytes + validation_bytes,
            "downloaded_bytes": 0,
        },
        "surfaces": summaries,
        "files": rows,
    }
    snapshot = {
        "experiment_id": manifest["experiment_id"],
        "bucket_id": manifest["bucket_id"],
        "annotation_semantics": manifest["annotation_semantics"],
        "split_policy": manifest["split_policy"],
        "evaluation": manifest["evaluation"],
        "budget": manifest["budget"],
        "surfaces": manifest["surfaces"],
        "files": manifest["files"],
    }
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["snapshot_sha256"] = hashlib.sha256(canonical).hexdigest()
    return manifest


def write_outputs(config_path: Path, manifest: dict[str, Any]) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    output_dir = root / config["outputs"]["directory"]
    _atomic_write(
        output_dir / config["outputs"]["manifest_json"],
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    )
    fields = [
        "surface_key", "scroll_id", "regime", "external_domain", "stage", "role",
        "path", "size_bytes", "xet_hash", "uploaded_at",
    ]
    from io import StringIO
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows({key: row[key] for key in fields} for row in manifest["files"])
    _atomic_write(output_dir / config["outputs"]["files_csv"], stream.getvalue())


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    manifest = build_manifest(config)
    write_outputs(config_path, manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
