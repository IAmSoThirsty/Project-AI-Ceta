from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
F=Path('T:/00-Active/Project-AI-CETA')
label=Path(sys.argv[1]);cmd=sys.argv[2:]
assert label.is_absolute() and label.is_relative_to(F/'.agents/runtime/oq23') and cmd
assert sys.flags.optimize==0
out=Path(str(label)+'.stdout');err=Path(str(label)+'.stderr');record=Path(str(label)+'-PROCESS.json');assert not record.exists()
started=datetime.now(timezone.utc).isoformat();t=time.perf_counter_ns()
with out.open('xb') as so,err.open('xb') as se:
 child=subprocess.Popen(cmd,cwd=F,stdin=subprocess.DEVNULL,stdout=so,stderr=se,creationflags=subprocess.CREATE_NO_WINDOW)
 status=child.wait();so.flush();os.fsync(so.fileno());se.flush();os.fsync(se.fileno())
v=dict(argv=cmd,cwd=str(F),pid=child.pid,started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),elapsed_ns=time.perf_counter_ns()-t,actual_process_exit_status=status,signal=None,stdout_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),stderr_sha256=hashlib.sha256(err.read_bytes()).hexdigest())
with record.open('xb') as w:w.write((json.dumps(v,indent=2)+'\n').encode());w.flush();os.fsync(w.fileno())
print(json.dumps(v));raise SystemExit(status)
