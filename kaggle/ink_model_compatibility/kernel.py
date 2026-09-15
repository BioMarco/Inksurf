"""Frozen DEV compatibility run for InkSurf; outputs a machine-readable report."""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import requests
import tifffile
import torch
import torch.nn.functional as F

WORK = Path("/kaggle/working")
ASSETS = Path("/kaggle/temp/inksurf_assets")
LOADER = ASSETS / "villa_inference"
VILLA_COMMIT = "76370e1a6908f0bc2eb7f92bc0397336ecbe3d96"
BASE = "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0139/segments/20250108000000-w025_2025010863"
SURFACE = BASE + "/surface-volumes/2.399um-0.22m-78keV-volume-20260102150214.zarr"
INK_URL = BASE + "/ink-detection/PHerc0139-20250108000000-2.399um-0.22m-78keV-volume-20260102150214-20260417190342-new_canon_autoresearch_recipe-tile256-stride128.tif"
CKPT_URL = "https://huggingface.co/scrollprize/ink_canonical_2um/resolve/075855bc69317ef6febf39a0d9d687b27d2b7c29/r152_3ddec_v2_l5_epoch13.ckpt"
EXPECTED = {
    "checkpoint": "36dd0de84b7b7aa6590184192c7415466cd8a1ba7c1e59f42c6373846373c3e0",
    "published": "d99dbd0698a41cc2106888eebc6bed76245cf5a9074a68d025066c89b982fa08",
    "model": "7b2b2cfc6c7fb963a3da1bf128543ceadf8ad887f32a319bc0a38fb378f9e2ca",
    "resnet": "2b49ac430d77bae189cf002ed9c2748f940a6cd92b809a23db6f7dba381afbf6",
    "nonlocal": "09910c134003051b0cb75bd1ede1c2da8bab7cc60bf56997ace018018a806ce5",
}


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download(url, path, expected_hash=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and (not expected_hash or digest(path) == expected_hash):
        return
    partial = path.with_suffix(path.suffix + ".partial")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with open(partial, "wb") as f:
            for block in response.iter_content(4 * 1024 * 1024):
                if block:
                    f.write(block)
    os.replace(partial, path)
    if expected_hash and digest(path) != expected_hash:
        raise RuntimeError("SHA256 mismatch: " + str(path))


started = time.monotonic()
print("device", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU", flush=True)
if not torch.cuda.is_available():
    raise RuntimeError("GPU was requested but is unavailable")
checkpoint = ASSETS / "r152_3ddec_v2_l5_epoch13.ckpt"
published_path = ASSETS / "published_ink_map.tif"
download(CKPT_URL, checkpoint, EXPECTED["checkpoint"])
download(INK_URL, published_path, EXPECTED["published"])
loader_files = [
    ("model_resnet3d_3d_decoder.py", "model", 7976),
    ("models/resnetall.py", "resnet", 7855),
    ("models/non_local_helper.py", "nonlocal", 5782),
]
for relative, key, _ in loader_files:
    url = f"https://raw.githubusercontent.com/ScrollPrize/villa/{VILLA_COMMIT}/ink-detection/optimized_inference/{relative}"
    download(url, LOADER / relative, EXPECTED[key])
(LOADER / "models" / "__init__.py").touch()

stack = np.zeros((109, 512, 512), dtype=np.uint8)
for iy, cy in enumerate(range(192, 196)):
    for ix, cx in enumerate(range(144, 148)):
        path = ASSETS / "chunks" / str(cy) / str(cx)
        download(f"{SURFACE}/0/0/{cy}/{cx}", path)
        raw = np.fromfile(path, dtype=np.uint8)
        if raw.size != 109 * 128 * 128:
            raise RuntimeError(f"chunk size mismatch {cy}/{cx}")
        stack[:, iy*128:(iy+1)*128, ix*128:(ix+1)*128] = raw.reshape(109, 128, 128)
stack = np.ascontiguousarray(np.clip(stack[24:86], 0, 200))

published_full = tifffile.imread(published_path)
published = np.asarray(published_full[24576:25088, 18432:18944], dtype=np.uint8).copy()
del published_full

sys.path.insert(0, str(LOADER))
from model_resnet3d_3d_decoder import load_model
device = torch.device("cuda")
model = load_model(str(checkpoint), device, num_frames=62)
positions = [(y, x) for y in (0, 128, 256) for x in (0, 128, 256)]
w = np.outer(np.hanning(256), np.hanning(256)).astype(np.float32)
w /= w.sum()
pred_sum = np.zeros((512, 512), np.float32)
weight_sum = np.zeros((512, 512), np.float32)
with torch.inference_mode():
    for index, (y, x) in enumerate(positions, 1):
        before = time.monotonic()
        volume = stack[:, y:y+256, x:x+256]
        valid = np.any(volume != 0, axis=0).astype(np.float32)
        tensor = torch.from_numpy(volume.astype(np.float32) / 200.0)[None, None].to(device)
        with torch.autocast(device_type="cuda", enabled=True):
            logits = model.forward(tensor)
        prob = torch.sigmoid(logits)
        prob = F.interpolate(prob.float(), size=(256, 256), mode="bilinear", align_corners=False)[0, 0].cpu().numpy()
        pred_sum[y:y+256, x:x+256] += prob * w * valid
        weight_sum[y:y+256, x:x+256] += w * valid
        print(f"tile {index}/9 seconds={time.monotonic()-before:.3f}", flush=True)
prediction = pred_sum / np.clip(weight_sum, 1e-12, None)
local = prediction[128:384, 128:384].astype(np.float64)
reference = published[128:384, 128:384].astype(np.float64) / 255.0
valid = weight_sum[128:384, 128:384] > 0
pearson = float(np.corrcoef(local[valid], reference[valid])[0, 1])
from scipy.stats import spearmanr
spearman = float(spearmanr(local[valid], reference[valid]).statistic)
np.savez_compressed(WORK / "local_prediction.npz", prediction=prediction, published=published, weight_sum=weight_sum)
report = {
    "schema_version": "inksurf-ink-model-compatibility/1.0",
    "experiment_id": "canonical-ink-compatibility-pherc0139-20260915-kaggle",
    "track": "A", "regime": "DEV", "geometry_tier": "G1",
    "status": "pass" if pearson > 0.5 else "fail",
    "acceptance_pearson_r_gt": 0.5, "pearson_r": pearson, "spearman_rho": spearman,
    "evaluation_pixels": int(valid.sum()), "tiles": 9, "layers": 62,
    "reverse_layers": False, "device": torch.cuda.get_device_name(0),
    "elapsed_seconds": time.monotonic() - started, "villa_commit": VILLA_COMMIT,
    "asset_sha256": EXPECTED,
    "interpretation": "Pipeline compatibility only; this is not a new ink claim."
}
with open(WORK / "compatibility_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, sort_keys=True); f.write("\n")
print(json.dumps(report, indent=2, sort_keys=True), flush=True)
