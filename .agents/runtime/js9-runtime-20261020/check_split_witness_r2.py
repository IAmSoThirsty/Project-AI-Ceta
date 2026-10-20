"""Data-only exact-function controls for the repaired split witness.

No release file, candidate module, Git process, native worker or actual source
observation is synthesized as live evidence. All mappings below are explicitly
synthetic function inputs; only the acceptance predicates execute.
"""
from pathlib import Path
import ast,copy,hashlib,json,os,sys
from types import SimpleNamespace

F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent;D=R/'successor-r2'
Q=F/'.agents/js9-runtime-20261020';PY=F/'.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
packet=json.loads((D/'PACKET.json').read_bytes())
env=json.loads((D/'ENVIRONMENT.json').read_bytes())
before=json.loads((D/'SOURCE-BEFORE.json').read_bytes())
manifest=json.loads((R/'MANIFEST-R4.json').read_bytes())
pref=dict(repository_relative_path=(D/'PACKET.json').relative_to(F).as_posix(),sha256=sha(D/'PACKET.json'))
results=[]
def load(path,name,namespace):
    tree=ast.parse(path.read_bytes());node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path)+'#exact-data-control','exec'),namespace)
    return namespace[name]
def check(name,operation,allowed=True):
    try:operation();observed=True;error=None
    except (AssertionError,RuntimeError,KeyError,TypeError) as exc:observed=False;error=type(exc).__name__+': '+str(exc)
    assert observed is allowed,(name,observed,error)
    results.append(dict(case=name,passed=True,allowed=observed,diagnostic=error))

facts={Q/name:dict(sha256=pin) for name,pin in manifest['payload_hashes'].items()}
facts.update({F/name:row for name,row in before['targets'].items() if row is not None})
facts.update({Path(row['path']):row for row in packet['fixture_dependencies'].values()})
facts.update({Path(env['python']['path']):env['python'],Path(env['base_python']['path']):env['base_python']})
def lstat(path):
    if Path(path) not in facts:raise FileNotFoundError(str(path))
    return object()
for phase,filename in [('native-store','run_native_store.py'),('native-observer','run_native_observer.py'),('parent',None)]:
    blocked=[];calls=[]
    if filename:
        audit=load(D/filename,'audit',dict(Path=Path,os=os,output=D/'PURE_NO_REAL_OUTPUT',blocked=blocked,forbidden=blocked,loads=[]))
    else:audit=lambda *args:None
    def git(root,*args):
        calls.append(list(args));audit('subprocess.Popen',('PURE_GIT_EVENT_ONLY',))
        return packet['Git']['HEAD' if args==('rev-parse','HEAD') else 'branch']
    ns=dict(Path=Path,sys=sys,os=os,F=F,Q=Q,PY=PY,packet=lambda:packet,
        manifest=lambda:dict(expected_payload_hashes=manifest['payload_hashes']),inputs=lambda:env,
        proof=lambda reference:(None,before),inventory=lambda root:env['environment_files'],
        s=SimpleNamespace(ordinary=lambda path:facts[Path(path)],fs=SimpleNamespace(lstat=lstat,text_git=git)))
    verify=load(D/'js9_support.py','verify',ns)
    if filename:
        def native_post():
            value=verify(verify_git=False)
            assert value['Git_observed'] is None and not calls and not blocked
        check(phase+'_post_CAS_without_Git_subprocess',native_post)
        check(phase+'_default_Git_remains_forbidden_inside_same_audit',lambda:verify(),False)
        assert calls==[['rev-parse','HEAD']] and len(blocked)==1
    else:
        def parent_default():
            value=verify()
            assert value['Git_observed']==packet['Git']
            assert calls==[['rev-parse','HEAD'],['branch','--show-current']]
        check('parent_default_executes_both_real_code_Git_calls_with_synthetic_dispatch',parent_default)

# Actual terminal/corroboration predicates with strictly in-memory records.
label='PURE_NOT_A_REAL_PROCESS'
tref=dict(repository_relative_path=(D/label/'RESULT.json').relative_to(F).as_posix(),sha256='1'*64)
rref=dict(repository_relative_path=(D/'releases/PURE_NOT_A_RELEASE.json').relative_to(F).as_posix(),sha256='2'*64)
cref=dict(repository_relative_path=(D/'PURE_NOT_A_CORROBORATION.json').relative_to(F).as_posix(),sha256='3'*64)
observed=dict(sys_executable=env['python']['path'],sys_base_executable=env['base_python']['path'],python=env['python'],base_python=env['base_python'])
argv=[str(PY),'-B','-X','utf8',str(D/'run_native_store.py'),label,'--release-path',str(D/'releases/PURE_NOT_A_RELEASE.json'),'--release-sha256','2'*64]
terminal=dict(phase='native-store',packet=pref,candidate_manifest=packet['candidate_manifest'],
    runner_sha256=packet['scripts']['run_native_store.py'],passed=True,post_CAS_verified=True,
    acceptance_complete=False,Git_corroboration=dict(status='PENDING_ROOT_CORROBORATION',before=packet['Git'],after=None),
    interpreter=observed,expected_ids=packet['native_store_ids'],tests_run=18,
    events=[dict(event=event,id=name) for name in packet['native_store_ids'] for event in ('START','STOP')],
    failures=[],errors=[],skips=[],primary_error=None,remaining_threads=[],boundary_violations=[],
    physical_custody=dict(owned_resources_closed=True),binding_custody=[dict(closed=True,pending=[])],
    release=rref,observed_argv=[env['base_python']['path'],*argv[1:]],cwd=str(D))
corroboration=dict(phase='native-store',accepted=True,status='ACCEPTED_NATIVE_ENGINEERING_SCOPE',packet=pref,
    candidate_manifest=packet['candidate_manifest'],native_terminal=tref,native_release=rref,exit_status=0,primary_error=None,
    parent_runner_sha256=packet['scripts']['launch_native.py'],native_child_process=dict(child_exit=0,child_result=tref,
        primary_error=None,retirement_error=None,native_owner_after=dict(closed=True,process_closed=True,job_closed=True,thread_closed=True),
        native_owner=dict(image_sha256=env['python']['sha256'],pid=405,creation_time=406)),
    native_child_argv=argv,native_child_cwd=str(D),Git_observed=packet['Git'],environment=packet['environment'],
    Source_before=packet['Source_before'],Source_observed=before['targets'],fixture_dependencies_observed=packet['fixture_dependencies'],
    interpreter=observed,started_at_ns=2,finished_at_ns=3,source_publication=False,product_acceptance=False)
store={'terminal':terminal,'corroboration':corroboration}
def proof(reference):
    if reference==tref:return D/label/'RESULT.json',store['terminal']
    if reference==cref:return D/'PURE_NOT_A_CORROBORATION.json',store['corroboration']
    if reference==packet['Source_before']:return D/'SOURCE-BEFORE.json',before
    if reference==rref:return D/'releases/PURE_NOT_A_RELEASE.json',dict(issued_at_ns=1,expires_at_ns=100)
    raise AssertionError('UNKNOWN_SYNTHETIC_PROOF')
ns=dict(Path=Path,F=F,R=D,packet=lambda:packet,proof=proof,
    exact_ref=lambda path:pref,inputs=lambda:env,interpreter_observation=lambda value:observed,
    proof_bytes=lambda reference:(D/'releases/PURE_NOT_A_RELEASE.json',b''))
load(D/'js9_support.py','require_native_terminal',ns)
require=load(D/'js9_support.py','require_native_corroboration',ns)
check('complete_synthetic_parent_witness_shape',lambda:require(cref,'native-store'))
for name,change in [
    ('nonzero_actual_child_exit',lambda t,c:c['native_child_process'].update(child_exit=1)),
    ('unretired_child_job',lambda t,c:c['native_child_process']['native_owner_after'].update(job_closed=False)),
    ('wrong_child_image',lambda t,c:c['native_child_process']['native_owner'].update(image_sha256='0'*64)),
    ('wrong_child_command',lambda t,c:c['native_child_argv'].__setitem__(4,str(D/'other.py'))),
    ('failed_child_receipt',lambda t,c:t.update(passed=False)),
    ('missing_Git_observation',lambda t,c:c.update(Git_observed=None)),
    ('mismatched_parent_packet',lambda t,c:c.update(packet=dict(repository_relative_path='PURE_WRONG',sha256='0'*64))),
    ('mismatched_parent_source',lambda t,c:c.update(Source_observed={})),
    ('mismatched_child_interpreter',lambda t,c:t.update(interpreter={})),
    ('wrong_exact_case_ids',lambda t,c:t.update(expected_ids=[])),
    ('pending_parent_outcome',lambda t,c:c.update(accepted=False)),
]:
    t=copy.deepcopy(terminal);c=copy.deepcopy(corroboration);change(t,c)
    store['terminal']=t;store['corroboration']=c
    check(name+'_denied',lambda:require(cref,'native-store'),False)

# Exact downstream release function must demand both witnesses before admission.
for phase in ('candidate-full','destination-full','publish'):
    value=dict(schema_version=1,executor='/root',run_id='js9-runtime-20261020',phase=phase,
        packet=pref,candidate_manifest=packet['candidate_manifest'],reviewed_scripts=packet['scripts'],
        case_set=packet['case_set'],Source_before=packet['Source_before'],automatic_retry=False,create_profiles=False,
        Source_publication=phase=='publish',all_conflicting_Source_pinned_runs_released=True,
        issued_at_ns=1,expires_at_ns=100,independent_review='PURE_REVIEW',native_case_release=rref,
        native_store_corroboration='PURE_STORE_WITNESS',native_observer_corroboration='PURE_OBSERVER_WITNESS')
    review=dict(reviewer='/root/PURE_REVIEWER',author='/root/recovery_regression20',decision='approved',exit_status=0,
        packet=pref,reviewed_scripts=packet['scripts'],candidate_manifest=packet['candidate_manifest'])
    calls=[];denied=None
    def witness(reference,scope):
        calls.append(scope)
        assert scope!=denied,'SYNTHETIC_FAILED_WITNESS'
    namespace=dict(Path=Path,R=D,RUN='js9-runtime-20261020',AUTHOR='/root/recovery_regression20',
        time=SimpleNamespace(time_ns=lambda:50),s=SimpleNamespace(fs=SimpleNamespace(safe_components=lambda p:p)),
        pinned_json=lambda path,pin:value,packet=lambda:packet,exact_ref=lambda path:pref,
        proof=lambda reference:(None,review),proof_bytes=lambda reference:(D/'releases/PURE_NOT_A_RELEASE.json',b''),
        require_native_corroboration=witness)
    admission=load(D/'js9_support.py','require_release',namespace)
    def both():
        calls.clear();admission(D/'releases/PURE_PHASE.json','PURE_PIN',phase)
        assert calls==['native-store','native-observer']
    check(phase+'_requires_both_parent_witness_callbacks',both)
    for denied in ('native-store','native-observer'):
        calls.clear();check(phase+'_'+denied+'_refusal_denies_admission',lambda:admission(D/'releases/PURE_PHASE.json','PURE_PIN',phase),False)

report=dict(scope='Exact AST functions; in-memory synthetic dispatch/data only; no authority or actual child receipt created',
    tests=len(results),all_passed=True,cases=results,packet_sha256=sha(D/'PACKET.json'),
    script_hashes={name:sha(D/name) for name in ['js9_support.py','run_native_store.py','run_native_observer.py','launch_native.py']},
    actual_Git_or_native_subprocesses=0,actual_product_tests=0,Source_or_Q_changes=False)
with (R/'SUCCESSOR-R2-SPLIT-WITNESS-CONTROLS.json').open('x',encoding='utf8') as stream:
    json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(dict(cases=len(results),all_passed=True,sha256=sha(R/'SUCCESSOR-R2-SPLIT-WITNESS-CONTROLS.json'))),flush=True)
