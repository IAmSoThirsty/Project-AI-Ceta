"""One actual ST2 child invocation with explicitly accepted handle qualification."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys
F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';C=S/'control';W=S/'work'
if sys.flags.optimize:raise RuntimeError('OPTIMIZED_INTERPRETER_REFUSED')
packet=json.loads((S/'packet/INPUTS.json').read_bytes())
if Path(sys.executable).resolve()!=Path(packet['python']).resolve():raise RuntimeError('UNPINNED_INTERPRETER_REFUSED')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 raw=(json.dumps(v,indent=2,allow_nan=False)+'\n').encode()
 with p.open('xb') as f:assert f.write(raw)==len(raw);f.flush();os.fsync(f.fileno())
assert len(sys.argv)==2;pin=sys.argv[1];assert sha(W/'MANIFEST.json')==pin and not any((S/'delivery').iterdir()) and not (C/'EXECUTION-INTENT.json').exists()
amendment=json.loads((C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json').read_bytes());approval=json.loads((C/'INDEPENDENT-HANDLE-EXECUTION-APPROVAL.json').read_bytes());assert amendment['prepared_manifest_sha256']==pin and amendment['launcher_sha256']==sha(Path(__file__)) and approval['amendment_sha256']==sha(C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json') and approval['launcher_sha256']==sha(Path(__file__)) and approval['decision']=='APPROVED_EXACT_F_ONLY_HANDLE_QUALIFICATION'
removed=sorted(k for k in os.environ if k.startswith('CETA_') or k in ('PYTHONPATH','PYTHONHOME','PYTHONOPTIMIZE'));env={k:v for k,v in os.environ.items() if k not in removed};env.update(PYTHONDONTWRITEBYTECODE='1',GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false')
argv=[sys.executable,'-B','-X','utf8',str(C/'run_handle_qualified.py'),'--manifest-sha256',pin,'--action','apply'];save(C/'EXECUTION-INTENT.json',dict(started_at=datetime.now(timezone.utc).isoformat(),argv=argv,cwd=str(F),manifest_sha256=pin,observation_amendment_sha256=sha(C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json'),removed_environment_names=removed,assertions_enabled=True,one_attempt=True,full_product_acceptance=False));p=subprocess.run(argv,cwd=F,env=env,capture_output=True)
for name,raw in [('EXECUTION.stdout',p.stdout),('EXECUTION.stderr',p.stderr)]:
 with (C/name).open('xb') as f:assert f.write(raw)==len(raw);f.flush();os.fsync(f.fileno())
save(C/'EXECUTION-PROCESS.json',dict(finished_at=datetime.now(timezone.utc).isoformat(),argv=argv,cwd=str(F),exit_status=p.returncode,manifest_sha256=pin,observation_amendment_sha256=sha(C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json'),stdout_sha256=sha(C/'EXECUTION.stdout'),stderr_sha256=sha(C/'EXECUTION.stderr'),full_product_acceptance=False));print(json.dumps(dict(exit_status=p.returncode,manifest_sha256=pin,observation_amendment_sha256=sha(C/'HANDLE-QUALIFIED-EXECUTION-AMENDMENT.json'))));raise SystemExit(p.returncode)
