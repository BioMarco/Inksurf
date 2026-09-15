"""Plan bounded HTTP byte ranges for tiled TIFF ROIs without reading pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from .evidence_consistency import _atomic_json


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def map_bounds(
    bounds_yx: tuple[int, int, int, int],
    source_shape_yx: tuple[int, int],
    target_shape_yx: tuple[int, int],
) -> tuple[int, int, int, int]:
    y0, y1, x0, x1 = bounds_yx
    sy, sx = source_shape_yx
    ty, tx = target_shape_yx
    if not (0 <= y0 < y1 <= sy and 0 <= x0 < x1 <= sx):
        raise ValueError("ROI bounds are outside the source canvas")
    return (
        math.floor(y0 * ty / sy), math.ceil(y1 * ty / sy),
        math.floor(x0 * tx / sx), math.ceil(x1 * tx / sx),
    )


def required_tile_indices(
    bounds: tuple[int, int, int, int],
    image_shape_yx: tuple[int, int],
    tile_shape_yx: tuple[int, int],
) -> set[int]:
    y0, y1, x0, x1 = bounds
    height, width = image_shape_yx
    tile_height, tile_width = tile_shape_yx
    if not (0 <= y0 < y1 <= height and 0 <= x0 < x1 <= width):
        raise ValueError("mapped bounds are outside the TIFF")
    tiles_across = math.ceil(width / tile_width)
    return {
        row * tiles_across + column
        for row in range(y0 // tile_height, (y1 - 1) // tile_height + 1)
        for column in range(x0 // tile_width, (x1 - 1) // tile_width + 1)
    }


def run(config_path: Path) -> dict:
    import fsspec
    import requests
    import tifffile

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-remote-tiff-roi-plan/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("remote TIFF planning is Track A DEV only")
    root = config_path.resolve().parent.parent
    chunk_path = root / config["chunk_audit_report"]
    if _sha256(chunk_path) != config["chunk_audit_sha256"]:
        raise ValueError("chunk audit report hash mismatch")
    chunks = json.loads(chunk_path.read_text(encoding="utf-8"))["chunks"]
    source_shape = tuple(map(int, config["source_canvas_shape_yx"]))
    scale = int(config["chunk_level_to_canvas_scale"])
    chunk_pixels = int(config["chunk_pixels"])
    source_rois = [
        (
            int(item["chunk_yx"][0]) * chunk_pixels * scale,
            (int(item["chunk_yx"][0]) + 1) * chunk_pixels * scale,
            int(item["chunk_yx"][1]) * chunk_pixels * scale,
            (int(item["chunk_yx"][1]) + 1) * chunk_pixels * scale,
        )
        for item in chunks
    ]
    artifacts = []
    for specification in config["artifacts"]:
        response = requests.head(specification["url"], allow_redirects=True, timeout=30)
        response.raise_for_status()
        size = int(response.headers["content-length"])
        etag = response.headers.get("etag", "").strip('"')
        if size != int(specification["size_bytes"]) or etag != specification["etag"]:
            raise ValueError("remote TIFF identity changed")
        if response.headers.get("accept-ranges", "").lower() != "bytes":
            raise ValueError("remote TIFF does not advertise byte ranges")
        with fsspec.open(specification["url"], mode="rb", block_size=65536, cache_type="readahead").open() as stream:
            with tifffile.TiffFile(stream) as tif:
                page = tif.pages[0]
                shape = tuple(map(int, page.shape))
                tile_shape = (int(page.tilelength), int(page.tilewidth))
                if not page.is_tiled or shape != tuple(specification["shape_yx"]):
                    raise ValueError("unexpected TIFF layout")
                indices: set[int] = set()
                mapped_rois = []
                for source_roi in source_rois:
                    mapped = map_bounds(source_roi, source_shape, shape)
                    mapped_rois.append(list(mapped))
                    indices.update(required_tile_indices(mapped, shape, tile_shape))
                ranges = [
                    {"tile_index": index, "offset": int(page.dataoffsets[index]), "length": int(page.databytecounts[index])}
                    for index in sorted(indices)
                ]
                artifacts.append({
                    "artifact_id": specification["artifact_id"], "url": specification["url"],
                    "size_bytes": size, "etag": etag, "shape_yx": list(shape),
                    "tile_shape_yx": list(tile_shape), "compression": page.compression.name,
                    "mapped_rois_y0_y1_x0_x1": mapped_rois,
                    "unique_tiles": len(ranges), "planned_compressed_bytes": sum(item["length"] for item in ranges),
                    "byte_ranges": ranges,
                })
    planned = sum(item["planned_compressed_bytes"] for item in artifacts)
    report = {
        "schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
        "track": "A", "regime": "DEV", "status": "tile_ranges_planned_registration_unverified",
        "source_canvas_shape_yx": list(source_shape), "roi_count": len(source_rois),
        "artifacts": artifacts, "planned_compressed_bytes": planned,
        "maximum_planned_bytes": int(config["maximum_planned_bytes"]),
        "within_budget": planned <= int(config["maximum_planned_bytes"]),
        "registration_warning": "Normalized canvas scaling is an I/O shortlist only; TIFXYZ registration must pass before pixel comparison.",
        "prediction_pixels_downloaded": 0,
    }
    if not report["within_budget"]:
        raise RuntimeError("planned TIFF tile bytes exceed budget")
    _atomic_json(root / config["output_report"], report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
