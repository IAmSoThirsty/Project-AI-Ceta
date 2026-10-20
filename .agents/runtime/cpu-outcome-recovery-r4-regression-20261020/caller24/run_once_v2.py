"""One fresh reproduction of the frozen controlled24 regression, without product edits."""
from pathlib import Path
from datetime import datetime, timezone
import contextlib
import hashlib
import json
import os
import sys
import threading
import traceback
from scope_guard_v2 import sqlite_contained

F = Path('T:/00-Active/Project-AI-CETA').resolve()
R = Path(__file__).resolve().parent
OLD = F/'.agents/runtime/cpu-outcome-recovery-20261017'
CUT = F/'.agents/runtime/cpu-outcome-recovery-repair-20261020'
Q = F/'.agents/cpu-outcome-recovery-r4-20261020'
BASE = F/'.agents/runtime/js8-20261015/amendment-report1/ACCEPTED-SOURCE-BASELINE.json'
E3 = F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
started = now()
command = [str(E3), '-B', '-X', 'utf8', str(Path(__file__).resolve())]

def write(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')

write(R/'COMMAND.json', dict(at=started, actor='/root/recovery_regression20', command=command,
    cwd=str(F), pid=os.getpid(), executable=sys.executable, prefix=sys.prefix,
    base_prefix=sys.base_prefix, orig_argv=sys.orig_argv,
    execution='This wrapper executes the separately pinned adapted runner once in this interpreter.',
    scope='controlled24 only; no Source or candidate publication'))
assert sha(OLD/'HANDOFF.json') == '1669814ed47186d8774fbbc9b124bfd2b9c1e3f2b3ec5aab0d2f0096b3a4bbfa'
assert sha(CUT/'MANIFEST.json') == 'aa1ee89d9d0d63051b090590fea1d4391f9a4aad77ff8d8e92c6bfd04abe270e'
assert sha(R/'scope_guard_v2.py') == 'f90db473ae1abb2bea8762c8e8562f44b4df12149b0e08803025fa33d310df13'
assert sha(R/'CASESET.json') == '2700c815784b264158f8d351fc5c23d209c3e07eb318af5b5adad9dd63760433'
cases = json.loads((R/'CASESET.json').read_bytes())
assert sha(R/'run_controlled.py') == '3fed9083b4db8634674d6ef4edba31eff5cb274b09b58c811b9cc943e0c620da'
manifest = json.loads((CUT/'MANIFEST.json').read_bytes())
assert len(manifest['payload_hashes']) == 375
baseline = json.loads(BASE.read_bytes())
assert baseline['Source_accepted'] and baseline['Source_payloads'] == 352

def snapshot(root, mapping):
    return {name: sha(root/name) for name in mapping}

candidate_before = snapshot(Q, manifest['payload_hashes'])
source_before = snapshot(F, baseline['effective_payload_hashes'])
assert candidate_before == manifest['payload_hashes']
assert source_before == baseline['effective_payload_hashes']
threads_before = [(thread.ident, thread.name, thread.daemon) for thread in threading.enumerate()]
write(R/'BEFORE.json', dict(at=now(), manifest_sha256=sha(CUT/'MANIFEST.json'),
    accepted_baseline_sha256=sha(BASE), candidate=candidate_before, Source=source_before,
    threads=threads_before, runner_sha256=sha(R/'run_controlled.py'),
    old_failed_regression_sha256=sha(OLD/'regression-r1/RESULT.json'),
    prior_20261018_directory_exists=(F/'.agents/runtime/cpu-outcome-recovery-20261018').exists()))
violations = []

def contained(path):
    if isinstance(path, int): return True
    return Path(os.fsdecode(path)).resolve().is_relative_to(R)

def audit(event, args):
    violation = False
    if event == 'open':
        path, mode, flags = args
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            violation = not contained(path)
    elif event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.utime', 'os.truncate'):
        violation = not contained(args[0])
    elif event in ('os.rename', 'os.link', 'os.symlink'):
        violation = not contained(args[0]) or not contained(args[1])
    elif event in ('socket.__new__', 'socket.bind', 'socket.connect', 'socket.getaddrinfo'):
        violation = True
    elif event == 'sqlite3.connect':
        violation = not sqlite_contained(args[0], R)
    if violation:
        violations.append(dict(at=now(), event=event, arguments=repr(args)))
        raise RuntimeError('RECOVERY_REGRESSION_SCOPE_VIOLATION')

sys.addaudithook(audit)
namespace = dict(__name__='__main__', __file__=str(R/'run_controlled.py'))
old_argv = sys.argv
sys.argv = [str(R/'run_controlled.py'), 'controlled-r1']
primary = None
code = 1
try:
    with (R/'stdout.txt').open('x', encoding='utf8') as out, (R/'stderr.txt').open('x', encoding='utf8') as err:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            exec(compile((R/'run_controlled.py').read_bytes(), str(R/'run_controlled.py'), 'exec'), namespace)
except SystemExit as error:
    code = error.code if type(error.code) is int else 1
    if code != 0: primary = dict(type=type(error).__name__, value=str(error), traceback=traceback.format_exc())
except BaseException as error:
    primary = dict(type=type(error).__name__, value=str(error), traceback=traceback.format_exc())
finally:
    sys.argv = old_argv

diagnostics = []
candidate_after = source_after = None
for name, root, mapping in [('candidate', Q, manifest['payload_hashes']), ('Source', F, baseline['effective_payload_hashes'])]:
    try:
        value = snapshot(root, mapping)
        if name == 'candidate': candidate_after = value
        else: source_after = value
    except BaseException as error:
        diagnostics.append(dict(subject=name, type=type(error).__name__, value=str(error), traceback=traceback.format_exc()))
threads_after = [(thread.ident, thread.name, thread.daemon) for thread in threading.enumerate()]
new_threads = [row for row in threads_after if row not in threads_before]
result_path = R/'controlled-r1/RESULT.json'
result = json.loads(result_path.read_bytes()) if result_path.exists() else None
passed = (code == 0 and primary is None and not diagnostics and not violations and not new_threads
    and candidate_before == candidate_after and source_before == source_after
    and result is not None and result['exit_status'] == 0 and result['tests_run'] == 24
    and result['expected_ids'] == result['executed_ids'] == result['stopped_ids'] == cases['expected_ids'])
record = dict(started_at=started, finished_at=now(), actor='/root/recovery_regression20',
    command=command, pid=os.getpid(), runner_exit_status=code, primary_exception=primary,
    diagnostics=diagnostics, threads_before=threads_before, threads_after=threads_after,
    residual_threads=new_threads, scope_violations=violations,
    candidate_payloads=len(candidate_before), Source_payloads=len(source_before),
    candidate_unchanged=candidate_before == candidate_after, Source_unchanged=source_before == source_after,
    after_candidate=candidate_after, after_Source=source_after,
    result_path=str(result_path), result_sha256=sha(result_path) if result_path.exists() else None,
    stdout_sha256=sha(R/'stdout.txt'), stderr_sha256=sha(R/'stderr.txt'),
    exact_successor24_sequence=result is not None and result['expected_ids'] == result['executed_ids'] == result['stopped_ids'] == cases['expected_ids'],
    exact_original24_sequence=result is not None and result['executed_ids'] == cases['original24_ids'],
    source_publication=False, native_process_execution=False, production_authority_qualified=False,
    limits=['Real canonical SQLite; native owner/provenance/capacity/approval are CONTROLLED.',
        'The original subprocess crash test remains excluded; no native CPU effect runs.',
        'Tested endpoint hashes do not establish uninterrupted custody.',
        'No full product, Source acceptance or recovery integration is claimed.'],
    exit_status=0 if passed else 1)
write(R/'OUTER-RESULT.json', record)
print(json.dumps(dict(exit_status=record['exit_status'], result=str(result_path),
    result_sha256=record['result_sha256'], outer_sha256=sha(R/'OUTER-RESULT.json'),
    candidate_unchanged=record['candidate_unchanged'], Source_unchanged=record['Source_unchanged'],
    residual_threads=new_threads)))
raise SystemExit(record['exit_status'])
