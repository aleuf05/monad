#!/usr/bin/env python3
"""Bounded HTTP adapter for the Monad libfive console."""
from __future__ import annotations
import argparse,json,subprocess,sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
GENERATOR=ROOT/'tools/libfive/generate.py'
MANIFEST=ROOT/'web/assets/libfive/manifest.json'

def status():
 result=subprocess.run([sys.executable,str(GENERATOR),'status'],capture_output=True,text=True,timeout=5,check=True)
 data=json.loads(result.stdout); data['models']=json.loads(MANIFEST.read_text()).get('models',[]) if MANIFEST.exists() else []
 return data

def generate(payload):
 allowed={'shape','name','radius','size','minor','source','source_filename'}
 if not isinstance(payload,dict) or set(payload)-allowed: raise ValueError('unsupported request fields')
 if 'source' in payload:
  source=payload['source']; filename=Path(str(payload.get('source_filename','source.io'))).name
  if not isinstance(source,str) or len(source.encode())>65536: raise ValueError('source must be text no larger than 64 KB')
  if Path(filename).suffix.lower() not in {'.io','.scm','.ss'}: raise ValueError('source file must be .io, .scm, or .ss')
  import tempfile
  with tempfile.NamedTemporaryFile('w',suffix=Path(filename).suffix,encoding='utf-8') as file:
   file.write(source); file.flush(); command=[sys.executable,str(GENERATOR),'compile',file.name,str(payload.get('name',''))]
   result=subprocess.run(command,capture_output=True,text=True,timeout=130)
  if result.returncode: raise ValueError((result.stderr or result.stdout).strip())
  return json.loads(result.stdout)
 command=[sys.executable,str(GENERATOR),'generate',str(payload.get('shape','')),str(payload.get('name',''))]
 for key in ('radius','size','minor'):
  if key in payload: command.extend([f'--{key}',str(payload[key])])
 result=subprocess.run(command,capture_output=True,text=True,timeout=130)
 if result.returncode: raise ValueError((result.stderr or result.stdout).strip())
 return json.loads(result.stdout)

class Handler(BaseHTTPRequestHandler):
 def send_json(self,code,value):
  body=json.dumps(value).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
 def do_GET(self):
  if self.path.rstrip('/')!='/status': return self.send_json(404,{'error':'not found'})
  try: self.send_json(200,status())
  except Exception as error: self.send_json(503,{'error':str(error)})
 def do_POST(self):
  if self.path.rstrip('/')!='/generate': return self.send_json(404,{'error':'not found'})
  try:
   length=int(self.headers.get('Content-Length','0')); assert 0<length<=70000
   self.send_json(201,generate(json.loads(self.rfile.read(length))))
  except Exception as error: self.send_json(400,{'error':str(error)})
 def log_message(self,format,*args): pass

def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--host',default='127.0.0.1'); parser.add_argument('--port',type=int,default=4787); args=parser.parse_args()
 ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()
if __name__=='__main__': main()
