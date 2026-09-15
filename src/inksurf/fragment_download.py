"""Bounded, manifest-verified Kaggle download for a preassigned DEV fragment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from inksurf.fragment_preflight import _find_kaggle


def select_files(config: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if config.get("regime") != "DEV":
        raise ValueError("fragment downloader is locked to DEV")
    fragment = str(config["fragment"]).rstrip("/") + "/"
    requested = list(config["files"])
    if not requested or len(requested) != len(set(requested)):
        raise ValueError("requested file list must be non-empty and unique")
    indexed = {item["name"]: item for item in manifest["files"]}
    selected = []
    for name in requested:
        if not name.startswith(fragment):
            raise ValueError(f"file is outside frozen DEV fragment: {name}")
        if "/surface_volume/" in name:
            raise ValueError("volume layers require a separate heavy-download authorization")
        if name not in indexed:
            raise ValueError(f"file is absent from frozen manifest: {name}")
        if indexed[name].get("bytes") is None:
            raise ValueError(f"file has unknown size: {name}")
        selected.append(indexed[name])
    total = sum(int(item["bytes"]) for item in selected)
    if total > int(config["max_bytes"]):
        raise ValueError(f"selected files exceed max_bytes: {total}")
    return selected


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_downloaded(temporary_dir: Path, name: str, expected_size: int) -> Path:
    exact = temporary_dir / Path(name)
    basename = Path(name).name
    direct_matches = [path for path in [exact, temporary_dir / basename] if path.is_file()]
    if len({path.resolve() for path in direct_matches}) == 1:
        return direct_matches[0]
    if len({path.resolve() for path in direct_matches}) > 1:
        raise RuntimeError(f"ambiguous direct download for {name}")

    archives = list(temporary_dir.rglob(basename + ".zip"))
    if len(archives) != 1:
        raise RuntimeError(f"downloaded path could not be resolved for {name}")
    with zipfile.ZipFile(archives[0]) as archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        if len(members) != 1 or Path(members[0].filename).name != basename:
            raise RuntimeError(f"unexpected archive content for {name}")
        if members[0].file_size != expected_size:
            raise RuntimeError(f"uncompressed-size mismatch for {name}")
        expanded = temporary_dir / ("expanded_" + basename)
        with archive.open(members[0]) as source, expanded.open("wb") as destination:
            shutil.copyfileobj(source, destination)
    return expanded


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
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


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    manifest = json.loads((root / config["manifest"]).read_text(encoding="utf-8"))
    if manifest.get("competition") != config["competition"]:
        raise ValueError("competition differs between config and manifest")
    selected = select_files(config, manifest)
    total = sum(int(item["bytes"]) for item in selected)
    output_dir = root / config["output_directory"]
    output_dir.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(output_dir).free
    required_free = int(config["minimum_free_bytes_after_download"])
    if free - total < required_free:
        raise RuntimeError("insufficient disk space for frozen safety margin")
    kaggle = _find_kaggle(root)
    if kaggle is None:
        raise RuntimeError("Kaggle CLI is missing")

    downloaded = []
    with tempfile.TemporaryDirectory(prefix="fragment_assets_", dir=output_dir) as temporary:
        temporary_dir = Path(temporary)
        for item in selected:
            name = item["name"]
            destination = output_dir / Path(name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                command = [
                    str(kaggle), "competitions", "download", config["competition"],
                    "--file", name, "--path", str(temporary_dir), "--quiet",
                ]
                completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
                if completed.returncode != 0:
                    raise RuntimeError(f"Kaggle download failed for {name}; output deliberately suppressed")
                source = _resolve_downloaded(temporary_dir, name, int(item["bytes"]))
                if source.stat().st_size != int(item["bytes"]):
                    raise RuntimeError(f"remote-size mismatch for {name}")
                os.replace(source, destination)
            if destination.stat().st_size != int(item["bytes"]):
                raise RuntimeError(f"local-size mismatch for {name}")
            downloaded.append(
                {"name": name, "bytes": destination.stat().st_size, "sha256": _sha256(destination)}
            )

    report = {
        "experiment_id": config["experiment_id"],
        "competition": config["competition"],
        "fragment": config["fragment"],
        "regime": "DEV",
        "status": "dev_assets_downloaded_and_verified",
        "downloaded_bytes": total,
        "minimum_free_bytes_after_download": required_free,
        "files": downloaded,
        "warning": "IR and labels are DEV-only. No surface-volume or VALIDATION file was downloaded.",
    }
    _atomic_json(root / config["output_report"], report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
