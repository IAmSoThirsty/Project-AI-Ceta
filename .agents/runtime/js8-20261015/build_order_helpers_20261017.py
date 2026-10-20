"""Create reviewed-successor tooling; never edit the frozen JS8 source or tools."""
from pathlib import Path
import ast
import copy
import json
import sys

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import js8_support as parent
s, F = parent.s, parent.F
A = P/'amendment-order1'
Q = F/'.agents/js8-amendment-order1-20261017'
staged = parent.current_json(A/'STAGED.json')
original = parent.manifest()

def write(name, raw):
    target=A/name
    target.parent.mkdir(parents=True,exist_ok=True)
    parent.write_bytes(target, raw.encode() if isinstance(raw,str) else raw)

source = (P/'js8_support.py').read_text(encoding='utf8')
tree = ast.parse(source)
functions = {n.name: ast.get_source_segment(source,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
header = '''"""Explicit JS8 test-order amendment; frozen author and review evidence preserved."""
from pathlib import Path
import copy, hashlib, importlib.util, json, os, shutil, stat, sys
R=Path(__file__).resolve().parent
PARENT=R.parent
sys.path.insert(0,str(PARENT))
import js8_support as parent
sys.path.remove(str(PARENT))
s=parent.s; F=parent.F; PY=parent.PY; RUN=parent.RUN
Q=F/'.agents/js8-amendment-order1-20261017'
STRICT=parent.STRICT
SCRIPT_NAMES=('amendment_support.py','run_full.py','launch_full.py','publish_source.py','complete_source.py',
              'bounded_custody.py','gc_observer.py','tool_environment.py','fixture_runtime.py','resource_observer.py')
inputs=parent.inputs
review=parent.review
require_current_claim=parent.require_current_claim

def manifest_record():
    original,old_pin=parent.manifest_record()
    a=current_json(R/'AMENDMENT.json')
    assert a['original_manifest']==parent.exact_ref(parent.Q/'TRANSFER-MANIFEST.json')
    assert a['staging']==exact_ref(R/'STAGED.json')
    staged=current_json(R/'STAGED.json')
    expected=copy.deepcopy(original)
    name=staged['changed_path']
    assert name=='tests/contract/test_cpu_execution_timing_diagnostics.py'
    assert expected['expected_payload_hashes'][name]==staged['before_sha256']
    expected['expected_payload_hashes'][name]=staged['after_sha256']
    expected['Stop_payload_hashes'][name]=staged['after_sha256']
    expected['scripts']=a['reviewed_scripts']
    expected['native_gate']['script']=a['native_gate_script']
    expected['amendment_lineage']=a['staging']
    manifest_path=Q/'TRANSFER-MANIFEST.json'
    assert a['manifest']==exact_ref(manifest_path)
    value=pinned_json(manifest_path,a['manifest']['sha256'])
    assert canonical(value)==canonical(expected),'AMENDMENT_NOT_EXACT_ONE_TEST_DELTA'
    assert scripts()==a['reviewed_scripts']
    assert exact_ref(R/'native-gate/native_case_gate.py')==a['native_gate_script']
    return value,a['manifest']['sha256']

def require_release(path,pin,phase):
    assert phase in ('candidate-full','publish','destination-full','complete')
    path=s.fs.safe_components(Path(path)); assert path.parent==R/'releases'
    release=pinned_json(path,pin);m,msha=manifest_record()
    assert type(release['schema_version']) is int and release['schema_version']==1
    assert release['executor']=='/root' and release['run_id']==RUN and release['phase']==phase
    assert release['amendment']==exact_ref(R/'AMENDMENT.json')
    assert release['manifest_sha256']==msha and release['reviewed_scripts']==m['scripts']==scripts()
    assert release['Source_publication'] is (phase=='publish') and release['automatic_retry'] is False
    assert release['all_conflicting_Source_pinned_runs_released'] is True
    # Reauthenticate every original author/component/reviewer receipt. This
    # reads the expired historical engineering release; it does not execute it.
    parent.require_release(PARENT/'releases/candidate-full.json',
        s.sha(PARENT/'releases/candidate-full.json'),'candidate-full')
    _,reviewed=proof(release['amendment_review'])
    assert reviewed['author']=='/root' and reviewed['reviewer']=='/root/integration_amendment_review'
    assert reviewed['decision']=='approved' and type(reviewed['exit_status']) is int and reviewed['exit_status']==0
    assert reviewed['amendment']==release['amendment'] and reviewed['manifest_sha256']==msha
    assert reviewed['reviewed_scripts']==scripts() and reviewed['native_gate_script']==m['native_gate']['script']
    assert release['expected_ids_sha256']==m['case_set']['sha256']
    assert release['Source_before_map_sha256']==m['Source_before_map_sha256']
    if phase in ('candidate-full','destination-full'):
        native_path,_=proof(release['native_case_release']);assert native_path.parent==R/'releases'
    return release
'''
names=('canonical','distinct_reviewer','retain','close','read_bytes','write_bytes','pinned_bytes','pinned_json',
       'current_json','proof_bytes','proof','exact_ref','manifest','scripts','child_environment','inventory','verify',
       'require_case_ids','ids','require_validation','interpreter_observation','require_interpreter_command',
       'require_full','native_case_subject','capture_native_case_gate')
sections=[header]
for name in names:
    text=functions[name]
    if name=='verify':
        text=text.replace("for name,row in v['auxiliary_copies11'].items():assert s.ordinary(Q/name)==row",
            "for name,row in current_json(R/'STAGED.json')['auxiliary_copies11'].items():assert s.ordinary(Q/name)==row")
    if name=='require_validation':
        text=text.replace("R/'validate.json'", "PARENT/'validate.json'").replace("R/RUN/", "PARENT/RUN/")
    sections.append(text)
write('amendment_support.py','\n\n'.join(sections)+'\n')
for name in ('bounded_custody.py','gc_observer.py','tool_environment.py','resource_observer.py'):
    write(name,parent.pinned_bytes(P/name,original['scripts'][name]))
for name in ('publish_source.py','complete_source.py','launch_full.py','run_full.py'):
    raw=parent.pinned_bytes(P/name,original['scripts'][name]).decode('utf8')
    raw=raw.replace('import js8_support as j','import amendment_support as j').replace('from js8_support import','from amendment_support import')
    if name=='launch_full.py':
        raw=raw.replace("'timeout_seconds':900", "'timeout_seconds':3600").replace('timeout=900','timeout=3600')
    if name=='run_full.py':
        raw=raw.replace('    class Result(unittest.TextTestResult):', '''    event_stream=(output/'CASE-EVENTS.jsonl').open('x',encoding='utf-8',buffering=1)
    def case_event(kind,test,**details):
        row=dict(event=kind,test_id=test.id(),at=s.utc(),elapsed_seconds=time.perf_counter()-tick,**details)
        raw=json.dumps(row,allow_nan=False)+'\\n'
        assert event_stream.write(raw)==len(raw),'CASE_EVENT_SHORT_WRITE'
        event_stream.flush()
    class Result(unittest.TextTestResult):''')
        raw=raw.replace('            gate.enter(test.id());native.active_case=test.id()',
            "            case_event('PREPARE',test)\n            gate.enter(test.id());native.active_case=test.id()")
        raw=raw.replace('observer.before_test(test.id());executed.append(test.id());super().startTest(test)',
            "observer.before_test(test.id());executed.append(test.id());super().startTest(test)\n            case_event('START',test)")
        raw=raw.replace('            try:gate.finish_case(test.id())', '''            try:
                gate.finish_case(test.id())
                if test.id()==m['native_gate']['original_case_id']:
                    # The bounded native permission ends at its original case.
                    # Guards stay installed for subsequent ordinary cases.
                    proof=gate.finish()
                    gate.close(preserve_guards=True)
                    proof['release_reader_closed']=gate.reader.closed
                    gate.completed_case_proof=proof
                    save(output/'NATIVE-CASE-EARLY-PROOF.json',proof)''')
        raw=raw.replace('native.active_case=None;stopped.append(test.id());super().stopTest(test)',
            "native.active_case=None;stopped.append(test.id());super().stopTest(test)\n                case_event('STOP',test)")
        raw=raw.replace('    stream=None\n', '''        def addFailure(self,test,error):
            super().addFailure(test,error)
            case_event('FAILURE',test,traceback=self.failures[-1][1])
        def addError(self,test,error):
            super().addError(test,error)
            case_event('ERROR',test,traceback=self.errors[-1][1])
        def addSubTest(self,test,subtest,error):
            super().addSubTest(test,subtest,error)
            if error is not None:
                case_event('SUBTEST_FAILURE',subtest,traceback=self._exc_info_to_string(error,test))
    stream=None
''',1)
        raw=raw.replace('        try:observer.uninstall()', '''        try:j.close(event_stream,primary,'case-events-close')
        except BaseException as error:
            if primary is None:primary=error
            else:j.retain(primary,error,'case-events-close')
        try:observer.uninstall()''',1)
        raw=raw.replace("'raw':j.exact_ref(output/'RAW.txt')", "'case_events':j.exact_ref(output/'CASE-EVENTS.jsonl'),'raw':j.exact_ref(output/'RAW.txt')")
        raw=raw.replace('        try:native_proof=gate.finish()', '''        try:
            native_proof=getattr(gate,'completed_case_proof',None)
            if native_proof is None:native_proof=gate.finish()''')
    write(name,raw)
fixture=parent.pinned_bytes(P/'fixture_runtime.py',original['scripts']['fixture_runtime.py']).decode('utf8')
fixture=fixture.replace('import foundation_support as s','from amendment_support import s, Q as AMENDED_Q')
fixture=fixture.replace('assert S in (s.F, s.Q)', 'assert S in (s.F, AMENDED_Q)')
write('fixture_runtime.py',fixture)
gate=parent.pinned_bytes(P/'native-gate/native_case_gate.py',original['native_gate']['script']['sha256']).decode('utf8')
gate=gate.replace("R = F / '.agents/runtime/js8-20261015/native-gate'", "R = F / '.agents/runtime/js8-20261015/amendment-order1/native-gate'")
gate=gate.replace("source in (F, F / '.agents/js8-20261015')", "source in (F, F / '.agents/js8-amendment-order1-20261017')")
gate=gate.replace("is_relative_to(F / '.agents/runtime/js8-20261015')", "is_relative_to(F / '.agents/runtime/js8-20261015/amendment-order1')")
gate=gate.replace("require(self._started and self._active is None and not self._finished, 'CASE_ENTRY_STATE')", "require(self._started and self._active is None, 'CASE_ENTRY_STATE')")
gate=gate.replace("require(not self._entered, 'ORIGINAL_CASE_ALREADY_ENTERED')", "require(not self._entered and not self._finished, 'ORIGINAL_CASE_ALREADY_ENTERED')")
gate=gate.replace('self._active == CASE and self._entered and not self._attempted and self._fixture is not None',
    'self._active == CASE and self._entered and not self._finished and not self._attempted and self._fixture is not None')
gate=gate.replace('def close(self, primary=None):\n        restoration = None', 'def close(self, primary=None, *, preserve_guards=False):\n        restoration = None')
gate=gate.replace("            if hasattr(self, '_restore'):", "            if not preserve_guards and hasattr(self, '_restore'):")
gate=gate.replace('            self.reader.close(primary if primary is not None else restoration)', '''            if not self.reader.close_attempted:
                self.reader.close(primary if primary is not None else restoration)
            elif not self.reader.closed:
                pending = NativeCaseError('RELEASE_READER_CLOSE_UNCERTAIN')
                if primary is not None:
                    attach(primary, pending, self.reader)
                elif restoration is not None:
                    attach(restoration, pending, self.reader)
                else:
                    raise pending''')
write('native-gate/native_case_gate.py',gate)
helpers=('amendment_support.py','run_full.py','launch_full.py','publish_source.py','complete_source.py',
         'bounded_custody.py','gc_observer.py','tool_environment.py','fixture_runtime.py','resource_observer.py')
for name in (*helpers,'native-gate/native_case_gate.py'):
    compile((A/name).read_text(encoding='utf8'),str(A/name),'exec')
new=copy.deepcopy(original)
new['expected_payload_hashes'][staged['changed_path']]=staged['after_sha256']
new['Stop_payload_hashes'][staged['changed_path']]=staged['after_sha256']
new['scripts']={n:s.sha(A/n) for n in helpers}
new['native_gate']['script']=parent.exact_ref(A/'native-gate/native_case_gate.py')
new['amendment_lineage']=parent.exact_ref(A/'STAGED.json')
parent.write_bytes(Q/'TRANSFER-MANIFEST.json',(json.dumps(new,indent=2)+'\n').encode())
write('AMENDMENT.json',json.dumps(dict(schema_version=1,author='/root',at=s.utc(),
    original_manifest=staged['original_manifest'],staging=parent.exact_ref(A/'STAGED.json'),
    manifest=parent.exact_ref(Q/'TRANSFER-MANIFEST.json'),reviewed_scripts=new['scripts'],
    native_gate_script=new['native_gate']['script'],failed_launch=staged['failed_launch'],
    exact_original_case_ids=True,case_count=2334,product_clock_and_assertion_bounds_unchanged=True,
    whole_suite_timeout_seconds=3600,native_release_maximum_seconds=1800,
    native_finalization='After the original case; retained guards deny all later restricted/profile calls.',
    full_source_environment_reverification=True,Source_published=False),indent=2)+'\n')
print(json.dumps(dict(amendment=parent.exact_ref(A/'AMENDMENT.json'),manifest=parent.exact_ref(Q/'TRANSFER-MANIFEST.json'))))
