"""Independent frozen AC7 review: data/AST only; never imports the real host tool."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import contextlib
import ctypes as C
import hashlib
import importlib.util
import io
import json
import os
import stat
import sys
import types
import unittest
from unittest.mock import patch

F=Path('T:/00-Active/Project-AI-CETA').resolve(strict=True)
Q=F/'.agents/ac7-token-contract-20261020'
R=F/'.agents/runtime/ac7-token-contract-20261020'
D=Path(__file__).resolve(strict=True).parent
assert D==F/'.agents/runtime/ac7-qualification-review-20261020/R2'
assert not (D/'PURE-RESULT.json').exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
M=R/'AC7-QUALIFICATION-MANIFEST-R4.json'
MPIN='83967d7b5c00abc6461cdcb9bbe398bb63b0ab53078d8364f56f383de9b511cf'
assert sha(M)==MPIN
manifest=json.loads(M.read_bytes());expected=manifest['payload_hashes']
assert len(expected)==357
def inventory(root,names):
    out={}
    for n in names:
        p=(root/n).resolve(strict=True);assert p.is_relative_to(root)
        out[n]=sha(p)
    return out
before=inventory(Q,expected);assert before==expected
evidence={n:sha(R/n) for n in manifest['evidence']}
assert evidence==manifest['evidence']
baseline=json.loads((R/'CANDIDATE-BASELINE-R4.json').read_bytes())['candidate352']
source=json.loads((F/'.agents/runtime/js8-20261015/amendment-report1/active-application/APPLIED.json').read_bytes())['source352']
assert len(baseline)==len(source)==352
def native_identity(p):
    s=p.lstat();assert stat.S_ISREG(s.st_mode) and not getattr(s,'st_file_attributes',0)&1024
    return dict(bytes=s.st_size,mtime_ns=s.st_mtime_ns,mode=stat.S_IMODE(s.st_mode),
        device=s.st_dev,inode=s.st_ino,attributes=getattr(s,'st_file_attributes',0))
for n,facts in baseline.items():
    assert before[n]==facts['sha256'] and native_identity(Q/n)==facts['native_identity']
source_before=inventory(F,source)
assert all(source_before[n]==facts['sha256'] and native_identity(F/n)==facts['native_identity'] for n,facts in source.items())

blocked=[]
def audit(event,args):
    if event in {'subprocess.Popen','os.system','os.startfile','sqlite3.connect',
                 'socket.__new__','ctypes.dlopen','ctypes.dlsym'}:
        blocked.append(event);raise AssertionError('REVIEW_EXCLUDED_'+event)
    if event=='open':
        p,mode,flags=args
        if (flags or 0)&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            assert Path(p).resolve().is_relative_to(D),'REVIEW_WRITE_SCOPE'
    if event in {'os.remove','os.rmdir'}:
        assert Path(args[0]).resolve().is_relative_to(D),'REVIEW_OWN_FIXTURE_CLEANUP_SCOPE'
sys.addaudithook(audit)
def deny(*args,**kw):blocked.append('WinDLL');raise AssertionError('NO_NATIVE_LIBRARY_LOADING')
C.WinDLL=deny;sys.dont_write_bytecode=True
sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
entry=load('independent_ac7_entry',Q/'tests/contract/test_isolation_qualification_entry.py')
# Sole fixture adaptation: TemporaryDirectory must stay in the reviewer scope.
import tempfile
real_temporary_directory=entry.TemporaryDirectory
def owned_temporary_directory(*args,**kw):
    kw['dir']=D
    return real_temporary_directory(*args,**kw)
entry.TemporaryDirectory=owned_temporary_directory
suite=unittest.defaultTestLoader.loadTestsFromNames([
 'test_isolated_worker.IsolationFactsContractTests',
 'test_isolation_token_diagnostics.IsolationTokenDiagnosticTests',
 'test_isolation_token_diagnostics.DiagnosticTestCustodyControls',
 'test_isolation_qualification_oracle.IsolationQualificationOracleTests'])
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(entry.QualificationEntryGateTests))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(entry.DriverLivenessTransformTests))
def flat(s):
    for t in s:
        if isinstance(t,unittest.TestSuite):yield from flat(t)
        else:yield t
ids=[t.id() for t in flat(suite)];assert len(ids)==len(set(ids))==47
started=datetime.now(timezone.utc).isoformat()
entered=[];stopped=[]
class Recorder(unittest.TextTestResult):
    def startTest(self,t):entered.append(t.id());super().startTest(t)
    def stopTest(self,t):stopped.append(t.id());super().stopTest(t)
with (D/'controlled47.txt').open('x',encoding='utf8') as stream:
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Recorder).run(suite)
assert result.wasSuccessful() and not result.skipped and entered==stopped==ids

oracle_fixture=sys.modules['test_isolation_qualification_oracle'];oracle=oracle_fixture.oracle
negative=[]
from copy import deepcopy
good=oracle_fixture.probe();oracle.assert_isolation(good,oracle_fixture.SID)
for name,mutate in [
 ('empty_process_rights',lambda r:r['facts'].__setitem__('process_rights',{})),
 ('missing_vm_write',lambda r:r['facts']['process_rights'].pop('vm_write')),
 ('count4096_both',lambda r:[x.update(restricted=True,restriction_raw_result=1,restricted_sid_count=4096) for x in (r['parent_token_facts'],r['facts']['token'])]),
 ('boolean_worker_flag',lambda r:r['facts']['token'].__setitem__('is_appcontainer',True)),
 ('duplicate_env',lambda r:r['facts']['environment_keys'].append('PATH')),
 ('missing_denial_result',lambda r:r['facts'].pop('denied_file_4'))]:
    row=deepcopy(good);mutate(row)
    try:oracle.assert_isolation(row,oracle_fixture.SID)
    except oracle.QualificationError as error:negative.append({'id':name,'rejected':True,'code':error.code})
    else:raise AssertionError(('ORACLE_NEGATIVE_ACCEPTED',name))

tool_path=Q/'tools/qualify_isolated_worker.py'
tool_ast=ast.parse(tool_path.read_text(encoding='utf8'))
old_ast=ast.parse((F/'.agents/runtime/ac6-profile-preparation-20261018/profile_qualification.py').read_text(encoding='utf8'))
old_class=next(n for n in old_ast.body if isinstance(n,ast.ClassDef) and n.name=='_QualificationRun')
new_class=next(n for n in tool_ast.body if isinstance(n,ast.ClassDef) and n.name=='_QualificationRun')
retained=['effect','retire','final_observations','execute','capture_failure_receipt','record']
for name in retained:
    old=next(n for n in old_class.body if isinstance(n,ast.FunctionDef) and n.name==name)
    new=next(n for n in new_class.body if isinstance(n,ast.FunctionDef) and n.name==name)
    assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False),name

# Execute the wrapper's exact non-import/non-location-assignment statements with
# explicit DATA_ONLY module/import/subprocess substitutions. No real host tool
# import, approval validator, inspection or subprocess is called.
wrapper=Q/'tools/run_one_isolation_qualification.py'
wrapper_ast=ast.parse(wrapper.read_text(encoding='utf8'))
body=[]
for n in wrapper_ast.body:
    if isinstance(n,(ast.Import,ast.ImportFrom)):continue
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'F','R','Q','PY'} for t in n.targets):continue
    body.append(n)
code=compile(ast.Module(body=body,type_ignores=[]),str(wrapper),'exec')
class ControlledExit(BaseException):
    def __init__(self,code):self.code=code
wrapper_results=[]
for label,change in [('success',{}),('wrong_wrapper',{'wrapper_sha256':'0'*64}),
                     ('self_review',{'reviewer':'/root'})]:
    wr=D/('wrapper-r4-'+label);wr.mkdir()
    proposal=wr/'PROFILE-CREATION-PROPOSAL-AC7-R4.json'
    proposal.write_bytes((R/proposal.name).read_bytes())
    review=dict(decision='approved',reviewer='/root/recovery_join_review20',
        tool_sha256=sha(tool_path),wrapper_sha256=sha(wrapper),proposal_sha256=sha(proposal),manifest_sha256=MPIN)
    review.update(change);calls=[]
    def save(path,value):
        assert Path(path).is_relative_to(wr)
        with Path(path).open('x',encoding='utf8') as output:json.dump(value,output)
    fake=types.SimpleNamespace(PROPOSAL=proposal,now=lambda:'DATA_ONLY_TIME',
        capture=lambda path,pin:(json.dumps(review).encode(),{'DATA_ONLY_identity':True}),
        validate_operator_record=lambda *a:calls.append('DATA_ONLY_approval'),
        inspect=lambda:({'prior_folder':{'HRESULT':-2147024894,'path':None}}),
        source_cut=lambda:{str(i):{'DATA_ONLY':True} for i in range(352)},
        candidate_cut=lambda:{str(i):{'DATA_ONLY':True} for i in range(352)},save=save)
    loader=types.SimpleNamespace(exec_module=lambda module:calls.append('DATA_ONLY_import'))
    util=types.SimpleNamespace(spec_from_file_location=lambda *a:types.SimpleNamespace(name='DATA_ONLY_module',loader=loader),
        module_from_spec=lambda spec:fake)
    def controlled_run(*a,**kw):
        calls.append('DATA_ONLY_child_dispatch');return types.SimpleNamespace(stdout=b'DATA_ONLY',stderr=b'',returncode=0)
    def stop(code):raise ControlledExit(code)
    ns=dict(Path=Path,hashlib=hashlib,importlib=types.SimpleNamespace(util=util),json=json,os=os,
        subprocess=types.SimpleNamespace(run=controlled_run),__file__=str(wrapper),
        F=F,R=wr,Q=Q,PY=Path(sys.executable),
        sys=types.SimpleNamespace(argv=[str(wrapper),str(wr/'NO_ACTUAL_APPROVAL'),'a'*64,
            str(wr/'NO_ACTUAL_REVIEW'),'b'*64],executable=sys.executable,
            flags=types.SimpleNamespace(optimize=0),modules={},stderr=io.StringIO()))
    ns['sys'].exit=stop
    with contextlib.redirect_stdout(io.StringIO()):
        try:exec(code,ns)
        except ControlledExit as end:assert end.code==0 and label=='success'
        except AssertionError:assert change and 'DATA_ONLY_child_dispatch' not in calls
        else:raise AssertionError('WRAPPER_DID_NOT_TERMINATE')
        first=list(calls)
        if label=='success':
            try:exec(code,ns)
            except AssertionError as error:assert 'PRIOR_ATTEMPT_MARKER_REFUSED' in str(error)
            else:raise AssertionError('WRAPPER_REENTRY_NOT_REJECTED')
            assert calls==first
    wrapper_results.append({'id':label,'controlled_calls':calls,
        'marker_written':(wr/'ONE-ATTEMPT-STARTED.json').exists(),'no_real_child':True})

build=json.loads((R/'build-r2/BUILD.json').read_bytes())
assert build['source']['sha256']==before['native/windows_broker/isolated_worker.rs']
assert build['native_image']['sha256']==evidence['build-r2/isolated_worker.exe']
assert all(c['exit_status']==0 for c in build['commands'])
assert build['commands'][-1]['stdout_sha256']==evidence['build-r2/pure-rust-tests.stdout']
assert b'5 passed; 0 failed; 0 ignored' in (R/'build-r2/pure-rust-tests.stdout').read_bytes()
assert inventory(Q,expected)==before and inventory(F,source)==source_before and sha(M)==MPIN
assert {n:sha(R/n) for n in manifest['evidence']}==evidence and not blocked
record=dict(schema='ceta-ac7-independent-successor-review-v1',actor='/root/recovery_join_review20',
 started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),
 command_argv=[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve())],
 manifest_sha256=MPIN,candidate357=before,candidate357_unchanged=True,
 source352_hash_and_native_identity_initial=True,source352_unchanged=True,
 candidate352_hash_and_native_identity_initial=True,existing_evidence_hashes=evidence,
 tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
 expected_ids=ids,entered_ids=entered,stopped_ids=stopped,raw_sha256=sha(D/'controlled47.txt'),
 additional_oracle_negatives=negative,wrapper_ast_controls=wrapper_results,
 retained_old_run_methods_ast_identical=retained,blocked_events=blocked,
 real_host_tool_imports=0,actual_profile_worker_listener_database_operations=[],
 rust_tests_rerun=0,real_subprocess_calls_inside_harness=0,
 adaptations=['Entry test TemporaryDirectory factory redirects only its directory argument to the reviewer scope; Q remains the real candidate for pure transform-source reads.',
  'Wrapper imports and F/R/Q/PY assignments replaced by explicit DATA_ONLY namespace; all remaining statements unchanged.',
  'Approval/review values inside controls are synthetic non-file values and authorize no host operation.'],
 limitations=['Static and DATA_ONLY evidence only; no native API boundary is qualified.',
  'Existing compiled Rust five-test receipts were source/image/output bound but not rerun.',
  'The real qualification tool import initializes its native reader and was not executed.'])
with (D/'PURE-RESULT.json').open('x',encoding='utf8') as out:json.dump(record,out,indent=2)
print(json.dumps(dict(tests=result.testsRun,extra_oracle_negatives=len(negative),
 wrapper_controls=len(wrapper_results),source352_unchanged=True,candidate357_unchanged=True,
 actual_native_operations=0,result_sha256=sha(D/'PURE-RESULT.json'))))
