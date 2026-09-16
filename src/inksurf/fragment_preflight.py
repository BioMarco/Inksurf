"""List Kaggle fragment-benchmark metadata without downloading competition data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
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


def _find_kaggle(root: Path) -> Path | None:
    local = root / ".venv" / "Scripts" / "kaggle.exe"
    if local.is_file():
        return local
    discovered = shutil.which("kaggle")
    return Path(discovered) if discovered else None


def normalize_files(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        candidates = payload.get("files", payload.get("items"))
    else:
        candidates = payload
    if not isinstance(candidates, list):
        raise ValueError("Kaggle file listing is not a list")
    normalized = []
    for item in candidates:
        if not isinstance(item, dict):
            raise ValueError("Kaggle file entry is not an object")
        name = item.get("name") or item.get("ref") or item.get("fileName")
        size = item.get("totalBytes", item.get("size", item.get("bytes")))
        if not isinstance(name, str) or not name:
            raise ValueError("Kaggle file entry has no name")
        normalized.append(
            {
                "name": name,
                "bytes": int(size) if size is not None else None,
                "creation_date": item.get("creationDate") or item.get("dateCreated"),
            }
        )
    return sorted(normalized, key=lambda item: item["name"])


def parse_cli_output(text: str) -> tuple[Any, str | None]:
    """Separate Kaggle's pagination header from its JSON payload."""
    stripped = text.strip()
    next_token = None
    prefix = "Next Page Token = "
    if stripped.startswith(prefix):
        header, separator, stripped = stripped.partition("\n")
        if not separator:
            raise ValueError("Kaggle listing has a page token but no JSON payload")
        next_token = header[len(prefix) :].strip()
        if not next_token:
            raise ValueError("Kaggle listing has an empty page token")
    if not stripped or stripped[0] not in "[{":
        raise ValueError("Kaggle listing contains no JSON payload")
    return json.loads(stripped), next_token


def run(config_path: Path) -> tuple[dict[str, Any], bool]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    output_report = root / config["outputs"]["report_json"]
    output_manifest = root / config["outputs"]["manifest_json"]
    executable = _find_kaggle(root)
    base = {
        "experiment_id": config["experiment_id"],
        "competition": config["competition"],
        "operation": "metadata_listing_only",
        "downloaded_bytes": 0,
        "regime": "VALIDATION_PREACCESS",
    }
    if executable is None:
        report = {
            **base,
            "status": "blocked_cli_missing",
            "next_action": "Install the optional fragment dependency, then authenticate Kaggle locally.",
        }
        _atomic_json(output_report, report)
        return report, False

    files_by_name: dict[str, dict[str, Any]] = {}
    next_token = None
    pages = 0
    max_pages = int(config.get("max_pages", 10))
    seen_tokens: set[str] = set()
    while pages < max_pages:
        command = [
            str(executable),
            "competitions",
            "files",
            config["competition"],
            "--page-size",
            str(int(config["page_size"])),
            "--format",
            "json",
        ]
        if next_token is not None:
            command.extend(["--page-token", next_token])
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            report = {
                **base,
                "status": "blocked_auth_or_rules",
                "kaggle_cli": str(executable.relative_to(root)) if executable.is_relative_to(root) else str(executable),
                "return_code": completed.returncode,
                "pages_completed": pages,
                "next_action": "Run '.venv\\Scripts\\kaggle.exe auth login' and accept the competition rules in the browser.",
                "warning": "CLI error text is deliberately not persisted because it may contain authentication details.",
            }
            _atomic_json(output_report, report)
            return report, False
        payload, new_token = parse_cli_output(completed.stdout)
        for item in normalize_files(payload):
            previous = files_by_name.get(item["name"])
            if previous is not None and previous != item:
                raise ValueError(f"conflicting metadata for {item['name']}")
            files_by_name[item["name"]] = item
        pages += 1
        if new_token is None:
            next_token = None
            break
        if new_token in seen_tokens:
            raise RuntimeError("Kaggle returned a repeated page token")
        seen_tokens.add(new_token)
        next_token = new_token
    files = sorted(files_by_name.values(), key=lambda item: item["name"])
    manifest = {"competition": config["competition"], "files": files}
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    known_sizes = [item["bytes"] for item in files if item["bytes"] is not None]
    report = {
        **base,
        "status": "metadata_manifest_frozen",
        "file_count": len(files),
        "known_total_bytes": sum(known_sizes),
        "files_with_unknown_size": len(files) - len(known_sizes),
        "pages": pages,
        "manifest_sha256": hashlib.sha256(canonical).hexdigest(),
        "listing_may_be_truncated": next_token is not None,
        "next_action": "Review exact archive sizes and contents before authorizing any bounded download.",
    }
    _atomic_json(output_manifest, manifest)
    _atomic_json(output_report, report)
    return report, True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    report, success = run(args.config)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
