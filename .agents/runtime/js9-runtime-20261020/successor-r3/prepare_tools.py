"""Exact successor binding and narrow full-run failure diagnostics repair."""
from pathlib import Path
from datetime import datetime, timezone
import ast, difflib, hashlib, json, sys
F=Path('T:/00-Active/Project-AI-CETA');R=Path(__file__).resolve().parent;D2=R.parent/'successor-r2'
Q=F/'.agents/js9-runtime-r5-20261020'
sys.path.insert(0,str(D2));import js9_support as predecessor
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def write(path,raw):
    with path.open('xb') as stream:assert stream.write(raw)==len(raw)
old_packet=json.loads((D2/'PACKET.json').read_bytes())
assert sha(D2/'PACKET.json')=='eb5f4c993a74f7b378db9b2dd10e039fadc64ebff3c31887c78393ce58157055'
manifest=json.loads((R/'MANIFEST-Q5.json').read_bytes());assert len(manifest['payload_hashes'])==541
before={name:predecessor.s.ordinary(F/name) if (F/name).exists() else None for name in manifest['payload_hashes']}
old_before=json.loads((D2/'SOURCE-BEFORE.json').read_bytes())
assert all(before[name]==value for name,value in old_before['targets'].items())
save(R/'SOURCE-BEFORE.json',dict(at=datetime.now(timezone.utc).isoformat(),targets=before,
    predecessor=predecessor.exact_ref(D2/'SOURCE-BEFORE.json'),old530_native_facts_unchanged=True))
write(R/'CASESET.json',(D2/'CASESET.json').read_bytes())
write(R/'ENVIRONMENT.json',(D2/'ENVIRONMENT.json').read_bytes())
scripts={};deltas={}
for name,pin in old_packet['scripts'].items():
    origin=D2/name;assert sha(origin)==pin
    raw=origin.read_text(encoding='utf8')
    text=raw.replace('.agents/runtime/js9-runtime-20261020/successor-r2','.agents/runtime/js9-runtime-20261020/successor-r3')
    text=text.replace("F/'.agents/js9-runtime-20261020'","F/'.agents/js9-runtime-r5-20261020'")
    text=text.replace("F / '.agents/js9-runtime-20261020'","F / '.agents/js9-runtime-r5-20261020'")
    if name=='js9_support.py':
        assert text.count("assert len(m['payload_hashes'])==530")==1
        text=text.replace("assert len(m['payload_hashes'])==530","assert len(m['payload_hashes'])==p['candidate_payload_count']==541")
    if name=='run_full.py':
        marker='\ndef execute(args,release,v,gate):\n'
        assert text.count(marker)==1
        helper='''
def error_record(error):
    if error is None:return None
    try:message=str(error)
    except BaseException:message='<exception text unavailable>'
    try:trace=''.join(traceback.format_exception(type(error),error,error.__traceback__))
    except BaseException:trace='<exception traceback unavailable>'
    value=dict(type=type(error).__name__,message=message,traceback=trace)
    data=BaseException.__dict__['__dict__'].__get__(error)
    secondary=dict.get(data,'publication_evidence_failures',())
    if type(secondary) is tuple:
        value['secondary_errors']=[dict(stage=stage,error_type=type(item).__name__,
            message=str(item),traceback=''.join(traceback.format_exception(type(item),item,tb)))
            for stage,item,tb in secondary]
    return value

def execute(args,release,v,gate,progress=None):
    if progress is None:progress={}
    progress.update(stage='payload-verification',preflight_complete=False,loader_errors=[])
'''
        text=text.replace(marker,'\n'+helper)
        replacements={
            '    load_sqlite();sqlite_identity=runtime_identity()':"    progress['stage']='sqlite-library-import'\n    load_sqlite();sqlite_identity=runtime_identity()",
            '    dependencies=[]':"    progress['stage']='dependency-imports'\n    dependencies=[]",
            '    modules=[]':"    progress['stage']='product-imports'\n    modules=[]",
            '    fixture_wiring=prepare(root,output,gate)':"    progress['stage']='fixture-preparation'\n    fixture_wiring=prepare(root,output,gate)",
            "    loader=unittest.TestLoader();suite=loader.discover(str(root/'tests/contract'),pattern='test_*.py')":"    progress['stage']='suite-discovery'\n    loader=unittest.TestLoader();suite=loader.discover(str(root/'tests/contract'),pattern='test_*.py')\n    progress.update(loader_errors=list(loader.errors),discovered_ids=list(j.ids(suite)))\n    progress['stage']='suite-order-and-exact-case-set'",
            '    controlled_arithmetic=configure_suite(suite)':"    progress['stage']='controlled-arithmetic-binding'\n    controlled_arithmetic=configure_suite(suite)",
            '    observer=Observer(native_handle_count());observer.install()':"    progress['stage']='gc-observer-install'\n    observer=Observer(native_handle_count());observer.install()",
            "    event_stream=(output/'CASE-EVENTS.jsonl').open('x',encoding='utf-8',buffering=1)":"    progress.update(stage='test-execution',preflight_complete=True)\n    event_stream=(output/'CASE-EVENTS.jsonl').open('x',encoding='utf-8',buffering=1)",
            "'primary_error':{'type':type(primary).__name__} if primary is not None else None":"'primary_error':error_record(primary)",
            '    primary=report=native_proof=None':'    primary=report=native_proof=None;progress=dict(stage=\'native-case-admission\',preflight_complete=False,loader_errors=[])',
            '        report=execute(args,release,v,gate)':'        report=execute(args,release,v,gate,progress)',
            "                    primary_error=None if primary is None else {'type':type(primary).__name__},":"                    primary_error=error_record(primary),expected_ids=j.proof(j.packet()['case_set'])[1]['expected_ids'],\n                    executed_ids=[],stopped_ids=[],failures=0,errors=0,skips=0,\n                    manifest_sha256=j.manifest_reference()['sha256'],mandatory_full_gate_complete=False,\n                    preflight_complete=progress['preflight_complete'],failure_stage=progress['stage'],\n                    loader_errors=progress['loader_errors'],discovered_ids=progress.get('discovered_ids',[]),",
            "            report['native_case_proof']=j.exact_ref(output/'NATIVE-CASE-PROOF.json')":"            report['native_case_proof']=j.exact_ref(output/'NATIVE-CASE-PROOF.json')\n            report['primary_error']=error_record(primary)\n            report['preflight_complete']=progress['preflight_complete']",
        }
        for old,new in replacements.items():
            assert text.count(old)==1,(name,old,text.count(old))
            text=text.replace(old,new)
    if name=='launch_full.py':
        marker='\ndef main():\n'
        assert text.count(marker)==1
        helper='''
def child_terminal_status(value):
    if type(value) is not dict or type(value.get('exit_status')) is not int:
        raise RuntimeError('FULL_CHILD_TERMINAL_INVALID_STATUS')
    status=value['exit_status'];expected=value.get('expected_ids')
    inventory_present=type(expected) is list
    if status==0 or inventory_present:j.require_case_ids(expected)
    return dict(exit_status=status,primary_error=value.get('primary_error'),
        suite_aborted=value.get('suite_aborted'),preflight_complete=value.get('preflight_complete'),
        expected_inventory_present=inventory_present,failure_stage=value.get('failure_stage'),
        loader_errors=value.get('loader_errors',[]))

def main():
'''
        text=text.replace(marker,'\n'+helper)
        text=text.replace('    record=primary=None','    record=primary=child_status=child_reference=None')
        old="    def child():\n        path=R/args.phase/'RESULT.json';full=j.current_json(path)\n        j.require_case_ids(full['expected_ids']);assert full['exit_status']==0\n        return j.exact_ref(path)"
        new="    def child():\n        nonlocal child_status,child_reference\n        path=R/args.phase/'RESULT.json';full=j.current_json(path)\n        child_reference=j.exact_ref(path);child_status=child_terminal_status(full)\n        return child_reference"
        assert text.count(old)==1;text=text.replace(old,new)
        old="        assert record['child_exit']==0"
        new="        if record['child_exit']!=0 or child_status is None or child_status['exit_status']!=0:\n            raise RuntimeError('FULL_CHILD_FAILED:'+str(record['child_exit']))"
        assert text.count(old)==1;text=text.replace(old,new)
        old="'exit_status':0 if primary is None else 1,'own_job_only':True"
        new="'child_terminal':child_reference,'child_status':child_status,\n        'child_primary_error':None if child_status is None else child_status['primary_error'],\n        'exit_status':0 if primary is None else 1,'own_job_only':True"
        assert text.count(old)==1;text=text.replace(old,new)
    ast.parse(text)
    write(R/name,text.encode('utf8'))
    scripts[name]=sha(R/name)
    if text!=raw:
        deltas[name]=dict(before_sha256=pin,after_sha256=scripts[name],
            unified_diff=''.join(difflib.unified_diff(raw.splitlines(True),text.splitlines(True),fromfile='R2/'+name,tofile='R3/'+name)))
save(R/'INITIAL-TOOL-DELTAS.json',deltas)
packet=dict(old_packet)
packet.update(at=datetime.now(timezone.utc).isoformat(),candidate_payload_count=541,
    candidate_manifest=dict(repository_relative_path=(R/'MANIFEST-Q5.json').relative_to(F).as_posix(),sha256=sha(R/'MANIFEST-Q5.json')),
    case_set=dict(repository_relative_path=(R/'CASESET.json').relative_to(F).as_posix(),sha256=sha(R/'CASESET.json')),
    Source_before=dict(repository_relative_path=(R/'SOURCE-BEFORE.json').relative_to(F).as_posix(),sha256=sha(R/'SOURCE-BEFORE.json')),
    environment=dict(repository_relative_path=(R/'ENVIRONMENT.json').relative_to(F).as_posix(),sha256=sha(R/'ENVIRONMENT.json')),scripts=scripts,
    predecessor_native_packet=predecessor.exact_ref(D2/'PACKET.json'))
assert len(packet['application_paths'])==31
save(R/'PACKET-DRAFT.json',packet)
print(json.dumps(dict(scripts=len(scripts),changed=list(deltas),payloads=541,publication_paths=31,draft=True)),flush=True)
