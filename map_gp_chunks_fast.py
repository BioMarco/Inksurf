import requests
import re
import numpy as np
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = (
    "https://dl.ash2txt.org/datasets/"
    "grand-prize-banner-region/volumes/gp_volume.zarr/"
)

WORKERS = 32
TIMEOUT = 30

session = requests.Session()

def get(url):
    r = session.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text

def numeric_dirs(url):
    html = get(url)
    return sorted({
        int(x)
        for x in re.findall(r'href="(\d+)/"', html)
    })

def numeric_files(url):
    html = get(url)
    return sorted({
        int(x)
        for x in re.findall(r'href="(\d+)"', html)
    })

print("=" * 90)
print("INKSURF — FAST GRAND PRIZE CHUNK MAPPING")
print("=" * 90)

t0 = time.time()

# ----------------------------------------------------------
# 1. Z
# ----------------------------------------------------------

zs = numeric_dirs(BASE)

print("Z directories:", len(zs))
print("Z range      :", min(zs), "->", max(zs))

# ----------------------------------------------------------
# 2. Tutti gli Y in parallelo
# ----------------------------------------------------------

zy = []

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {
        ex.submit(numeric_dirs, f"{BASE}{z}/"): z
        for z in zs
    }

    done = 0

    for fut in as_completed(futs):
        z = futs[fut]
        ys = fut.result()

        zy.extend((z, y) for y in ys)

        done += 1
        if done % 10 == 0 or done == len(zs):
            print(
                f"Y scan: {done:3d}/{len(zs)}   "
                f"coppie Z/Y={len(zy):,}"
            )

print()
print("Coppie Z/Y:", len(zy))

# ----------------------------------------------------------
# 3. Tutti gli X in parallelo
# ----------------------------------------------------------

coords = []

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {
        ex.submit(
            numeric_files,
            f"{BASE}{z}/{y}/"
        ): (z, y)
        for z, y in zy
    }

    done = 0
    total = len(futs)

    for fut in as_completed(futs):

        z, y = futs[fut]

        try:
            xs = fut.result()
            coords.extend(
                (z, y, x)
                for x in xs
            )
        except Exception as e:
            print(
                f"WARNING Z/Y={z}/{y}: {e}"
            )

        done += 1

        if done % 100 == 0 or done == total:
            elapsed = time.time() - t0
            print(
                f"X scan: {done:5d}/{total}   "
                f"chunk={len(coords):,}   "
                f"tempo={elapsed/60:.1f} min"
            )

coords = np.asarray(coords, dtype=np.int32)

if not len(coords):
    raise RuntimeError("Nessun chunk trovato")

# ----------------------------------------------------------
# 4. Bounding box
# ----------------------------------------------------------

cmin = coords.min(axis=0)
cmax = coords.max(axis=0)

lo = cmin * 128
hi = (cmax + 1) * 128

print()
print("=" * 90)
print("RISULTATO")
print("=" * 90)

print("Chunk presenti:", f"{len(coords):,}")

print()
print("RANGE CHUNK ZYX")
print(" Z:", cmin[0], "->", cmax[0])
print(" Y:", cmin[1], "->", cmax[1])
print(" X:", cmin[2], "->", cmax[2])

print()
print("BBOX GRAND PRIZE — FRAME 2023")
print(f" Z: {lo[0]}:{hi[0]}")
print(f" Y: {lo[1]}:{hi[1]}")
print(f" X: {lo[2]}:{hi[2]}")

print()
print("DIMENSIONI BBOX")
print(
    f" Z={hi[0]-lo[0]} "
    f"Y={hi[1]-lo[1]} "
    f"X={hi[2]-lo[2]} voxel"
)

outfile = Path(
    "/mnt/d/Vesuvius/inksurf/results/"
    "grand_prize_chunk_coords.npy"
)

outfile.parent.mkdir(
    parents=True,
    exist_ok=True
)

np.save(outfile, coords)

print()
print("Coordinate salvate:")
print(outfile)

elapsed = time.time() - t0

print()
print(
    f"TEMPO TOTALE: "
    f"{elapsed:.1f} s "
    f"({elapsed/60:.2f} min)"
)

print("=" * 90)
