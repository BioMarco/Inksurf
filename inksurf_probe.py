import numpy as np
import zarr
import fsspec
from scipy.ndimage import distance_transform_edt

INK = (
    "s3://vesuvius-challenge-open-data/"
    "PHercParis4/representations/predictions/ink-3d/"
    "20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr/"
)

SURF = (
    "s3://vesuvius-challenge-open-data/"
    "PHercParis4/representations/predictions/surfaces/"
    "20260411134726-surface-20260413141734-surface-recto-2um-ps256-L0-th0.45.zarr/"
)

LEVEL = "3"
CHUNK = 256

# Soglie iniziali, volutamente conservative.
INK_T = 128
SURF_T = 128

fs = fsspec.filesystem("s3", anon=True)

ink_g = zarr.open_group(fs.get_mapper(INK), mode="r")
surf_g = zarr.open_group(fs.get_mapper(SURF), mode="r")

ink = ink_g[LEVEL]
surf = surf_g[LEVEL]

print("=" * 90)
print("INKSURF — PROBE LEVEL 3")
print("=" * 90)
print("INK   :", ink.shape, ink.chunks, ink.dtype)
print("SURF  :", surf.shape, surf.chunks, surf.dtype)
print("INK_T :", INK_T)
print("SURF_T:", SURF_T)
print()

# T2 era XYZ = 19735,19651,35344 a livello 0.
# Convertiamo in ZYX livello 3 dividendo per 8.
t2_zyx = np.array(
    [35344, 19651, 19735],
    dtype=np.int64
) // 8

center_chunk = t2_zyx // CHUNK

print("T2 level-3 ZYX       :", tuple(t2_zyx))
print("T2 level-3 chunk ZYX :", tuple(center_chunk))
print()

# 10 chunk: quello contenente T2 + vicinato.
offsets = [
    (0,0,0),
    (-1,0,0), (1,0,0),
    (0,-1,0), (0,1,0),
    (0,0,-1), (0,0,1),
    (-1,-1,0),
    (1,1,0),
    (0,1,1),
]

def read_chunk(a, cz, cy, cx):
    z0, y0, x0 = cz*CHUNK, cy*CHUNK, cx*CHUNK
    z1 = min(z0+CHUNK, a.shape[0])
    y1 = min(y0+CHUNK, a.shape[1])
    x1 = min(x0+CHUNK, a.shape[2])
    return np.asarray(a[z0:z1, y0:y1, x0:x1])

print("=" * 90)
print("CHUNK PROBE")
print("=" * 90)

for n, off in enumerate(offsets, 1):

    c = center_chunk + np.array(off)
    cz, cy, cx = map(int, c)

    if (
        cz < 0 or cy < 0 or cx < 0 or
        cz*CHUNK >= ink.shape[0] or
        cy*CHUNK >= ink.shape[1] or
        cx*CHUNK >= ink.shape[2]
    ):
        continue

    print()
    print(f"[{n:02d}] chunk ZYX=({cz},{cy},{cx})")

    iv = read_chunk(ink, cz, cy, cx)
    sv = read_chunk(surf, cz, cy, cx)

    im = iv >= INK_T
    sm = sv >= SURF_T

    ni = int(im.sum())
    ns = int(sm.sum())

    print(
        f"  INK  min/max={int(iv.min()):3d}/{int(iv.max()):3d} "
        f"mean={iv.mean():7.3f} >=128={ni:9d} "
        f"({100*ni/iv.size:8.5f}%)"
    )

    print(
        f"  SURF min/max={int(sv.min()):3d}/{int(sv.max()):3d} "
        f"mean={sv.mean():7.3f} >=128={ns:9d} "
        f"({100*ns/sv.size:8.5f}%)"
    )

    if ni == 0:
        print("  RESULT: nessun ink forte")
        continue

    if ns == 0:
        print("  RESULT: ink presente, nessuna surface >=128")
        continue

    # Distanza di ogni voxel dalla surface.
    # distance_transform_edt(~sm) restituisce distanza dalla surface più vicina.
    dist = distance_transform_edt(~sm)

    d = dist[im]

    print("  DISTANZA INK -> SURFACE")
    print(f"    min     : {d.min():7.3f} voxel")
    print(f"    median  : {np.median(d):7.3f} voxel")
    print(f"    p90     : {np.percentile(d,90):7.3f} voxel")

    for radius in (0,1,2,3,5,8):
        pct = 100.0 * np.mean(d <= radius)
        print(
            f"    <= {radius:2d} vx : "
            f"{pct:8.3f}%"
        )

print()
print("=" * 90)
print("FINE PROBE")
print("=" * 90)
