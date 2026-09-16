"""Reproduce a frozen published ink-map window with the canonical 3D model."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def grid_1d(length: int, tile: int, stride: int) -> list[int]:
    if length < tile or tile <= 0 or stride <= 0:
        raise ValueError("length must cover one positive tile and stride")
    positions = list(range(0, max(1, length - tile + 1), stride))
    end = length - tile
    if not positions or positions[-1] != end:
        positions.append(end)
    return positions


def hann2d(height: int, width: int) -> np.ndarray:
    weights = np.outer(np.hanning(height), np.hanning(width)).astype(np.float32)
    total = float(weights.sum())
    return weights / (total if total > 0 else 1.0)


def enforce_cpu_tile_guard(tile_count: int, allow_cpu_multitile: bool) -> None:
    if tile_count > 1 and not allow_cpu_multitile:
        raise RuntimeError(
            "multi-tile ResNet3D-152 CPU inference is disabled; use a GPU or set "
            "allow_cpu_multitile=true as an explicit operational override"
        )


def assemble_raw_window(cache_root: Path, volume_id: str, level: int,
                        shape: list[int], chunks: list[int], start: list[int],
                        size: list[int]) -> np.ndarray:
    shape_a = np.asarray(shape, dtype=np.int64)
    chunks_a = np.asarray(chunks, dtype=np.int64)
    start_a = np.asarray(start, dtype=np.int64)
    size_a = np.asarray(size, dtype=np.int64)
    stop_a = start_a + size_a
    if any(len(v) != 3 for v in (shape, chunks, start, size)) or np.any(start_a < 0) or np.any(stop_a > shape_a):
        raise ValueError("invalid Z,Y,X window")
    output = np.zeros(tuple(int(v) for v in size_a), dtype=np.uint8)
    first = start_a // chunks_a
    last = (stop_a - 1) // chunks_a
    for cz in range(int(first[0]), int(last[0]) + 1):
        for cy in range(int(first[1]), int(last[1]) + 1):
            for cx in range(int(first[2]), int(last[2]) + 1):
                index = np.asarray([cz, cy, cx], dtype=np.int64)
                chunk_start = index * chunks_a
                chunk_stop = np.minimum(chunk_start + chunks_a, shape_a)
                chunk_shape = tuple(int(v) for v in chunk_stop - chunk_start)
                path = cache_root / volume_id / str(level) / str(cz) / str(cy) / str(cx)
                if not path.exists():
                    raise FileNotFoundError(path)
                raw = np.fromfile(path, dtype=np.uint8)
                expected = int(np.prod(chunk_shape))
                if raw.size != expected:
                    raise RuntimeError(f"raw chunk size mismatch for {path}: {raw.size} != {expected}")
                chunk = raw.reshape(chunk_shape)
                overlap_start = np.maximum(chunk_start, start_a)
                overlap_stop = np.minimum(chunk_stop, stop_a)
                source = tuple(slice(int(overlap_start[i] - chunk_start[i]), int(overlap_stop[i] - chunk_start[i])) for i in range(3))
                target = tuple(slice(int(overlap_start[i] - start_a[i]), int(overlap_stop[i] - start_a[i])) for i in range(3))
                output[target] = chunk[source]
    return output


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def _atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def run(config_path: Path) -> dict[str, Any]:
    started = time.monotonic()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "inksurf-ink-model-compatibility/1.0":
        raise ValueError("unsupported schema_version")
    if config.get("track") != "A" or config.get("regime") != "DEV":
        raise ValueError("compatibility run must be Track A / DEV")
    root = config_path.resolve().parent.parent
    surface = config["surface"]
    checkpoint = root / config["checkpoint"]["path"]
    published_path = root / config["published_map"]["path"]
    loader_root = root / config["loader"]["root"]
    integrity = {
        "checkpoint": sha256(checkpoint),
        "published_map": sha256(published_path),
        "model_loader": sha256(loader_root / "model_resnet3d_3d_decoder.py"),
        "resnetall": sha256(loader_root / "models" / "resnetall.py"),
        "non_local_helper": sha256(loader_root / "models" / "non_local_helper.py"),
    }
    expected = {
        "checkpoint": config["checkpoint"]["sha256"],
        "published_map": config["published_map"]["sha256"],
        "model_loader": config["loader"]["model_loader_sha256"],
        "resnetall": config["loader"]["resnetall_sha256"],
        "non_local_helper": config["loader"]["non_local_helper_sha256"],
    }
    if integrity != expected:
        raise RuntimeError(f"asset integrity mismatch: {integrity}")

    stack = assemble_raw_window(root / surface["cache_root"], surface["volume_id"],
                                int(surface["level"]), surface["shape_zyx"],
                                surface["chunks_zyx"], surface["start_zyx"], surface["size_zyx"])
    inference = config["inference"]
    stack = stack[int(inference["layer_start"]):int(inference["layer_end"])]
    if bool(inference["reverse_layers"]):
        stack = stack[::-1]
    stack = np.ascontiguousarray(np.clip(stack, 0, int(inference["max_clip_value"])))

    import tifffile
    import zarr
    store = tifffile.imread(published_path, aszarr=True)
    try:
        published_zarr = zarr.open(store, mode="r")
        wy, wx, wh, ww = [int(v) for v in config["published_map"]["window_yx"]]
        published = np.asarray(published_zarr[wy:wy + wh, wx:wx + ww], dtype=np.uint8)
    finally:
        store.close()

    height, width = stack.shape[1:]
    tile = int(inference["tile_size"]); stride = int(inference["stride"])
    positions = [(y, x) for y in grid_1d(height, tile, stride) for x in grid_1d(width, tile, stride)]
    enforce_cpu_tile_guard(len(positions), bool(inference.get("allow_cpu_multitile", False)))

    import torch
    import torch.nn.functional as functional
    torch.set_num_threads(int(inference["cpu_threads"]))
    sys.path.insert(0, str(loader_root))
    try:
        loader_module = importlib.import_module("model_resnet3d_3d_decoder")
        device = torch.device("cpu")
        model = loader_module.load_model(str(checkpoint), device, num_frames=stack.shape[0])
    finally:
        if sys.path[0] == str(loader_root):
            sys.path.pop(0)

    weights = hann2d(tile, tile)
    prediction_sum = np.zeros((height, width), dtype=np.float32)
    weight_sum = np.zeros((height, width), dtype=np.float32)
    with torch.inference_mode():
        for y, x in positions:
            volume = stack[:, y:y + tile, x:x + tile]
            valid = np.any(volume != 0, axis=0).astype(np.float32)
            tensor = torch.from_numpy(volume.astype(np.float32) / float(inference["max_clip_value"]))[None, None]
            with torch.autocast(device_type="cpu", enabled=bool(inference["cpu_autocast"])):
                logits = model.forward(tensor)
            probability = torch.sigmoid(logits)
            probability = functional.interpolate(probability.float(), size=(tile, tile), mode="bilinear", align_corners=False)
            probability_np = probability[0, 0].cpu().numpy()
            prediction_sum[y:y + tile, x:x + tile] += probability_np * weights * valid
            weight_sum[y:y + tile, x:x + tile] += weights * valid
    prediction = prediction_sum / np.clip(weight_sum, 1e-12, None)
    y1, x1, y2, x2 = [int(v) for v in config["evaluation_crop_yxyx"]]
    local_eval = prediction[y1:y2, x1:x2].astype(np.float64)
    published_eval = published[y1:y2, x1:x2].astype(np.float64) / 255.0
    valid_eval = weight_sum[y1:y2, x1:x2] > 0
    pearson = float(np.corrcoef(local_eval[valid_eval], published_eval[valid_eval])[0, 1])
    from scipy.stats import spearmanr
    spearman = float(spearmanr(local_eval[valid_eval], published_eval[valid_eval]).statistic)
    threshold = float(config["acceptance_pearson_r_gt"])
    output_path = root / config["output_npz"]
    _atomic_npz(output_path, prediction=prediction, published=published, weight_sum=weight_sum)
    report = {
        "schema_version": config["schema_version"], "experiment_id": config["experiment_id"],
        "track": config["track"], "regime": config["regime"], "geometry_tier": config["geometry_tier"],
        "status": "pass" if pearson > threshold else "fail",
        "acceptance_pearson_r_gt": threshold, "pearson_r": pearson, "spearman_rho": spearman,
        "evaluation_pixels": int(valid_eval.sum()), "tiles": len(positions), "layers": int(stack.shape[0]),
        "reverse_layers": bool(inference["reverse_layers"]), "device": "cpu",
        "cpu_autocast": bool(inference["cpu_autocast"]), "elapsed_seconds": time.monotonic() - started,
        "asset_sha256": integrity, "villa_commit": config["loader"]["villa_commit"],
        "output_npz": config["output_npz"],
        "interpretation": "Pipeline compatibility only; this is not a new ink claim."
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
