"""Render frozen dense surface stacks from a verified local raw-chunk cache."""
from __future__ import annotations
import argparse, json, os, tempfile
from pathlib import Path
from typing import Any
import numpy as np
import tifffile
from .cross_scan_render_plan import bilinear
from .seating_reproduce import _atomic_json

class ChunkReader:
    def __init__(self, root: Path, chunk=128): self.root=root; self.chunk=chunk; self.loaded={}
    def nearest(self, points: np.ndarray) -> np.ndarray:
        out=np.empty(len(points),np.float32); keys=points//self.chunk
        unique,inverse=np.unique(keys,axis=0,return_inverse=True)
        for i,key in enumerate(unique):
            kt=tuple(int(v) for v in key); path=self.root.joinpath(*(str(v) for v in kt))
            if kt not in self.loaded:
                if not path.exists(): raise FileNotFoundError(path)
                self.loaded[kt]=np.fromfile(path,np.uint8).reshape((self.chunk,)*3)
            mask=inverse==i; local=points[mask]-key*self.chunk
            self_values=self.loaded[kt]; out[mask]=self_values[local[:,0],local[:,1],local[:,2]]
        return out
    def trilinear(self, coordinates: np.ndarray) -> np.ndarray:
        lo=np.floor(coordinates).astype(np.int64); frac=coordinates-lo; result=np.zeros(len(lo),np.float32)
        for dz in (0,1):
            for dy in (0,1):
                for dx in (0,1):
                    off=np.array([dz,dy,dx]); weight=np.prod(np.where(off,frac,1-frac),axis=1)
                    result += self.nearest(lo+off)*weight
        return result

def geometry(plan: dict[str,Any], root: Path):
    mesh=plan['mesh']; xyz=[tifffile.imread(root/mesh[k]).astype(np.float32) for k in ('x','y','z')]
    n=int(plan['render_pixels']); center=np.asarray(plan['seating_crop_origin_row_col'],float)+(int(plan['seating_crop_pixels'])-1)/2
    uv=(np.arange(n)-(n-1)/2)/float(plan['surface_grid_step_voxels']); rows=center[0]+uv; cols=center[1]+uv
    dense=np.stack([bilinear(a,rows,cols) for a in xyz],-1)
    dr=np.stack([bilinear(np.gradient(a,axis=0),rows,cols) for a in xyz],-1)
    dc=np.stack([bilinear(np.gradient(a,axis=1),rows,cols) for a in xyz],-1)
    normals=np.cross(dc,dr); normals/=np.linalg.norm(normals,axis=-1)[...,None]
    return dense[...,::-1],normals[...,::-1]

def atomic_npy(path:Path,array:np.ndarray):
    path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f: np.save(f,array); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    except BaseException:
        try: os.unlink(tmp)
        except FileNotFoundError: pass
        raise

def run(config_path:Path):
    cfg=json.loads(config_path.read_text(encoding='utf-8')); root=config_path.resolve().parent.parent
    if cfg.get('schema_version')!='inksurf-cross-scan-render/1.0' or cfg.get('track')!='A' or cfg.get('regime')!='DEV': raise ValueError('invalid config')
    plan=json.loads((root/cfg['plan_config']).read_text(encoding='utf-8')); points,normals=geometry(plan,root)
    lo,hi=plan['normal_offsets_voxels']; offsets=np.arange(lo,hi+1,dtype=np.float32); reports=[]
    for volume in plan['volumes']:
        reader=ChunkReader(root/cfg['cache_root']/volume['volume_id']/"0")
        stack=np.empty((len(offsets),points.shape[0],points.shape[1]),np.uint8)
        flatp=points.reshape(-1,3); flatn=normals.reshape(-1,3)
        for i,offset in enumerate(offsets):
            values=reader.trilinear(flatp+flatn*offset)
            stack[i]=np.rint(np.clip(values,0,255)).astype(np.uint8).reshape(points.shape[:2])
        out=root/cfg['output_root']/f"{volume['volume_id']}.npy"; atomic_npy(out,stack)
        center=stack[len(offsets)//2]; reports.append({'volume_id':volume['volume_id'],'output':str(out.relative_to(root)).replace('\\','/'),
            'chunks_read':len(reader.loaded),'nonzero_fraction':float(np.any(stack!=0,axis=0).mean()),
            'surface_gt40_fraction':float((center>40).mean()),'surface_mean':float(center.mean())})
    report={'schema_version':cfg['schema_version'],'experiment_id':cfg['experiment_id'],'track':'A','regime':'DEV','geometry_tier':'G2',
        'status':'render_complete','axes':'Z,Y,X','shape_zyx':[len(offsets),points.shape[0],points.shape[1]],'results':reports,
        'claim':'Geometry and CT-support output only; no ink claim.'}
    _atomic_json(root/cfg['report_json'],report); return report
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.config),indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
