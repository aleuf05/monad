#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,tempfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'web/assets/libfive'; MANIFEST=OUT/'manifest.json'; DEFAULT_EXPORTER=Path('/usr/local/bin/monad-libfive-export')
def scheme(shape,args):
 r=float(args.radius); size=float(args.size); minor=float(args.minor)
 if shape=='sphere': expr=f'(sphere {r})'; bound=r*1.25
 elif shape=='box': expr=f'(box [-{size/2} -{size/2} -{size/2}] [{size/2} {size/2} {size/2}])'; bound=size*.75
 elif shape=='torus': expr=f'(torus-z {r} {minor})'; bound=(r+minor)*1.25
 else: raise ValueError('unsupported primitive')
 return f'{expr}\n(set-quality! 8)\n(set-resolution! 20)\n(set-bounds! [-{bound} -{bound} -{bound}] [{bound} {bound} {bound}])\n'
def generate(args):
 exporter=Path(os.getenv('MONAD_LIBFIVE_EXPORTER',DEFAULT_EXPORTER));
 if not exporter.exists(): raise SystemExit(f'libfive exporter unavailable: {exporter}; run /home/cgl/cmd.sh')
 OUT.mkdir(parents=True,exist_ok=True); target=OUT/f'{args.name}.stl'; source=scheme(args.shape,args)
 with tempfile.NamedTemporaryFile('w',suffix='.io') as f: f.write(source); f.flush(); subprocess.run([str(exporter),f.name,str(target)],check=True,timeout=120)
 if not target.exists() or target.stat().st_size<84: raise SystemExit('export produced no valid STL')
 entry={'name':args.name,'primitive':args.shape,'stl_path':str(target.relative_to(ROOT)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'created_at':datetime.now(timezone.utc).isoformat(),'source':source,'upstream_commit':'c9e97343e0af998cd1696e85583eccba95532b96'}
 data=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'schema_version':'monad.libfiveManifest.v1','models':[]}; data['models']=[x for x in data['models'] if x['name']!=args.name]+[entry]; MANIFEST.write_text(json.dumps(data,indent=2)); print(json.dumps(entry,indent=2))
def main():
 p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True); sub.add_parser('status'); g=sub.add_parser('generate'); g.add_argument('shape',choices=['sphere','box','torus']); g.add_argument('name'); g.add_argument('--radius',type=float,default=10); g.add_argument('--size',type=float,default=20); g.add_argument('--minor',type=float,default=3); a=p.parse_args()
 if a.cmd=='status': print(json.dumps({'exporter':str(DEFAULT_EXPORTER),'installed':DEFAULT_EXPORTER.exists(),'manifest':str(MANIFEST)},indent=2)); return 0
 generate(a); return 0
if __name__=='__main__': raise SystemExit(main())
