from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
D=Path(__file__).parent;argv=['T:/00-Active/Project-AI-CETA/.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe','-I','-B',str(D/'preflight.py')];start=datetime.now(timezone.utc).isoformat()
with (D/'stdout.txt').open('xb') as out,(D/'stderr.txt').open('xb') as err:p=subprocess.Popen(argv,cwd='T:/00-Active/Project-AI-CETA',stdout=out,stderr=err);rc=p.wait()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=dict(argv=argv,cwd='T:/00-Active/Project-AI-CETA',pid=p.pid,started_at=start,finished_at=datetime.now(timezone.utc).isoformat(),actual_process_exit_status=rc,stdout_sha256=sha(D/'stdout.txt'),stderr_sha256=sha(D/'stderr.txt'),script_sha256=sha(D/'preflight.py'))
if (D/'CONTROLS.json').exists():r['controls_sha256']=sha(D/'CONTROLS.json')
with (D/'PROCESS.json').open('x',encoding='utf-8') as h:json.dump(r,h,indent=2);h.write('\n')
print(json.dumps(r));raise SystemExit(rc)
