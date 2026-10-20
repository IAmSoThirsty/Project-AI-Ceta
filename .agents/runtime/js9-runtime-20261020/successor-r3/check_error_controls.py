"""DATA_ONLY controls of exact R3 error/parser bodies; no test/native execution."""
from pathlib import Path
from datetime import datetime, timezone
from types import SimpleNamespace
import ast, hashlib, json, sys, traceback

F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent;D2=R.parent/'successor-r2'
cases=json.loads((R/'CASESET.json').read_bytes());rows=[];denied=[]
def audit(event,args):
    if event.startswith(('subprocess.','socket.','ctypes.','winreg.')) or event in ('sqlite3.connect','os.system','os.startfile'):
        denied.append(event);raise RuntimeError('PURE_CONTROL_EFFECT_DENIED:'+event)
sys.addaudithook(audit)
def extract(path,names,namespace):
    tree=ast.parse(path.read_text(encoding='utf8'))
    selected=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    assert {node.name for node in selected}==set(names)
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(path),'exec'),namespace)
def check(name,call):
    call();rows.append(dict(name=name,passed=True))
def require(condition):assert condition
def throws(kind,call):
    try:call()
    except kind:return
    raise AssertionError('Expected '+kind.__name__)
core=dict(proof=lambda ref:(None,cases),packet=lambda:dict(case_set={}))
extract(R/'js9_support.py',['require_case_ids','retain'],core)
errors=dict(traceback=traceback);extract(R/'run_full.py',['error_record'],errors)
error_record=errors['error_record']
parser=dict(j=SimpleNamespace(require_case_ids=core['require_case_ids']))
extract(R/'launch_full.py',['child_terminal_status'],parser)
child_status=parser['child_terminal_status']

def raised(kind,message):
    try:raise kind(message)
    except BaseException as error:return error
class BrokenText(Exception):
    def __str__(self):raise RuntimeError('broken diagnostic text')
primary=raised(AssertionError,'DISCOVERED_CASESET_MISMATCH')
check('primary_message_and_original_trace',lambda:require(
    error_record(primary)['message']=='DISCOVERED_CASESET_MISMATCH' and
    'raise kind(message)' in error_record(primary)['traceback']))
check('none_primary',lambda:require(error_record(None) is None))
broken=raised(BrokenText,'hidden')
check('broken_primary_str_guarded',lambda:require(error_record(broken)['message']=='<exception text unavailable>'))
secondary=raised(BrokenText,'cleanup')
core['retain'](primary,secondary,'native-case-finish')
check('broken_secondary_str_keeps_primary',lambda:require(
    error_record(primary)['type']=='AssertionError' and
    error_record(primary)['message']=='DISCOVERED_CASESET_MISMATCH' and
    error_record(primary)['secondary_errors'][0]['error']['message']=='<exception text unavailable>'))
malformed=raised(ValueError,'original')
malformed.publication_evidence_failures=(None,('short',),(object(),RuntimeError('x'),None),('bad-error',object(),None))
check('malformed_retained_entries_recorded',lambda:require(
    len(error_record(malformed)['secondary_errors'])==4 and
    all(row['malformed_retained_entry'] for row in error_record(malformed)['secondary_errors'])))
wrong_container=raised(RuntimeError,'container')
wrong_container.publication_evidence_failures=[]
check('malformed_retained_container_recorded',lambda:require(
    error_record(wrong_container)['secondary_errors_diagnostic']['malformed_retained_entries'] is True))
saved_traceback=errors['traceback'];errors['traceback']=SimpleNamespace(format_exception=lambda *args:(_ for _ in ()).throw(RuntimeError('trace formatter')))
check('primary_and_secondary_trace_formatter_failure_guarded',lambda:require(
    error_record(primary)['traceback']=='<exception traceback unavailable>' and
    error_record(primary)['secondary_errors'][0]['error']['traceback']=='<exception traceback unavailable>'))
errors['traceback']=saved_traceback
legacy=json.loads((D2/'candidate-full/RESULT.json').read_bytes())
check('actual_old_failed_schema_preserved_without_KeyError',lambda:require(
    child_status(legacy)['exit_status']==1 and
    child_status(legacy)['primary_error']==legacy['primary_error'] and
    child_status(legacy)['expected_inventory_present'] is False))
failed=dict(legacy,expected_ids=cases['expected_ids'],primary_error=error_record(primary),failure_stage='suite-order-and-exact-case-set')
check('new_failed_schema_preserves_trace_and_case_inventory',lambda:require(
    child_status(failed)['primary_error']['message']=='DISCOVERED_CASESET_MISMATCH' and
    child_status(failed)['expected_inventory_present'] is True))
check('successful_child_exact_case_set_required',lambda:require(
    child_status(dict(exit_status=0,expected_ids=cases['expected_ids']))['exit_status']==0))
check('successful_child_missing_ids_refused',lambda:throws(AssertionError,lambda:child_status(dict(exit_status=0))))
check('failed_child_wrong_supplied_ids_refused',lambda:throws(AssertionError,lambda:child_status(dict(exit_status=1,expected_ids=cases['expected_ids'][:-1]))))
for label,value in [('boolean',True),('string','1'),('absent',None)]:
    check('invalid_status_'+label,lambda value=value:throws(RuntimeError,lambda:child_status(dict(exit_status=value))))

root=R/'pure-controls';root.mkdir(exist_ok=False)
for label,cleanup_broken,malformed_cleanup in [('preflight',False,False),('broken-secondary',True,False),('malformed-secondary',False,True)]:
    base=root/label;base.mkdir()
    initiating=raised(AssertionError,'EXACT_PREFLIGHT_PRIMARY_'+label);writes={}
    reader=SimpleNamespace(closed=False)
    class Gate:
        completed_case_proof=None
        def start(self):pass
        def finish(self):
            if cleanup_broken:raise secondary
            return dict(passed=False)
        def close(self,error):reader.closed=True
    gate=Gate();gate.reader=reader
    args=SimpleNamespace(phase='candidate-full',release_path=base/'unused-release.json',release_sha256='0'*64)
    class Parser:
        def add_argument(self,*args,**kwargs):pass
        def parse_args(self):return args
    def execute(args,release,v,gate,progress):
        progress.update(stage='suite-order-and-exact-case-set',preflight_complete=False,
            loader_errors=['actual loader failure retained'],discovered_ids=['unittest.loader._FailedTest.module'])
        if malformed_cleanup:initiating.publication_evidence_failures=(None,('bad',))
        raise initiating
    def ref(path):return dict(repository_relative_path=Path(path).relative_to(F).as_posix(),sha256='1'*64)
    def write(path,raw):
        assert path not in writes;writes[path]=json.loads(raw)
    fake=SimpleNamespace(require_release=lambda *args:{},verify=lambda **kwargs:{},
        capture_native_case_gate=lambda *args:gate,write_bytes=write,exact_ref=ref,
        manifest=lambda:dict(native_gate=dict(original_case_id='original_native_case')),
        manifest_reference=lambda:dict(sha256='2'*64),proof=lambda ref:(None,cases),
        packet=lambda:dict(case_set={}),retain=core['retain'])
    namespace=dict(argparse=SimpleNamespace(ArgumentParser=Parser),Path=Path,j=fake,
        s=SimpleNamespace(utc=lambda:datetime.now(timezone.utc).isoformat()),R=base,
        json=json,sys=sys,traceback=traceback,execute=execute)
    extract(R/'run_full.py',['error_record','main'],namespace)
    try:namespace['main']()
    except BaseException as observed:assert observed is initiating
    else:raise AssertionError('exact original primary was not propagated')
    report=writes[base/'candidate-full/RESULT.json']
    assert report['primary_error']['message']=='EXACT_PREFLIGHT_PRIMARY_'+label
    assert 'raise initiating' in report['primary_error']['traceback']
    assert report['tests_run']==0 and report['executed_ids']==report['stopped_ids']==[]
    assert report['expected_ids']==cases['expected_ids'] and report['loader_errors']==['actual loader failure retained']
    assert report['failure_stage']=='suite-order-and-exact-case-set' and report['preflight_complete'] is False
    assert report['mandatory_full_gate_complete'] is False and report['exit_status']==1 and reader.closed
    if cleanup_broken:assert report['primary_error']['secondary_errors'][0]['error']['message']=='<exception text unavailable>'
    if malformed_cleanup:assert all(item['malformed_retained_entry'] for item in report['primary_error']['secondary_errors'])
    assert child_status(report)['primary_error']==report['primary_error']
    rows.append(dict(name='actual_main_AST_'+label,passed=True,mode='CONTROLLED_PORTS_NO_NATIVE_OR_TEST_BODIES'))

assert denied==[]
packet=json.loads((R/'PACKET.json').read_bytes());manifest=json.loads((R/'MANIFEST-Q5.json').read_bytes())
assert len(manifest['payload_hashes'])==541
assert all(hashlib.sha256((Path(manifest['candidate'])/name).read_bytes()).hexdigest()==pin for name,pin in manifest['payload_hashes'].items())
assert all(hashlib.sha256((R/name).read_bytes()).hexdigest()==pin for name,pin in packet['scripts'].items())
result=dict(at=datetime.now(timezone.utc).isoformat(),mode='FILE_AST_DATA_ONLY',
    packet_sha256=hashlib.sha256((R/'PACKET.json').read_bytes()).hexdigest(),
    candidate_manifest_sha256=hashlib.sha256((R/'MANIFEST-Q5.json').read_bytes()).hexdigest(),
    controls=rows,count=len(rows),passed=True,denied_events=denied,
    actual_test_bodies=0,native_calls=0,full_execution=False,fixture_execution=False,
    actual_candidate541_payloads_unchanged=True,exit_status=0)
output=R/'ERROR-PARSER-CONTROLS.json'
with output.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(count=len(rows),passed=True,output=str(output),sha256=hashlib.sha256(output.read_bytes()).hexdigest())),flush=True)
