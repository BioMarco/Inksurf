"""Audit bounded Zarr metadata for candidate cross-volume surface pairs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Callable


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


def fetch_json(url: str, max_bytes: int) -> tuple[dict[str, Any], int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "InkSurf-surface-audit/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        declared = response.headers.get("Content-Length")
        if declared is not None and int(declared) > max_bytes:
            raise RuntimeError(f"metadata object exceeds max_bytes: {declared} > {max_bytes}")
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise RuntimeError(f"metadata object exceeds max_bytes: > {max_bytes}")
    return json.loads(payload), len(payload), hashlib.sha256(payload).hexdigest()


def _http_url(s3_url: str) -> str:
    prefix = "s3://vesuvius-challenge-open-data/"
    if not s3_url.startswith(prefix):
        raise ValueError(f"unsupported artifact URL: {s3_url}")
    return s3_url.replace(
        prefix,
        "https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/",
        1,
    )


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "inksurf-surface-artifact-audit/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("surface artifact audit must be Track A / DEV")
    if int(config.get("max_bytes_per_object", 0)) <= 0:
        raise ValueError("max_bytes_per_object must be positive")


def audit(
    config_path: Path,
    fetcher: Callable[[str, int], tuple[dict[str, Any], int, str]] = fetch_json,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    root = config_path.resolve().parent.parent
    source_path = root / config["artifact_pairs_csv"]
    source_bytes = source_path.read_bytes()
    pairs = list(csv.DictReader(source_bytes.decode("utf-8").splitlines()))
    limit = int(config["max_bytes_per_object"])
    cache: dict[str, dict[str, Any]] = {}
    bytes_read = 0

    for pair in pairs:
        for side in ("a", "b"):
            s3_url = pair[f"layers_{side}"]
            if s3_url in cache:
                continue
            base = _http_url(s3_url)
            attrs, attrs_bytes, attrs_hash = fetcher(base + ".zattrs", limit)
            zarray, array_bytes, array_hash = fetcher(base + "0/.zarray", limit)
            bytes_read += attrs_bytes + array_bytes
            datasets = attrs.get("multiscales", [{}])[0].get("datasets", [])
            level_zero = next((item for item in datasets if str(item.get("path")) == "0"), {})
            transforms = level_zero.get("coordinateTransformations", [])
            scale = next((item.get("scale") for item in transforms if item.get("type") == "scale"), None)
            translation = next(
                (item.get("translation") for item in transforms if item.get("type") == "translation"),
                None,
            )
            axes = [item.get("name") for item in attrs.get("multiscales", [{}])[0].get("axes", [])]
            shape = list(zarray.get("shape") or [])
            cache[s3_url] = {
                "axes": axes,
                "shape": shape,
                "chunks": list(zarray.get("chunks") or []),
                "dtype": zarray.get("dtype"),
                "scale_um": scale,
                "translation_um": translation,
                "physical_extent_um": [round(float(n) * float(s), 6) for n, s in zip(shape, scale or [])],
                "attrs_sha256": attrs_hash,
                "zarray_sha256": array_hash,
            }

    output_rows: list[dict[str, Any]] = []
    for pair in pairs:
        first, second = cache[pair["layers_a"]], cache[pair["layers_b"]]
        axes_match = first["axes"] == second["axes"] == ["z", "y", "x"]
        extent_ratios = [
            min(a, b) / max(a, b) if max(a, b) else 0.0
            for a, b in zip(first["physical_extent_um"], second["physical_extent_um"])
        ]
        local_zero_translations = first["translation_um"] == second["translation_um"] == [0.0, 0.0, 0.0]
        output_rows.append({
            "sample_id": pair["sample_id"],
            "label": pair["label"],
            "segment_a": pair["segment_a"],
            "segment_b": pair["segment_b"],
            "axes_match_zyx": axes_match,
            "shape_a": json.dumps(first["shape"]),
            "shape_b": json.dumps(second["shape"]),
            "scale_a_um": json.dumps(first["scale_um"]),
            "scale_b_um": json.dumps(second["scale_um"]),
            "physical_extent_a_um": json.dumps(first["physical_extent_um"]),
            "physical_extent_b_um": json.dumps(second["physical_extent_um"]),
            "extent_ratio_z": round(extent_ratios[0], 6),
            "extent_ratio_y": round(extent_ratios[1], 6),
            "extent_ratio_x": round(extent_ratios[2], 6),
            "local_zero_translations": local_zero_translations,
            "global_transform_present": False,
            "verdict": "plausible_partial_overlap_transform_missing",
        })

    report = {
        "schema_version": config["schema_version"],
        "experiment_id": config["experiment_id"],
        "track": config["track"],
        "regime": config["regime"],
        "status": "conditional_go_transform_required" if output_rows else "no_go_no_pairs",
        "artifact_pairs": len(output_rows),
        "artifact_pairs_csv_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "metadata_objects_read": len(cache) * 2,
        "metadata_bytes_read": bytes_read,
        "volumetric_chunk_bytes_read": 0,
        "global_transforms_found": 0,
        "claim": (
            "Physical extents make partial overlap plausible, but local Zarr scale and zero "
            "translation do not define cross-scan registration."
        ),
        "sources": cache,
    }
    outputs = config["outputs"]
    _atomic_write(root / outputs["report_json"], json.dumps(report, indent=2, sort_keys=True) + "\n")
    fields = list(output_rows[0]) if output_rows else ["sample_id", "label", "verdict"]
    from io import StringIO
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(output_rows)
    _atomic_write(root / outputs["pairs_csv"], stream.getvalue())
    return report, output_rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    report, _ = audit(args.config)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
