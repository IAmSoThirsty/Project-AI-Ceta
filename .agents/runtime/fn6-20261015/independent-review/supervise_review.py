"""One exact owned ordinary interpreter; full native cleanup before final evidence."""
from review_support import *
import importlib.util
preflight()
D=V/'supervision-controlled-r1';assert not D.exists();D.mkdir();(D/'tmp').mkdir()
native_names=('src/ceta/__init__.py','src/ceta/supervisor/__init__.py','src/ceta/supervisor/windows_jobs.py',
    'src/ceta/contracts/__init__.py','src/ceta/contracts/wire.py','src/ceta/contracts/resource_management.py')
pins={name:ordinary(F/name) for name in native_names}
argv=[str(s.PY),'-B','-X','utf8',str(V/'execute_review.py'),'controlled']
write_new(D/'PREPARED-INPUTS.json',dict(at=utc(),source_six_native_supervision_only=pins,
    interpreter=ordinary(s.PY),argv=argv,timeout_seconds=240,Source_conservation_claim=False))
sys.path.insert(0,str(F/'src'))
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
assert ordinary(Path(sys.modules['ceta.supervisor.windows_jobs'].__file__))==pins['src/ceta/supervisor/windows_jobs.py']
spec=importlib.util.spec_from_file_location('fn6_review_bounded_custody',V/'bounded_custody.py')
custody=importlib.util.module_from_spec(spec);spec.loader.exec_module(custody)
def launch():
    return WindowsOwnedProcess.launch(str(s.PY),tuple(argv[1:]),cwd=str(D),
        environment={'SystemRoot':os.environ['SystemRoot'],'TEMP':str(D/'tmp'),'TMP':str(D/'tmp'),'PYTHONDONTWRITEBYTECODE':'1'},
        expected_image_sha256=ordinary(s.PY)['sha256'])
def emit(row):write_new(D/'OWNED-RUNNER.json',row)
def child():
    value=read(V/'controlled-r1/RESULT.json');proof=read(V/'PHYSICAL-controlled.json')
    assert value['exit_status']==0 and value['tests_run']==82 and proof['exit_status']==0
    return dict(result=reference(V/'controlled-r1/RESULT.json'),physical=reference(V/'PHYSICAL-controlled.json'))
primary=None;record=None
try:
    record=custody.run_owned(launch,emit,child,timeout=240)
    assert record['child_exit']==0
except BaseException as error:
    primary=error;record=dict.get(BaseException.__dict__['__dict__'].__get__(error),'full_runner_report',record)
native_after={name:ordinary(F/name) for name in native_names}
preflight()
write_new(D/'SUPERVISION-RESULT.json',dict(at=utc(),record=record,primary=None if primary is None else custody.failure(primary),
    source_six_before=pins,source_six_after=native_after,source_six_preserved=pins==native_after,
    no_retry=True,Source_full=False,Source_publication=False,exit_status=0 if primary is None and pins==native_after else 1))
if primary is not None:raise primary
assert pins==native_after
print(json.dumps(dict(exit_status=0,record=record)))
