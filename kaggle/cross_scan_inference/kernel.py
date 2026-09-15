"""Frozen dual-acquisition DEV inference for the PHerc0139 cross-scan pilot."""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import requests
import torch
import torch.nn.functional as F

WORK = Path("/kaggle/working")
ASSETS = Path("/kaggle/temp/inksurf_assets")
LOADER = ASSETS / "villa_inference"
KAGGLE_INPUT = Path("/kaggle/input")
VILLA_COMMIT = "76370e1a6908f0bc2eb7f92bc0397336ecbe3d96"
CKPT_URL = "https://huggingface.co/scrollprize/ink_canonical_2um/resolve/075855bc69317ef6febf39a0d9d687b27d2b7c29/r152_3ddec_v2_l5_epoch13.ckpt"
EXPECTED = {
    "checkpoint": "36dd0de84b7b7aa6590184192c7415466cd8a1ba7c1e59f42c6373846373c3e0",
    "model": "7b2b2cfc6c7fb963a3da1bf128543ceadf8ad887f32a319bc0a38fb378f9e2ca",
    "resnet": "2b49ac430d77bae189cf002ed9c2748f940a6cd92b809a23db6f7dba381afbf6",
    "nonlocal": "09910c134003051b0cb75bd1ede1c2da8bab7cc60bf56997ace018018a806ce5",
    "20250820105138": "71a636abe4f2717257e8f686ab88e6183014bc33c093cf9866bf6a153549879c",
    "20260319133554": "bf54383a694c3594ed742e695b99d6b0af480e679c1b0f7555c0a577f3302fd5",
}


def digest(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def download(url, path, expected_hash):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and digest(path) == expected_hash:
        return
    partial = path.with_suffix(path.suffix + ".partial")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with open(partial, "wb") as handle:
            for block in response.iter_content(4 * 1024 * 1024):
                if block:
                    handle.write(block)
    os.replace(partial, path)
    if digest(path) != expected_hash:
        raise RuntimeError("SHA256 mismatch: " + str(path))


def infer(model, stack, device):
    stack = np.ascontiguousarray(np.clip(stack[24:86][::-1], 0, 200))
    positions = [(y, x) for y in (0, 128, 256) for x in (0, 128, 256)]
    window = np.outer(np.hanning(256), np.hanning(256)).astype(np.float32)
    window /= window.sum()
    prediction_sum = np.zeros((512, 512), np.float32)
    weight_sum = np.zeros((512, 512), np.float32)
    timings = []
    with torch.inference_mode():
        for y, x in positions:
            before = time.monotonic()
            volume = stack[:, y:y + 256, x:x + 256]
            valid = np.any(volume != 0, axis=0).astype(np.float32)
            tensor = torch.from_numpy(volume.astype(np.float32) / 200.0)[None, None].to(device)
            with torch.autocast(device_type="cuda", enabled=True):
                logits = model.forward(tensor)
            probability = torch.sigmoid(logits)
            probability = F.interpolate(
                probability.float(), size=(256, 256), mode="bilinear", align_corners=False
            )[0, 0].cpu().numpy()
            prediction_sum[y:y + 256, x:x + 256] += probability * window * valid
            weight_sum[y:y + 256, x:x + 256] += window * valid
            timings.append(time.monotonic() - before)
    return prediction_sum / np.clip(weight_sum, 1e-12, None), weight_sum, timings


started = time.monotonic()
if not torch.cuda.is_available():
    raise RuntimeError("GPU was requested but is unavailable")
device = torch.device("cuda")
checkpoint = ASSETS / "r152_3ddec_v2_l5_epoch13.ckpt"
download(CKPT_URL, checkpoint, EXPECTED["checkpoint"])
for relative, key in (
    ("model_resnet3d_3d_decoder.py", "model"),
    ("models/resnetall.py", "resnet"),
    ("models/non_local_helper.py", "nonlocal"),
):
    download(
        f"https://raw.githubusercontent.com/ScrollPrize/villa/{VILLA_COMMIT}/ink-detection/optimized_inference/{relative}",
        LOADER / relative,
        EXPECTED[key],
    )
(LOADER / "models" / "__init__.py").touch()
sys.path.insert(0, str(LOADER))
from model_resnet3d_3d_decoder import load_model

model = load_model(str(checkpoint), device, num_frames=62)
results = []
for volume_id in ("20250820105138", "20260319133554"):
    matches = list(KAGGLE_INPUT.glob(f"**/{volume_id}.npy"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one mounted input for {volume_id}, found {matches}")
    input_path = matches[0]
    if digest(input_path) != EXPECTED[volume_id]:
        raise RuntimeError("input SHA256 mismatch: " + volume_id)
    stack = np.load(input_path, allow_pickle=False)
    if stack.shape != (109, 512, 512) or stack.dtype != np.uint8:
        raise RuntimeError(f"invalid input {volume_id}: {stack.shape} {stack.dtype}")
    prediction, weights, timings = infer(model, stack, device)
    output_path = WORK / f"prediction_{volume_id}.npz"
    np.savez_compressed(output_path, prediction=prediction, weight_sum=weights)
    results.append({
        "volume_id": volume_id,
        "independence_group": f"acquisition-{volume_id}",
        "input_sha256": EXPECTED[volume_id],
        "output_sha256": digest(output_path),
        "tiles": len(timings),
        "tile_seconds": timings,
        "prediction_min": float(prediction.min()),
        "prediction_max": float(prediction.max()),
        "prediction_mean": float(prediction.mean()),
        "valid_fraction": float((weights > 0).mean()),
    })

report = {
    "schema_version": "inksurf-cross-scan-inference/1.0",
    "experiment_id": "pherc0139-cross-scan-inference-dev-20260915",
    "track": "A",
    "regime": "DEV",
    "geometry_tier": "G2",
    "status": "complete",
    "device": torch.cuda.get_device_name(0),
    "layers": [24, 86],
    "reverse_layers": True,
    "tile_size": 256,
    "stride": 128,
    "max_clip_value": 200,
    "checkpoint_sha256": EXPECTED["checkpoint"],
    "villa_commit": VILLA_COMMIT,
    "results": results,
    "elapsed_seconds": time.monotonic() - started,
    "interpretation": "Cross-acquisition repeatability pilot only; no ink or letter claim. Shared model errors remain a dependency.",
}
with open(WORK / "dual_inference_report.json", "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2, sort_keys=True)
    handle.write("\n")
print(json.dumps(report, indent=2, sort_keys=True), flush=True)
