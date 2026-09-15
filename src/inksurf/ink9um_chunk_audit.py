"""Verify and prepare bounded ink_9um DEV chunks without visual inspection."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from numcodecs import Blosc

from .bounded_http_download import _sha256
from .cross_scan_consistency import atomic_npz
from .seating_reproduce import _atomic_json


def decode_annotation(path: Path, shape=(21, 128, 128)) -> np.ndarray:
    codec = Blosc(cname="zstd", clevel=5, shuffle=Blosc.BITSHUFFLE)
    decoded = codec.decode(path.read_bytes())
    array = np.frombuffer(decoded, dtype=np.uint8)
    if array.size != int(np.prod(shape)):
        raise ValueError(f"annotation chunk has {array.size} values, expected {np.prod(shape)}")
    return array.reshape(shape)


def pool_centered(source: np.ndarray, output_planes=21, z_pool=4) -> np.ndarray:
    requested = output_planes * z_pool
    if source.ndim != 3 or requested > source.shape[0]:
        raise ValueError("invalid source for centered pooling")
    start = math.ceil((source.shape[0] - requested) / 2)
    block = source[start:start + requested].astype(np.float32)
    return np.rint(block.reshape(output_planes, z_pool, *source.shape[1:]).mean(axis=1)).astype(np.uint8)


def run(config_path: Path) -> dict:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    root = config_path.resolve().parent.parent
    if cfg.get("schema_version") != "inksurf-ink9um-chunk-audit/1.0":
        raise ValueError("invalid config schema")
    regime = cfg.get("regime")
    if cfg.get("track") != "A" or regime not in {"DEV", "VALIDATION"}:
        raise ValueError("chunk audit is restricted to Track A DEV/VALIDATION")
    if regime == "VALIDATION" and cfg.get("freeze_state") != "frozen_before_ground_truth":
        raise ValueError("VALIDATION chunk audit requires a frozen protocol")
    manifest = json.loads((root / cfg["manifest"]).read_text(encoding="utf-8"))
    download = json.loads((root / cfg["download_report"]).read_text(encoding="utf-8"))
    indexed = {Path(item["destination"]).resolve(): item for item in download["files"]}
    cache = root / cfg["cache_root"]
    rows = []
    for entry in manifest["selected_chunks"]:
        y, x = entry["chunk_yx"]
        source_path = cache / "source" / "2" / "0" / str(y) / str(x)
        recorded = indexed.get(source_path.resolve())
        if recorded is None or _sha256(source_path) != recorded["sha256"]:
            raise RuntimeError(f"unverified source chunk {y},{x}")
        source = np.fromfile(source_path, dtype=np.uint8).reshape(109, 128, 128)
        pooled = pool_centered(source, 21, int(cfg["z_pool"]))
        annotations = {}
        for kind in ("inklabels", "supervision_mask", "validation_mask"):
            path = cache / "annotations" / kind / f"0.{y}.{x}"
            recorded = indexed.get(path.resolve())
            if recorded is None or _sha256(path) != recorded["sha256"]:
                raise RuntimeError(f"unverified {kind} chunk {y},{x}")
            annotations[kind] = decode_annotation(path)
        plane = int(cfg["label_plane"])
        label = annotations["inklabels"][plane] > 0
        validation = annotations["validation_mask"][plane] > 0
        supervision = annotations["supervision_mask"][plane] > 0
        out = root / cfg["derived_root"] / f"chunk_{y}_{x}.npz"
        atomic_npz(out, volume=pooled, inklabels=label, validation_mask=validation, supervision_mask=supervision)
        valid_count = int(validation.sum())
        rows.append({
            "chunk_yx": [y, x],
            "derived": str(out.relative_to(root)).replace("\\", "/"),
            "source_sha256": _sha256(source_path),
            "validation_pixels": valid_count,
            "ink_pixels_in_validation": int((label & validation).sum()),
            "ink_prevalence_in_validation": float((label & validation).sum() / valid_count) if valid_count else None,
            "supervision_pixels_in_validation": int((supervision & validation).sum()),
            "pooled_nonzero_fraction": float((pooled != 0).mean()),
        })
    total_valid = sum(row["validation_pixels"] for row in rows)
    total_ink = sum(row["ink_pixels_in_validation"] for row in rows)
    report = {
        "schema_version": cfg["schema_version"],
        "experiment_id": cfg["experiment_id"],
        "track": "A",
        "regime": regime,
        "geometry_tier": "G1",
        "status": "bounded_chunks_ready_for_inference" if total_valid and total_ink else "NO_GO_EMPTY_EVALUATION",
        "preparation": "official level-2 XY; centered 84 Z planes; rounded 4x Z mean pooling; 21x128x128 uint8",
        "chunks": rows,
        "total_validation_pixels": total_valid,
        "total_ink_pixels_in_validation": total_ink,
        "ink_prevalence_in_validation": float(total_ink / total_valid) if total_valid else None,
        "visual_files_inspected": 0,
        "limitation": (
            "Locally locked validation with transferred/pseudo labels; upstream online-validation exposure prevents fully independent confirmation."
            if regime == "VALIDATION"
            else "Transferred annotation/pseudo-label benchmark and official online-validation case; DEV evidence only."
        ),
    }
    _atomic_json(root / cfg["report_json"], report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
