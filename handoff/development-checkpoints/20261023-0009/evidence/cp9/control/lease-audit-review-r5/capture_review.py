"""Create-only review process evidence and prior/source conservation."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys,time
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[D.parent/'lease_audit_r5.py',D.parent/'lease_audit_r4.py',D.parent/'lease_audit_r4-before-normalized-review-policy.py',
    D.parent.parent/'work/exact_git_scope.py']
for directory in ('lease-audit-review','lease-audit-review-r3','lease-audit-review-r4'):
    paths.extend(p for p in (D.parent/directory).rglob('*') if p.is_file())
before={str(p):dict(sha256=sha(p),bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns) for p in paths}
command=[sys.executable,'-B','-X','utf8',str(D/'review_controls.py')]
started=datetime.now(timezone.utc).isoformat();tick=time.perf_counter_ns()
result=subprocess.run(command,cwd=D,capture_output=True)
elapsed=time.perf_counter_ns()-tick
for suffix,raw in (('stdout',result.stdout),('stderr',result.stderr)):
    with (D/('CONTROLS.'+suffix)).open('xb') as stream:stream.write(raw)
after={str(p):dict(sha256=sha(p),bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns) for p in paths}
conserved=before==after
record=dict(command=command,cwd=str(D),started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),
    elapsed_ns=elapsed,exit_status=result.returncode,stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
    stderr_sha256=hashlib.sha256(result.stderr).hexdigest(),prior_and_sources_conserved=conserved,
    source_and_prior_before=before,source_and_prior_after=after)
with (D/'PROCESS.json').open('x',encoding='utf8') as stream:json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps(dict(exit_status=result.returncode,prior_and_sources_conserved=conserved,
    process_sha256=sha(D/'PROCESS.json'),stdout=result.stdout.decode('utf8'),stderr=result.stderr.decode('utf8'))))
assert conserved
raise SystemExit(result.returncode)
