"""Download an exactly frozen set of DEV fragment volume layers with resume."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from inksurf.fragment_download import _atomic_json, _resolve_downloaded, _sha256
from inksurf.fragment_preflight import _find_kaggle


def select_layers(config: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if config.get("regime") != "DEV":
        raise ValueError("volume downloader is locked to DEV")
    start, stop = (int(value) for value in config["surface_volume_layers_inclusive"])
    if start < 0 or stop < start:
        raise ValueError("invalid inclusive layer range")
    fragment = str(config["fragment"]).rstrip("/")
    requested = [f"{fragment}/surface_volume/{layer:02d}.tif" for layer in range(start, stop + 1)]
    indexed = {item["name"]: item for item in manifest["files"]}
    try:
        selected = [indexed[name] for name in requested]
    except KeyError as exc:
        raise ValueError(f"layer absent from frozen manifest: {exc.args[0]}") from exc
    if len(selected) != int(config["surface_volume_file_count"]):
        raise ValueError("frozen layer count differs from generated selection")
    total = sum(int(item["bytes"]) for item in selected)
    if total != int(config["expected_bytes"]):
        raise ValueError("selected byte total differs from frozen expectation")
    if total > int(config["max_download_bytes"]):
        raise ValueError("selected layers exceed max_download_bytes")
    return selected


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    manifest = json.loads((root / config["manifest"]).read_text(encoding="utf-8"))
    if manifest.get("competition") != config["competition"]:
        raise ValueError("competition differs between config and manifest")
    selected = select_layers(config, manifest)
    output_dir = root / config["output_directory"]
    output_dir.mkdir(parents=True, exist_ok=True)
    total = sum(int(item["bytes"]) for item in selected)
    free = shutil.disk_usage(output_dir).free
    if free - total < int(config["minimum_free_bytes_after_download"]):
        raise RuntimeError("insufficient disk space for frozen safety margin")
    kaggle = _find_kaggle(root)
    if kaggle is None:
        raise RuntimeError("Kaggle CLI is missing")
    report_path = root / config["output_report"]
    verified: list[dict[str, Any]] = []

    for index, item in enumerate(selected, start=1):
        name = item["name"]
        destination = output_dir / Path(name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            with tempfile.TemporaryDirectory(prefix=f"layer_{index:02d}_", dir=output_dir) as temporary:
                temporary_dir = Path(temporary)
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
        verified.append({"name": name, "bytes": destination.stat().st_size, "sha256": _sha256(destination)})
        progress = {
            "experiment_id": config["experiment_id"],
            "fragment": config["fragment"],
            "regime": "DEV",
            "status": "downloading" if index < len(selected) else "dev_volume_pilot_downloaded_and_verified",
            "expected_bytes": total,
            "verified_bytes": sum(int(entry["bytes"]) for entry in verified),
            "verified_files": verified,
            "validation_files_accessed": 0,
        }
        _atomic_json(report_path, progress)
        print(f"verified {index}/{len(selected)} {name}", flush=True)
    return progress


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
