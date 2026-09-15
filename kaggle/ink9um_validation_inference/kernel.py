"""Pinned bounded inference for two correlated official ink_9um replicas."""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import requests
import torch
import torch.nn.functional as F

WORK = Path("/kaggle/working")
TEMP = Path("/kaggle/temp/inksurf_ink9um")
INPUT = Path("/kaggle/input")
VILLA_COMMIT = "3ea17f54a9b3d5fd1aaf73e1d2c8386dbaa9f30e"
MODELS = [
    ("seed42", "https://huggingface.co/scrollprize/ink_9um/resolve/main/hybrid_3d2d-seed42/step-075000.pth", "e635558ae6a1a807a7e5ec1e83adfd45bc3c0ac53883ea43f1d4e085d62a9cab"),
    ("seed43", "https://huggingface.co/scrollprize/ink_9um/resolve/main/hybrid_3d2d-seed43/step-075000.pth", "2aeaa85a35ef28d7bc7bf3e848c4a6a91385e9132710927fdba41133c4ecb28f"),
]


def digest(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def download(url, path, expected):
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with open(partial, "wb") as handle:
            for block in response.iter_content(4 * 1024 * 1024):
                if block:
                    handle.write(block)
    os.replace(partial, path)
    if digest(path) != expected:
        raise RuntimeError("checkpoint SHA256 mismatch")


def robust_mad(volume):
    array = volume.astype(np.float32)
    lower, upper = np.percentile(array, [1.0, 99.0])
    np.clip(array, lower, upper, out=array)
    median = float(np.median(array))
    mad = 1.4826 * float(np.median(np.abs(array - median)))
    if not np.isfinite(mad) or mad < 1e-6:
        mad = max(float(array.std()), abs(float(upper - lower)) / 2.0, 1.0)
    return np.nan_to_num((array - median) / mad)


started = time.monotonic()
if not torch.cuda.is_available():
    raise RuntimeError("GPU unavailable")
subprocess.run(
    [sys.executable, "-m", "pip", "install", "--quiet", "pynrrd==1.1.3", "zarr==2.18.7", "numcodecs==0.15.1"],
    check=True,
)
repo = TEMP / "villa"
subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", "https://github.com/ScrollPrize/villa.git", str(repo)], check=True)
subprocess.run(["git", "-C", str(repo), "sparse-checkout", "init", "--cone"], check=True)
subprocess.run(["git", "-C", str(repo), "sparse-checkout", "set", "ink-detection/koine_machines", "vesuvius/src/vesuvius"], check=True)
subprocess.run(["git", "-C", str(repo), "checkout", "--detach", VILLA_COMMIT], check=True)
sys.path.insert(0, str(repo / "ink-detection"))
sys.path.insert(0, str(repo / "vesuvius" / "src"))
from koine_machines.models.make_model import make_model

files = sorted(INPUT.glob("**/chunk_*_*.npz"))
if len(files) != 12:
    raise RuntimeError(f"expected 12 input chunks, found {len(files)}")
volumes = []
chunk_yx = []
for path in files:
    with np.load(path, allow_pickle=False) as bundle:
        volume = bundle["volume"]
    if volume.shape != (21, 128, 128) or volume.dtype != np.uint8:
        raise RuntimeError("invalid input chunk")
    volumes.append(robust_mad(volume[2:19]))
    parts = path.stem.split("_")
    chunk_yx.append([int(parts[-2]), int(parts[-1])])
inputs = torch.from_numpy(np.stack(volumes))[:, None]

all_predictions = []
model_reports = []
for model_id, url, expected in MODELS:
    checkpoint = TEMP / f"{model_id}.pth"
    download(url, checkpoint, expected)
    try:
        payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    except TypeError:
        payload = torch.load(checkpoint, map_location="cpu")
    config = dict(payload["config"])
    config.setdefault("crop_size", config["patch_size"])
    model = make_model(config)
    state_key = "ema_model" if isinstance(payload.get("ema_model"), dict) else "model"
    incompat = model.load_state_dict(payload[state_key], strict=False)
    model = model.cuda().eval()
    predictions = []
    before = time.monotonic()
    with torch.inference_mode(), torch.autocast(device_type="cuda", enabled=True):
        for start in range(0, len(inputs), 2):
            output = model(inputs[start:start + 2].cuda())
            logits = output["ink"]
            if isinstance(logits, (list, tuple)):
                logits = logits[0]
            probability = torch.sigmoid(logits.float())
            if probability.shape[-2:] != (128, 128):
                probability = F.interpolate(probability, size=(128, 128), mode="bilinear", align_corners=False)
            predictions.append(probability[:, 0].cpu().numpy())
    predictions = np.concatenate(predictions)
    all_predictions.append(predictions)
    model_reports.append({
        "model_id": model_id,
        "checkpoint_sha256": expected,
        "state_key": state_key,
        "missing_keys": len(incompat.missing_keys),
        "unexpected_keys": len(incompat.unexpected_keys),
        "seconds": time.monotonic() - before,
        "prediction_min": float(predictions.min()),
        "prediction_max": float(predictions.max()),
        "prediction_mean": float(predictions.mean()),
    })
    del model
    torch.cuda.empty_cache()

output_path = WORK / "predictions.npz"
np.savez_compressed(output_path, predictions=np.stack(all_predictions), chunk_yx=np.asarray(chunk_yx), model_ids=np.asarray([m[0] for m in MODELS]))
report = {
    "schema_version": "inksurf-ink9um-validation-inference/1.0",
    "experiment_id": "ink9um-pherc0814-46527-locked-inference-20260915",
    "track": "A",
    "regime": "VALIDATION",
    "geometry_tier": "G1",
    "status": "complete",
    "device": torch.cuda.get_device_name(0),
    "villa_commit": VILLA_COMMIT,
    "input_chunks": len(files),
    "input_crop_from_21": [2, 19],
    "normalization": "official robust_mad p01-p99 per patch",
    "models": model_reports,
    "output_sha256": digest(output_path),
    "elapsed_seconds": time.monotonic() - started,
    "interpretation": "Locked cross-scroll validation of one correlated model family; upstream online-validation exposure remains a documented dependency.",
}
with open(WORK / "inference_report.json", "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2, sort_keys=True)
    handle.write("\n")
print(json.dumps(report, indent=2, sort_keys=True), flush=True)
