"""Run only the private deterministic capture tests with native effects denied."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes
import hashlib,json,sys,threading,traceback,unittest
F=Path('T:/00-Active/Project-AI-CETA');Q=F/'.agents/ac7-loader-capture-20261020'
R=Path(__file__).resolve().parent
before={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in Q.glob('*.py')}
attempt='pure-r2';out=R/attempt;out.mkdir(exist_ok=False)
denied=[]
def audit(event,args):
    if event.startswith(('subprocess.','socket.','winreg.')) or event in ('ctypes.dlopen','sqlite3.connect','os.system','os.startfile'):
        denied.append(dict(event=event,args=[str(value) for value in args]));raise RuntimeError('PURE_CAPTURE_EFFECT_DENIED:'+event)
sys.addaudithook(audit)
sys.path.insert(0,str(Q));loader=unittest.TestLoader();suite=loader.discover(str(Q),pattern='test_loader_capture.py')
def ids(group):
    if isinstance(group,unittest.TestSuite):
        for item in group:yield from ids(item)
    else:yield group.id()
expected=list(ids(suite));threads=set(threading.enumerate());started=datetime.now(timezone.utc).isoformat()
with (out/'RAW.txt').open('x',encoding='utf8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
after={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in Q.glob('*.py')}
remaining=[row.name for row in set(threading.enumerate())-threads if row.is_alive()]
passed=result.wasSuccessful() and result.testsRun==len(expected) and not result.skipped and not loader.errors and not denied and not remaining and before==after
report=dict(started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),
    argv=list(sys.orig_argv),sys_executable=sys.executable,sys_base_executable=sys._base_executable,
    expected_ids=expected,tests_run=result.testsRun,failures=[(test.id(),detail) for test,detail in result.failures],
    errors=[(test.id(),detail) for test,detail in result.errors],skips=[(test.id(),reason) for test,reason in result.skipped],
    loader_errors=loader.errors,denied_calls=denied,remaining_threads=remaining,
    before_hashes=before,after_hashes=after,code_unchanged=before==after,
    real_debug_worker_profile_registry_network_SQLite_calls=0,fixture_native_functions_are_controlled=True,
    actual_native_qualification=False,exit_status=0 if passed else 1)
with (out/'RESULT.json').open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(dict(tests_run=result.testsRun,passed=passed,failures=len(result.failures),errors=len(result.errors),
    result=str(out/'RESULT.json'),sha256=hashlib.sha256((out/'RESULT.json').read_bytes()).hexdigest())),flush=True)
sys.exit(report['exit_status'])
