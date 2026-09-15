"""Plan exact raw Zarr chunks for a dense cross-scan surface render."""

from __future__ import annotations
import argparse, csv, json, os, tempfile
from io import StringIO
from pathlib import Path
from typing import Any
import numpy as np
import tifffile


def bilinear(array: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    r0 = np.floor(rows).astype(int); c0 = np.floor(cols).astype(int)
    r1 = np.minimum(r0 + 1, array.shape[0] - 1); c1 = np.minimum(c0 + 1, array.shape[1] - 1)
    wr = rows - r0; wc = cols - c0
    return ((1-wr)[:, None] * (1-wc)[None, :] * array[np.ix_(r0, c0)] +
            wr[:, None] * (1-wc)[None, :] * array[np.ix_(r1, c0)] +
            (1-wr)[:, None] * wc[None, :] * array[np.ix_(r0, c1)] +
            wr[:, None] * wc[None, :] * array[np.ix_(r1, c1)])


def _atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            f.write(text); f.flush(); os.fsync(f.fileno())
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding='utf-8'))
    if config.get('schema_version') != 'inksurf-cross-scan-render-plan/1.0': raise ValueError('unsupported schema')
    if config.get('track') != 'A' or config.get('regime') != 'DEV': raise ValueError('plan must be Track A / DEV')
    root = config_path.resolve().parent.parent; mesh = config['mesh']
    xyz = [tifffile.imread(root / mesh[k]).astype(np.float32) for k in ('x','y','z')]
    if not (xyz[0].shape == xyz[1].shape == xyz[2].shape): raise ValueError('TIFXYZ shapes differ')
    n = int(config['render_pixels']); step = float(config['surface_grid_step_voxels'])
    origin = np.asarray(config['seating_crop_origin_row_col'], float)
    center = origin + (int(config['seating_crop_pixels']) - 1) / 2
    uv = (np.arange(n, dtype=float) - (n - 1) / 2) / step
    rows = center[0] + uv; cols = center[1] + uv
    if rows.min() < 1 or cols.min() < 1 or rows.max() >= xyz[0].shape[0]-1 or cols.max() >= xyz[0].shape[1]-1:
        raise ValueError('render footprint lacks gradient margin')
    dense_xyz = np.stack([bilinear(a, rows, cols) for a in xyz], axis=-1)
    deriv_row = np.stack([bilinear(np.gradient(a, axis=0), rows, cols) for a in xyz], axis=-1)
    deriv_col = np.stack([bilinear(np.gradient(a, axis=1), rows, cols) for a in xyz], axis=-1)
    normals_xyz = np.cross(deriv_col, deriv_row)
    norm = np.linalg.norm(normals_xyz, axis=-1)
    if not np.isfinite(dense_xyz).all() or not np.isfinite(norm).all() or np.any(norm <= 0):
        raise ValueError('non-finite or degenerate dense geometry')
    normals_xyz /= norm[..., None]
    lo, hi = [int(v) for v in config['normal_offsets_voxels']]
    offsets = np.arange(lo, hi + 1, dtype=np.float32)
    chunk = np.asarray(config['chunk_shape_zyx'], int)
    keys: set[tuple[int,int,int]] = set(); bounds_min = np.full(3, np.inf); bounds_max = np.full(3, -np.inf)
    for r in range(n):
        points_xyz = dense_xyz[r, :, None, :] + normals_xyz[r, :, None, :] * offsets[None, :, None]
        points_zyx = points_xyz[..., ::-1]
        lower = np.floor(points_zyx).astype(np.int64).reshape(-1, 3)
        upper = np.ceil(points_zyx).astype(np.int64).reshape(-1, 3)
        bounds_min = np.minimum(bounds_min, lower.min(axis=0)); bounds_max = np.maximum(bounds_max, upper.max(axis=0))
        keys.update(map(tuple, lower // chunk)); keys.update(map(tuple, upper // chunk))
    records=[]; max_bytes=0
    for volume in config['volumes']:
        shape=np.asarray(volume['shape_zyx'], int)
        if np.any(bounds_min < 0) or np.any(bounds_max >= shape): raise ValueError(f"render outside {volume['volume_id']}")
        for key in sorted(keys):
            start=np.asarray(key)*chunk; extent=np.minimum(start+chunk, shape)-start
            raw=int(np.prod(extent)); max_bytes += raw
            records.append({'volume_id':volume['volume_id'],'z_chunk':key[0],'y_chunk':key[1],'x_chunk':key[2],
                            'raw_bytes':raw,'object_key':f"0/{key[0]}/{key[1]}/{key[2]}"})
    report={'schema_version':config['schema_version'],'experiment_id':config['experiment_id'],'track':'A','regime':'DEV',
            'current_geometry_tier':config['current_geometry_tier'],'target_geometry_tier':config['target_geometry_tier'],
            'status':'planned_not_downloaded_geometry_gate_pending','axes':'Z,Y,X','render_pixels':n,
            'render_width_mm':n*float(mesh['voxel_um'])/1000,'depth_layers':len(offsets),
            'uv_center_row_col':center.tolist(),'uv_bounds_row_col':[float(rows.min()),float(cols.min()),float(rows.max()),float(cols.max())],
            'xyz_sample_bounds_zyx':[bounds_min.astype(int).tolist(),bounds_max.astype(int).tolist()],
            'unique_chunks_per_volume':len(keys),'total_chunk_objects':len(records),'maximum_raw_bytes':max_bytes,
            'volumetric_bytes_downloaded':0,'blockers':['dense ROI geometry audit must pass G2 before download']}
    outputs=config['outputs']; _atomic(root/outputs['report_json'],json.dumps(report,indent=2,sort_keys=True)+'\n')
    s=StringIO(newline=''); fields=['volume_id','z_chunk','y_chunk','x_chunk','raw_bytes','object_key']; w=csv.DictWriter(s,fieldnames=fields); w.writeheader(); w.writerows(records)
    _atomic(root/outputs['chunk_manifest_csv'],s.getvalue()); return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--config',type=Path,required=True); a=p.parse_args()
    print(json.dumps(run(a.config),indent=2,sort_keys=True)); return 0
if __name__ == '__main__': raise SystemExit(main())
