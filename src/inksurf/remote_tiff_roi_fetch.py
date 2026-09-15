"""Fetch and decode only planned TIFF tiles for bounded DEV ROIs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .evidence_consistency import _atomic_json, _atomic_npz


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_roi(
    tiles: dict[int, np.ndarray],
    bounds: tuple[int, int, int, int],
    image_shape_yx: tuple[int, int],
    tile_shape_yx: tuple[int, int],
) -> np.ndarray:
    y0, y1, x0, x1 = bounds
    tile_height, tile_width = tile_shape_yx
    tiles_across = (image_shape_yx[1] + tile_width - 1) // tile_width
    output = np.zeros((y1 - y0, x1 - x0), dtype=next(iter(tiles.values())).dtype)
    for index, tile in tiles.items():
        tile_row, tile_column = divmod(index, tiles_across)
        ty0, tx0 = tile_row * tile_height, tile_column * tile_width
        ty1, tx1 = ty0 + tile.shape[0], tx0 + tile.shape[1]
        oy0, oy1 = max(y0, ty0), min(y1, ty1)
        ox0, ox1 = max(x0, tx0), min(x1, tx1)
        if oy0 >= oy1 or ox0 >= ox1:
            continue
        output[oy0-y0:oy1-y0, ox0-x0:ox1-x0] = tile[oy0-ty0:oy1-ty0, ox0-tx0:ox1-tx0]
    return output


def run(config_path: Path) -> dict:
    import fsspec
    import requests
    import tifffile

    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-remote-tiff-roi-fetch/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("remote TIFF fetching is Track A DEV only")
    root = config_path.resolve().parent.parent
    plan_path = root / config["plan_report"]
    if _sha256(plan_path) != config["plan_sha256"]:
        raise ValueError("TIFF plan hash mismatch")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan["planned_compressed_bytes"] > int(config["maximum_download_bytes"]):
        raise RuntimeError("plan exceeds download budget")
    outputs = []
    downloaded = 0
    for artifact in plan["artifacts"]:
        with fsspec.open(artifact["url"], mode="rb", block_size=65536, cache_type="readahead").open() as stream:
            with tifffile.TiffFile(stream) as tif:
                page = tif.pages[0]
                tiles = {}
                for item in artifact["byte_ranges"]:
                    start = int(item["offset"])
                    length = int(item["length"])
                    response = requests.get(
                        artifact["url"],
                        headers={"Range": f"bytes={start}-{start + length - 1}", "If-Match": f'"{artifact["etag"]}"'},
                        timeout=30,
                    )
                    if response.status_code != 206 or len(response.content) != length:
                        raise RuntimeError("server did not return the frozen TIFF byte range")
                    decoded = page.decode(response.content, int(item["tile_index"]))[0]
                    tile = np.asarray(decoded).squeeze()
                    if tile.ndim != 2:
                        raise ValueError("decoded TIFF tile is not 2D")
                    tiles[int(item["tile_index"])] = tile
                    downloaded += length
                arrays = {
                    f"roi_{index:02d}": extract_roi(
                        tiles, tuple(bounds), tuple(artifact["shape_yx"]), tuple(artifact["tile_shape_yx"])
                    )
                    for index, bounds in enumerate(artifact["mapped_rois_y0_y1_x0_x1"])
                }
        output_path = root / config["output_directory"] / f'{artifact["artifact_id"]}.npz'
        _atomic_npz(output_path, arrays)
        outputs.append({
            "artifact_id": artifact["artifact_id"],
            "output": str(output_path.relative_to(root)).replace("\\", "/"),
            "sha256": _sha256(output_path),
            "roi_count": len(arrays),
            "nonzero_fraction_by_roi": [float(np.count_nonzero(array) / array.size) for array in arrays.values()],
            "maximum_by_roi": [int(array.max()) for array in arrays.values()],
        })
    report = {
        "schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
        "track": "A", "regime": "DEV", "status": "bounded_tiles_decoded_registration_unverified",
        "downloaded_compressed_bytes": downloaded, "maximum_download_bytes": int(config["maximum_download_bytes"]),
        "outputs": outputs,
        "warning": "Decoded ROIs must not be compared until the cross-TIFXYZ registration audit passes.",
    }
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
