"""Root one-attempt launcher; reviewed manifest and actual child exit retained."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys
J=Path(__file__).resolve().parents[1]
F=Path('T:/00-Active/Project-AI-CETA')
assert J==F/'.agents/runtime/oq23/br3'
assert Path(__file__).resolve().parent==J/'control'
assert len(sys.argv)==2
pin=sys.argv[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(J/'work/MANIFEST.json')==pin
assert sys.flags.optimize==0
packet=json.loads((J/'packet/INPUTS.json').read_bytes())
assert Path(sys.executable).resolve()==Path(packet['python']).resolve()
def save(name,value):
    raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
    with (J/'control'/name).open('xb') as stream:
        assert stream.write(raw)==len(raw);stream.flush();os.fsync(stream.fileno())
assert not (J/'control/EXECUTION-INTENT.json').exists()
assert not any((J/'delivery').iterdir())
removed=sorted(k for k in os.environ if k.startswith('CETA_') or k in ('PYTHONPATH','PYTHONHOME','PYTHONOPTIMIZE'))
env={k:v for k,v in os.environ.items() if k not in removed}
env.update(PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false')
argv=[sys.executable,'-B','-X','utf8',str(J/'work/run_broader.py'),'--manifest-sha256',pin]
save('EXECUTION-INTENT.json',dict(started_at=datetime.now(timezone.utc).isoformat(),argv=argv,cwd=str(F),manifest_sha256=pin,removed_environment_names=removed,assertions_enabled=True,one_attempt=True,full_product_acceptance=False))
completed=subprocess.run(argv,cwd=F,env=env,capture_output=True)
for name,raw in [('EXECUTION.stdout',completed.stdout),('EXECUTION.stderr',completed.stderr)]:
    with (J/'control'/name).open('xb') as stream:
        assert stream.write(raw)==len(raw);stream.flush();os.fsync(stream.fileno())
save('EXECUTION-PROCESS.json',dict(finished_at=datetime.now(timezone.utc).isoformat(),argv=argv,cwd=str(F),exit_status=completed.returncode,stdout_sha256=sha(J/'control/EXECUTION.stdout'),stderr_sha256=sha(J/'control/EXECUTION.stderr'),manifest_sha256=pin,full_product_acceptance=False))
print(json.dumps(dict(exit_status=completed.returncode,manifest_sha256=pin,full_product_acceptance=False)))
raise SystemExit(completed.returncode)
