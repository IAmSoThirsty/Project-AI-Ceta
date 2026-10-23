"""Bounded Root entrypoint controls; no canonical or Git writes."""
import os,sys,json,hashlib,subprocess
from pathlib import Path
from datetime import datetime,timezone
if sys.flags.optimize != 0: raise RuntimeError('control driver requires unoptimized Python')
F=Path('T:/00-Active/Project-AI-CETA');C=F/'.agents/runtime/oq23/cp9/control'
expected={'ROOT-CLOSE-PREPARATION.py':'c1ee67072c944103a08826f8150c13d7e6333da575c2766f1f53d29c8a11f2aa','SETUP-PUBLICATION.py':'3d84d3c5af824dd7b7b79f5ca2600e5e86923a41e4f1edcca2b39d98799c0983','ROOT-PUBLICATION.py':'7cecf4f135faf05d1a063154b3d1d89f97f7fa561a60332fcf4c67c8a0edf147'}
rows=[]
for name,pin in expected.items():
 path=C/name;raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=pin: raise RuntimeError('source changed: '+name)
 source=raw.decode();prefix=source.split('from pathlib import Path',1)[0]
 for optimize in ('-O','-OO'):
  argv=[sys.executable,'-E','-B',optimize,'-X','utf8',str(path)]
  p=subprocess.run(argv,cwd=F,stdin=subprocess.DEVNULL,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
  passed=p.returncode!=0 and not p.stdout and b'CP9 requires unoptimized Python before imports or effects' in p.stderr
  rows.append(dict(name=name+' explicit '+optimize,argv=argv,actual_exit_status=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode(),passed=passed))
 env=os.environ.copy();env['PYTHONOPTIMIZE']='2'
 argv=[sys.executable,'-E','-B','-X','utf8','-c',prefix+"import json;print(json.dumps(dict(optimize=sys.flags.optimize,inherited='PYTHONOPTIMIZE' in os.environ)))"]
 p=subprocess.run(argv,cwd=F,env=env,stdin=subprocess.DEVNULL,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
 data=json.loads(p.stdout) if p.returncode==0 else None
 rows.append(dict(name=name+' exact prefix child environment scrub',argv=argv,actual_exit_status=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode(),passed=data==dict(optimize=0,inherited=False)))
value=dict(recorded_at=datetime.now(timezone.utc).isoformat(),author='/root',independent_review=False,source_pins=expected,controls=len(rows),rows=rows,passed=all(r['passed'] for r in rows),canonical_mutation=False,publication=False)
raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
with (C/'ROOT-INTERPRETER-CONTROLS-R3.json').open('xb') as stream:
 written=stream.write(raw)
 if written!=len(raw):raise OSError('short evidence write')
 stream.flush();os.fsync(stream.fileno())
print(json.dumps(dict(controls=len(rows),passed=value['passed'])))
raise SystemExit(0 if value['passed'] else 1)
