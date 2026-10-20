"""One benign test interpreter with exact canonical Windows job retirement."""
from foundation_support import *
import importlib.util

label=sys.argv[1]
mode=sys.argv[2];assert mode in ('all','diagnostics')
bound=240 if mode=='all' else 60
assert label.replace('-','').isalnum()
D=R/('supervision-'+label);assert not D.exists();D.mkdir();(D/'tmp').mkdir()
native_names=['src/ceta/__init__.py','src/ceta/supervisor/__init__.py',
    'src/ceta/supervisor/windows_jobs.py','src/ceta/contracts/__init__.py',
    'src/ceta/contracts/wire.py','src/ceta/contracts/resource_management.py']
names=set(read(R/'ASSEMBLY.json')['payloads'])
before={name:ordinary(Q/name) for name in sorted(names)}
pins={name:ordinary(F/name) for name in native_names}
inputs=dict(at=utc(),source_six_native_supervision_only=pins,interpreter=ordinary(PY),
    runner=ordinary(R/'run_controlled.py'),custody=ordinary(R/'bounded_custody.py'),
    candidate_payloads=before,argv=[str(PY),'-B','-X','utf8',str(R/'run_controlled.py'),label,mode],
    no_whole_Source_conservation_claim=True,child_wait_seconds=bound,
    host_profile_Hello_CPU_Set=False,engineering_process_only=True)
write_new(D/'PREPARED-INPUTS.json',inputs)
sys.path.insert(0,str(F/'src'))
from ceta.supervisor.windows_jobs import WindowsOwnedProcess
assert ordinary(Path(sys.modules['ceta.supervisor.windows_jobs'].__file__))==pins['src/ceta/supervisor/windows_jobs.py']
spec=importlib.util.spec_from_file_location('ka5_bounded_custody',R/'bounded_custody.py')
custody=importlib.util.module_from_spec(spec);spec.loader.exec_module(custody)
write_new(D/'ATTEMPT.json',dict(at=utc(),prepared=reference(D/'PREPARED-INPUTS.json'),
    automatic_retry=False,ordinary_python_harness=True))
def launch():
    return WindowsOwnedProcess.launch(str(PY),('-B','-X','utf8',str(R/'run_controlled.py'),label,mode),cwd=str(D),
        environment={'SystemRoot':os.environ['SystemRoot'],'TEMP':str(D/'tmp'),'TMP':str(D/'tmp'),
                     'PYTHONDONTWRITEBYTECODE':'1'},expected_image_sha256=inputs['interpreter']['sha256'])
def emit(row):write_new(D/'OWNED-RUNNER.json',row)
def child():
    result=read(R/label/'RESULT.json')
    assert result['exit_status']==0 and result['tests_run']==(82 if mode=='all' else 10),result
    return reference(R/label/'RESULT.json')
primary=None;record=None
try:
    record=custody.run_owned(launch,emit,child,timeout=bound)
    assert record['child_exit']==0
except BaseException as error:
    primary=error
    record=dict.get(BaseException.__dict__['__dict__'].__get__(error),'full_runner_report',record)
after={name:ordinary(Q/name) for name in sorted(names)}
native_after={name:ordinary(F/name) for name in native_names}
preserved=before==after and pins==native_after
write_new(D/'SUPERVISION-RESULT.json',dict(at=utc(),record=record,
    primary=None if primary is None else custody.failure(primary),
    candidate_before=before,candidate_after=after,source_six_before=pins,source_six_after=native_after,
    current_Source_scope='Only six read-only native-supervisor import files, not whole Source',
    candidate_and_six_source_files_preserved=preserved,exit_status=0 if primary is None and preserved else 1,
    synchronous_native_launch_close_not_preempted=True,no_retry=True))
print(json.dumps(dict(primary=None if primary is None else custody.failure(primary),
    preserved=preserved,record=record,exit_status=0 if primary is None and preserved else 1)),flush=True)
if primary is not None:raise primary
assert preserved
