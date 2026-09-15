import io
import csv
import json
import math
import struct
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import fsspec
import numpy as np
import tifffile


# ============================================================
# CONFIG
# ============================================================

TARGET_XYZ = np.array(
    [19735.0, 19651.0, 35344.0],
    dtype=np.float32
)

VOL = "20260411134726"

INDEX = Path(
    "/home/marco/vesuvius-dev/villa/"
    "scrollprize.org/static/data_browser/index.json"
)

OUTDIR = Path("/mnt/d/Vesuvius/inksurf/results")
OUTDIR.mkdir(parents=True, exist_ok=True)

STAGE1_STEP = 256
STAGE2_STEP = 64

STAGE1_KEEP = 12
STAGE2_KEEP = 5

# Non esageriamo con S3.
# Otto segmenti contemporanei sono già parecchi.
MAX_WORKERS = 8


# ============================================================
# DATASET
# ============================================================

data = json.loads(INDEX.read_text())

paris4 = next(
    s for s in data["scrolls"]
    if s["id"] == "PHercParis4"
)

fs = fsspec.filesystem("s3", anon=True)


# ============================================================
# TIFF METADATA
# ============================================================

def tif_info(path):

    with fs.open(path, "rb") as f:

        with tifffile.TiffFile(f) as tif:

            p = tif.pages[0]

            if len(p.dataoffsets) != 1:
                raise RuntimeError(
                    f"{path}: expected one TIFF data block"
                )

            if p.dtype != np.dtype("float32"):
                raise RuntimeError(
                    f"{path}: expected float32, got {p.dtype}"
                )

            return {
                "height": int(p.shape[0]),
                "width": int(p.shape[1]),
                "offset": int(p.dataoffsets[0]),
                "byteorder": tif.byteorder,
            }


# ============================================================
# ROW READER
# ============================================================

def read_row(f, *, row, width, dataoffset, fmt):

    """
    Legge UNA riga completa del TIFF con una singola range read.

    Questo sostituisce migliaia di read() da 4 byte della versione
    precedente.
    """

    row_bytes = width * 4
    offset = dataoffset + row * row_bytes

    f.seek(offset)
    raw = f.read(row_bytes)

    if len(raw) != row_bytes:
        raise IOError(
            f"short read at row {row}: "
            f"{len(raw)} != {row_bytes}"
        )

    endian = "<" if fmt == "<f" else ">"

    return np.frombuffer(
        raw,
        dtype=np.dtype(endian + "f4")
    )


# ============================================================
# SURFACE SAMPLING
# ============================================================

def sample_segment(seg, step):

    seg_id = seg["id"]
    label = seg.get("label", "")

    base = (
        seg["folder"].rstrip("/")
        + "/mesh/"
        + f"{seg_id}-on-{VOL}-2.4um.tifxyz/"
    )

    x_path = base + "x.tif"
    y_path = base + "y.tif"
    z_path = base + "z.tif"

    info = tif_info(x_path)

    h = info["height"]
    w = info["width"]

    fmt = (
        "<f"
        if info["byteorder"] == "<"
        else ">f"
    )

    rows = list(range(0, h, step))

    if not rows or rows[-1] != h - 1:
        rows.append(h - 1)

    cols = np.arange(
        0,
        w,
        step,
        dtype=np.int64
    )

    if len(cols) == 0 or cols[-1] != w - 1:
        cols = np.append(cols, w - 1)

    best_dist2 = float("inf")
    best_xyz = None
    valid_samples = 0

    # Una cache molto piccola serve solo ad assorbire eventuali
    # letture adiacenti. La parte importante è: una lettura per riga,
    # NON una lettura per pixel.
    open_kwargs = {
        "mode": "rb",
        "block_size": 1024 * 1024,
        "cache_type": "readahead",
    }

    with (
        fs.open(x_path, **open_kwargs) as fx,
        fs.open(y_path, **open_kwargs) as fy,
        fs.open(z_path, **open_kwargs) as fz,
    ):

        for row in rows:

            xr = read_row(
                fx,
                row=row,
                width=w,
                dataoffset=info["offset"],
                fmt=fmt,
            )

            yr = read_row(
                fy,
                row=row,
                width=w,
                dataoffset=info["offset"],
                fmt=fmt,
            )

            zr = read_row(
                fz,
                row=row,
                width=w,
                dataoffset=info["offset"],
                fmt=fmt,
            )

            xs = xr[cols]
            ys = yr[cols]
            zs = zr[cols]

            valid = (
                np.isfinite(xs)
                & np.isfinite(ys)
                & np.isfinite(zs)
                & (xs >= 0)
                & (ys >= 0)
                & (zs >= 0)
            )

            if not np.any(valid):
                continue

            xs = xs[valid]
            ys = ys[valid]
            zs = zs[valid]

            valid_samples += len(xs)

            dx = xs - TARGET_XYZ[0]
            dy = ys - TARGET_XYZ[1]
            dz = zs - TARGET_XYZ[2]

            dist2 = dx*dx + dy*dy + dz*dz

            j = int(np.argmin(dist2))

            if float(dist2[j]) < best_dist2:

                best_dist2 = float(dist2[j])

                best_xyz = (
                    float(xs[j]),
                    float(ys[j]),
                    float(zs[j]),
                )

    return {
        "segment_id": seg_id,
        "label": label,
        "step": step,
        "samples": int(valid_samples),
        "distance_vox": math.sqrt(best_dist2)
            if math.isfinite(best_dist2)
            else float("inf"),
        "distance_um": math.sqrt(best_dist2) * 2.4
            if math.isfinite(best_dist2)
            else float("inf"),
        "nearest_xyz": best_xyz,
    }


# ============================================================
# BBOX PREFILTER
# ============================================================

def bbox_candidates():

    candidates = []

    tx, ty, tz = TARGET_XYZ

    for seg in paris4["inkSegments"]:

        seg_id = seg["id"]

        base = (
            seg["folder"].rstrip("/")
            + "/mesh/"
            + f"{seg_id}-on-{VOL}-2.4um.tifxyz/"
        )

        try:
            with fs.open(base + "meta.json", "r") as f:
                meta = json.load(f)

        except Exception:
            continue

        bbox = meta.get("bbox")

        if not bbox:
            continue

        lo, hi = bbox

        if (
            lo[0] <= tx <= hi[0]
            and lo[1] <= ty <= hi[1]
            and lo[2] <= tz <= hi[2]
        ):
            candidates.append(seg)

    return candidates


# ============================================================
# PARALLEL SCAN
# ============================================================

def scan(segments, step, title):

    print()
    print("=" * 100)
    print(title)
    print("=" * 100)

    print("Segments :", len(segments))
    print("Step     :", step)
    print("Workers  :", MAX_WORKERS)
    print()

    start = time.time()

    results = []

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = {
            executor.submit(
                sample_segment,
                seg,
                step
            ): seg
            for seg in segments
        }

        done = 0

        for future in as_completed(futures):

            seg = futures[future]
            done += 1

            try:

                r = future.result()
                results.append(r)

                print(
                    f"[{done:02d}/{len(segments):02d}] "
                    f"{r['label'][:20]:20s} "
                    f"samples={r['samples']:5d} "
                    f"d~={r['distance_vox']:9.2f} vx "
                    f"({r['distance_um']:9.2f} µm)"
                )

            except Exception as exc:

                print(
                    f"[{done:02d}/{len(segments):02d}] "
                    f"{seg.get('label','')[:20]:20s} "
                    f"ERROR: {exc}"
                )

    elapsed = time.time() - start

    results.sort(
        key=lambda r: r["distance_vox"]
    )

    print()
    print(
        f"Tempo stage: "
        f"{elapsed:.1f} s "
        f"({elapsed/60:.2f} min)"
    )

    return results


# ============================================================
# SAVE
# ============================================================

def save_csv(results, filename):

    path = OUTDIR / filename

    with path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "rank",
            "segment_id",
            "label",
            "step",
            "samples",
            "distance_vox",
            "distance_um",
            "nearest_x",
            "nearest_y",
            "nearest_z",
        ])

        for rank, r in enumerate(results, 1):

            xyz = r["nearest_xyz"]

            writer.writerow([
                rank,
                r["segment_id"],
                r["label"],
                r["step"],
                r["samples"],
                r["distance_vox"],
                r["distance_um"],
                None if xyz is None else xyz[0],
                None if xyz is None else xyz[1],
                None if xyz is None else xyz[2],
            ])

    print("Salvato:", path)


# ============================================================
# MAIN
# ============================================================

print("=" * 100)
print("INKSURF SCANNER — COARSE SURFACE SEARCH v2")
print("=" * 100)

print(
    "Target XYZ:",
    tuple(float(v) for v in TARGET_XYZ)
)

candidates = bbox_candidates()

print("BBOX candidates:", len(candidates))


# ---------------- STAGE 1 ----------------

stage1 = scan(
    candidates,
    STAGE1_STEP,
    "STAGE 1 — FAST COARSE SEARCH"
)

save_csv(
    stage1,
    "T2_stage1_step256.csv"
)

print()
print("=" * 100)
print("TOP STAGE 1")
print("=" * 100)

for i, r in enumerate(
    stage1[:STAGE1_KEEP],
    1
):
    print(
        f"{i:2d}. "
        f"{r['label']:20s} "
        f"{r['segment_id']} "
        f"d~={r['distance_vox']:9.2f} vx "
        f"({r['distance_um']:9.2f} µm)"
    )


# ---------------- STAGE 2 ----------------

ids = {
    r["segment_id"]
    for r in stage1[:STAGE1_KEEP]
}

stage2_segments = [
    seg
    for seg in candidates
    if seg["id"] in ids
]

stage2 = scan(
    stage2_segments,
    STAGE2_STEP,
    "STAGE 2 — REFINED COARSE SEARCH"
)

save_csv(
    stage2,
    "T2_stage2_step64.csv"
)

print()
print("=" * 100)
print("FINAL TOP CANDIDATES")
print("=" * 100)

for i, r in enumerate(
    stage2[:STAGE2_KEEP],
    1
):

    print(
        f"{i:2d}. "
        f"{r['label']:20s} "
        f"{r['segment_id']} "
        f"d~={r['distance_vox']:9.3f} vx "
        f"({r['distance_um']:9.3f} µm)"
    )

    if r["nearest_xyz"] is not None:

        x, y, z = r["nearest_xyz"]

        print(
            f"    coarse nearest XYZ="
            f"({x:.2f}, {y:.2f}, {z:.2f})"
        )

print()
print("=" * 100)
print("INKSURF COARSE SEARCH COMPLETE")
print("=" * 100)
