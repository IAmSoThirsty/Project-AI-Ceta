"""Independent file/AST inventory checks only; never import the reviewed tools."""
import ast
import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

F=Path(r'T:\00-Active\Project-AI-CETA')
R=F/'.agents/runtime/js9-runtime-20261020/successor-r1'
Q=F/'.agents/js9-runtime-20261020'
D=F/'.agents/runtime/js9-successor-tools-review-20261020'
inputs={};checks=[]
def sha(p):
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    assert str(p) not in inputs or inputs[str(p)]==digest,('INPUT_DRIFT',str(p))
    inputs[str(p)]=digest
    return digest
def load(p):sha(p);return json.loads(p.read_text(encoding='utf-8-sig'))
def check(name,passed,details=None):
    assert passed,name
    checks.append(dict(name=name,passed=True,details=details))

packet=load(R/'PACKET.json')
check('PACKET_PIN',sha(R/'PACKET.json')=='455efb4d1d30ecd05f7076f32648a44b71f7fc383882945e233f1e2c126810c5')
for key in ('candidate_manifest','case_set','Source_before','environment','git_dependency','adapter_deltas'):
    ref=packet[key];check('REF:'+key,sha(F/ref['repository_relative_path'])==ref['sha256'])
for name,pin in packet['scripts'].items():check('SCRIPT:'+name,sha(R/name)==pin)
delta=load(R/'ADAPTER-DELTAS-R2.json')
for name,row in delta['origins'].items():
    ancestor=Path(row['path']);check('ANCESTOR:'+name,sha(ancestor)==row['sha256'])
    check('SUCCESSOR:'+name,sha(R/name)==row['current_sha256'])
    old=ancestor.read_text(encoding='utf-8');new=(R/name).read_text(encoding='utf-8')
    check('EXACT_DIFF:'+name,''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True)))==row['delta'])
    if row.get('exact_byte_copy'):check('EXACT_COPY:'+name,old==new)
for name,row in packet['fixture_dependencies'].items():check('FIXTURE:'+name,sha(Path(row['path']))==row['sha256'])
manifest=load(F/packet['candidate_manifest']['repository_relative_path'])
check('CANDIDATE530',len(manifest['payload_hashes'])==530 and all(sha(Q/name)==pin for name,pin in manifest['payload_hashes'].items()))
cases=load(F/packet['case_set']['repository_relative_path'])
parent=load(F/cases['parent_reference']['repository_relative_path'])
check('PARENT2334_PIN',sha(F/cases['parent_reference']['repository_relative_path'])==cases['parent_reference']['sha256'])
ids=cases['expected_ids'];old=cases['parent2334_ids'];oldset=set(old)
check('EXACT2622_IDS',len(ids)==len(set(ids))==2622 and cases['expected_count']==2622)
check('EXACT2334_ORDER',len(old)==2334 and old==parent['expected_ids'] and [x for x in ids if x in oldset]==old)
check('EXACT288_ADDITIONS',set(cases['added_ids'])==set(ids)-oldset and len(cases['added_ids'])==288)
check('REASONING50',sum(x.startswith('reasoning.test_reasoning_integration.') for x in ids)==21 and sum(x.startswith('reasoning.test_reasoning_repairs.') for x in ids)==29)
check('ALL_METHOD_LOCATORS',set(cases['method_locators'])==set(ids))
trees={};old_changed=[]
for case,row in cases['method_locators'].items():
    p=Q/row['path'];check('METHOD_SOURCE:'+case,sha(p)==row['source_sha256'])
    if row['path'] not in trees:trees[row['path']]=ast.parse(p.read_text(encoding='utf-8-sig'))
    nodes=[n for n in ast.walk(trees[row['path']]) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.lineno==row['first_line'] and n.end_lineno==row['last_line']]
    check('METHOD_AST:'+case,len(nodes)==1 and hashlib.sha256(ast.dump(nodes[0],include_attributes=False).encode()).hexdigest()==row['method_ast_sha256'])
    if case in oldset:
        key=row['path']+'::'+'.'.join(case.split('.')[-2:])
        previous=parent['method_ast_sha256'].get(key)
        if previous is not None and previous!=row['method_ast_sha256']:old_changed.append(dict(case=case,old=previous,new=row['method_ast_sha256']))
check('NATIVE18_IDS',len(packet['native_store_ids'])==18 and len(set(packet['native_store_ids']))==18 and set(packet['native_store_ids'])<=set(ids))
check('NATIVE6_IDS',len(packet['native_observer_ids'])==6 and len(set(packet['native_observer_ids']))==6 and set(packet['native_observer_ids'])<=set(ids))
before=load(F/packet['Source_before']['repository_relative_path'])
paths=packet['application_paths'];expected=manifest['payload_hashes']
check('SOURCE_TARGETS530',set(before['targets'])==set(expected) and len(before['targets'])==530)
actual_changed=sorted(name for name,row in before['targets'].items() if row is None or row['sha256']!=expected[name])
check('EXACT_CHANGED_NEW31',paths==before['changed_or_new_paths']==actual_changed and len(paths)==31)
for name,row in before['targets'].items():
    p=F/name
    if row is None:check('SOURCE_ABSENT:'+name,not p.exists())
    else:check('SOURCE_CURRENT_HASH:'+name,sha(p)==row['sha256'])
for key in ('source352','reasoning_R3','selected26'):
    ref=before[key];check('SOURCE_ORIGIN:'+key,sha(F/ref['repository_relative_path'])==ref['sha256'])
accepted=load(F/before['source352']['repository_relative_path'])
check('ACCEPTED_SOURCE352_PRESERVED',accepted['Source_accepted'] is True and accepted['Source_payloads']==len(accepted['source'])==352 and all(before['targets'][name]==row for name,row in accepted['source'].items()))
native_ids=packet['native_store_ids']+packet['native_observer_ids']
check('INDEPENDENT_NATIVE24_DISJOINT',len(set(native_ids))==24)
for name in ('js9_support.py','publish_source.py','CASESET.json','PACKET.json'):
    controls=load(R/'PURE-CONTROLS-R2.json');check('PURE_CONTROL_SOURCE:'+name,sha(R/name)==controls['sources'][name])
check('AUTHOR_PURE_CONTROLS_RECORDED12',controls['all_passed'] is True and controls['tests']==len(controls['cases'])==12 and all(x['passed'] for x in controls['cases']))
check('INPUTS_STABLE',all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==pin for p,pin in inputs.items()))
out=dict(status='PASS',at=datetime.now(timezone.utc).isoformat(),reviewer='/root/recovery_join_review20',
    mode='FILE_AND_AST_ONLY',candidate_imports=False,native_operations=False,product_tests_run=False,
    checks=checks,check_count=len(checks),inputs_sha256=inputs,stable_inputs=len(inputs),
    parent_method_AST_changes=old_changed,
    retained_no_profile_case=packet['original_case_id'],
    native_store_ids=packet['native_store_ids'],native_observer_ids=packet['native_observer_ids'])
with (D/'FROZEN-CUT-RESULT.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in out.items() if k not in ('checks','inputs_sha256','native_store_ids','native_observer_ids')}))
