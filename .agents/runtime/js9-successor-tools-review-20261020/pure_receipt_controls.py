"""Synthetic-value controls of exact reviewed gate expressions/functions."""
import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

F=Path(r'T:\00-Active\Project-AI-CETA');R=F/'.agents/runtime/js9-runtime-20261020/successor-r1'
D=F/'.agents/runtime/js9-successor-tools-review-20261020'
packet=json.loads((R/'PACKET.json').read_text());cases=json.loads((R/'CASESET.json').read_text())
def extract(path,names,namespace):
    nodes=[n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path)+'#PURE','exec'),namespace)
results=[]
def run(name,operation,expected):
    error=None
    try:operation();accepted=True
    except BaseException as caught:accepted=False;error=dict(type=type(caught).__name__,text=str(caught))
    assert accepted is expected,(name,accepted,error)
    results.append(dict(name=name,accepted=accepted,expected=expected,passed=True,error=error))

# This is the actual read-side acceptance predicate with synthetic receipts.
ids=cases['expected_ids'];reference={'repository_relative_path':'fixture/result','sha256':'a'*64}
full=dict(phase='candidate-full',manifest_sha256='m',expected_ids=ids,executed_ids=ids,stopped_ids=ids,
 tests_run=len(ids),failures=0,errors=0,skips=0,suite_aborted=False,primary_error=None,remaining_threads=[],
 captured_journal_fixtures_closed=True,gc_observation_failed=False,source_unchanged=True,
 before_hashes={'a':'b'},after_hashes={'a':'b'},physical_custody='physical',native_owners_proof='native',
 native_case_proof='gate',exit_status=0,interpreter={'exact':'interpreter'},argv=['base','-B','child'])
launch=dict(phase='candidate-full',primary_error=None,exit_status=0,interpreter={'exact':'interpreter'},
 child_argv=['venv','-B','child'],record=dict(child_exit=0,child_result=reference,retirement_error=None,
 primary_error=None,native_owner_after=dict(process=True,job=True,thread=True)))
physical={'owned_resources_closed':True};native={'owned_resources_closed':True};gate={'passed':True,'release_reader_closed':True}
records={'result':full,'launch':launch,'physical':physical,'native':native,'gate':gate}
def proof(ref):
    key='result' if ref==reference else ref
    return R/'candidate-full/RESULT.json',records[key]
ns={'R':R,'proof':proof,'packet':lambda:packet,'manifest_reference':lambda:{'sha256':'m'},
 'manifest':lambda:{'expected_payload_hashes':{'a':'b'}},'inputs':lambda:{'python':{'path':'venv'},'base_python':{'path':'base'}},
 'interpreter_observation':lambda value:{'exact':'interpreter'}}
# require_case_ids uses proof(packet.case_set); preserve that exact body too.
def all_proof(ref):
    if ref==packet['case_set']:return None,cases
    return proof(ref)
ns['proof']=all_proof
extract(R/'js9_support.py',{'require_case_ids','require_full_result'},ns)
run('exact_terminal_full_and_owner_receipts_accepted',lambda:ns['require_full_result'](reference,'launch','candidate-full'),True)
for name,path,value in [
 ('count_without_completed_ids',('executed_ids',),ids[:-1]),
 ('missing_STOP',('stopped_ids',),ids[:-1]),
 ('skip_not_accepted',('skips',),1),
 ('runner_error_not_accepted',('suite_aborted',),True),
 ('pending_thread_not_accepted',('remaining_threads',),['live']),
 ('nonterminal_full_exit_not_accepted',('exit_status',),None),
 ('payload_drift_not_accepted',('after_hashes',),{'a':'different'})]:
    before=records['result'];records['result']=copy.deepcopy(before);records['result'][path[0]]=value
    run(name,lambda:ns['require_full_result'](reference,'launch','candidate-full'),False);records['result']=before
for name,key,field,value in [('live_physical_custody','physical','owned_resources_closed',False),
 ('live_native_custody','native','owned_resources_closed',False),('failed_native_case','gate','passed',False),
 ('open_gate_reader','gate','release_reader_closed',False)]:
    old=records[key][field];records[key][field]=value
    run(name,lambda:ns['require_full_result'](reference,'launch','candidate-full'),False);records[key][field]=old
for name,field,value in [('failed_actual_child_exit','child_exit',1),('uncertain_outer_retirement','retirement_error',{'error':'pending'}),
 ('open_outer_job','native_owner_after',{'job':False})]:
    old=records['launch']['record'][field];records['launch']['record'][field]=value
    run(name,lambda:ns['require_full_result'](reference,'launch','candidate-full'),False);records['launch']['record'][field]=old

# Evaluate the actual narrow pending-control exception without native objects.
tree=ast.parse((R/'fixture_runtime.py').read_text())
expressions=[]
for node in ast.walk(tree):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='dict':
        expressions.extend(kw.value for kw in node.keywords if kw.arg=='bindings_closed')
assert len(expressions)==1
compiled=compile(ast.Expression(expressions[0]),str(R/'fixture_runtime.py')+'#bindings_closed','eval')
special='test_native_runtime_composition.NativeRuntimeCompositionTests.test_interrupted_native_open_preserves_unknown_output_without_false_closure'
controlled=dict(controlled_API=True,kind='store',test_id=special,closed=False,
                pending=[dict(kind='file_open',retry='UNCERTAIN',handle=None)])
def binding_check(row):assert eval(compiled,{'bindings':[row]}) is True
run('exact_pure_unknown_output_retained_and_accounted',lambda:binding_check(controlled),True)
for name,key,value in [('real_native_pending_refused','controlled_API',False),
 ('other_case_pending_refused','test_id','other'),('known_handle_pending_refused','pending',[dict(kind='file_open',retry='UNCERTAIN',handle=9)]),
 ('different_pending_kind_refused','pending',[dict(kind='sid',retry='UNCERTAIN',handle=None)])]:
    row=copy.deepcopy(controlled);row[key]=value
    run(name,lambda row=row:binding_check(row),False)

out={'status':'PASS','scope':'DATA_ONLY exact function/expression bodies; no production module/tool import, native API, worker, profile, process, socket or database',
 'controls':results,'count':len(results),'source_hashes':{name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in ('js9_support.py','fixture_runtime.py')}}
with (D/'PURE-RECEIPT-CONTROLS.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps({'status':'PASS','controls':len(results)}))
