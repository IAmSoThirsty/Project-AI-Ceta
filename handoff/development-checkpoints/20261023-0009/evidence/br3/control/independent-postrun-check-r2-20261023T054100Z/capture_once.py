from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
OUT=Path(__file__).parent;F=Path('T:/00-Active/Project-AI-CETA');PY=F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
argv=[str(PY),'-E','-B','-X','utf8',str(OUT/'check_once.py')]
started=datetime.now(timezone.utc).isoformat();mono=time.perf_counter_ns()
with (OUT/'stdout.txt').open('xb') as stdout,(OUT/'stderr.txt').open('xb') as stderr:
    process=subprocess.Popen(argv,cwd=str(F),stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
    code=process.wait()
receipt=dict(argv=argv,cwd=str(F),pid=process.pid,wrapper_pid=os.getpid(),started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),elapsed_monotonic_ns=time.perf_counter_ns()-mono,actual_process_exit_status=code,script_sha256=hashlib.sha256((OUT/'check_once.py').read_bytes()).hexdigest(),stdout_sha256=hashlib.sha256((OUT/'stdout.txt').read_bytes()).hexdigest(),stderr_sha256=hashlib.sha256((OUT/'stderr.txt').read_bytes()).hexdigest(),report_sha256=hashlib.sha256((OUT/'REPORT.json').read_bytes()).hexdigest() if (OUT/'REPORT.json').exists() else None,canonical_test_bodies_executed=0,claims_or_gate_or_release_or_bootstrap_actions=0)
with (OUT/'PROCESS.json').open('x',encoding='utf8',newline='\n') as stream:json.dump(receipt,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
print(json.dumps(receipt,sort_keys=True));raise SystemExit(code)
