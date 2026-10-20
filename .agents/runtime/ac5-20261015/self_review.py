"""Bounded author source/caller/AST/custody review; not independent acceptance."""
from ac_support import *
import ast,difflib
inputs=json.loads((R/'SOURCE-INPUTS.json').read_text());scope=inputs['eligible_author_paths']
parent=F/'.agents/ac4-20261015';proof=json.loads((R/'focused-r1/RESULT.json').read_text())
assert proof['tests_run']==26 and proof['exit_status']==0 and not proof['failures'] and not proof['errors'] and not proof['skipped']
assert proof['expected_ids']==proof['executed_ids']==proof['stopped_ids'] and len(set(proof['executed_ids']))==26
assert proof['candidate_before']==proof['candidate_after'] and not proof['new_threads'] and not proof['forbidden_calls']
assert not any(proof['pending_native_resources']) and len(proof['native_observations'])==4
for row in proof['native_observations']:
    assert not row['pending_resources'] and not row['profile_operations'] and not row['worker_launches']
    if 'retired_through_exposed_cleanup' in row:assert row['retired_through_exposed_cleanup'] and row['exact_primary'] and row['nested_exact_primary']
source='src/ceta/supervisor/isolated_worker.py';tests='tests/contract/test_isolation_token_diagnostics.py'
old_tree=ast.parse((parent/source).read_text());new_tree=ast.parse((Q/source).read_text())
select=lambda tree:[n for n in tree.body if not isinstance(n,ast.FunctionDef) or n.name!='_attach_cleanup']
assert ast.dump(ast.Module(body=select(old_tree),type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=select(new_tree),type_ignores=[]),include_attributes=False)
old_attach=next(n for n in old_tree.body if isinstance(n,ast.FunctionDef) and n.name=='_attach_cleanup')
new_attach=next(n for n in new_tree.body if isinstance(n,ast.FunctionDef) and n.name=='_attach_cleanup')
assert ast.dump(old_attach.args,include_attributes=False)==ast.dump(new_attach.args,include_attributes=False)
old_test=ast.parse((parent/tests).read_text());new_test=ast.parse((Q/tests).read_text())
without_added=[n for n in new_test.body if not isinstance(n,ast.ClassDef) or n.name!='NativeRejectedTokenCustodyTests']
assert ast.dump(ast.Module(body=without_added,type_ignores=[]),include_attributes=False)==ast.dump(old_test,include_attributes=False)
old_methods=[n for n in ast.walk(old_test) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
assert len(old_methods)==15
assert fs.read_bytes(Q/'tests/contract/test_isolated_worker.py')==fs.read_bytes(parent/'tests/contract/test_isolated_worker.py')
assert fs.read_bytes(Q/'native/windows_broker/isolated_worker.rs')==fs.read_bytes(parent/'native/windows_broker/isolated_worker.rs')
baseline=json.loads((R/'baseline-r1.json').read_text());closed=json.loads((R/'literal-closure-r2.json').read_text())
assert baseline['tests_run']==2 and len(baseline['failures'])==2 and not baseline['errors']
assert closed['tests_run']==2 and not closed['failures'] and not closed['errors'] and closed['exit_status']==0
assert baseline['literal_class_AST_sha256']==closed['literal_class_AST_sha256']
for name,row in proof['candidate_after'].items():assert ordinary(Q/name)==row
metric=ast.parse((F/'.agents/runtime/na1-20261014/self_review.py').read_text());space={'ast':ast}
node=next(n for n in metric.body if isinstance(n,ast.FunctionDef) and n.name=='python_lines')
exec(compile(ast.Module(body=[node],type_ignores=[]),'<retained-LOC-reader>','exec'),space)
rows={};patches={}
for name in scope:
    original=(parent/name).read_text();current=(Q/name).read_text();old=original.splitlines();new=current.splitlines()
    added=set();removed=set()
    for tag,a,b,c,d in difflib.SequenceMatcher(a=old,b=new,autojunk=False).get_opcodes():
        if tag in ('replace','insert'):added.update(range(c+1,d+1))
        if tag in ('replace','delete'):removed.update(range(a+1,b+1))
    meaningful=space['python_lines'](current)[1] if name.endswith('.py') else set()
    old_meaningful=space['python_lines'](original)[1] if name.endswith('.py') else set()
    rows[name]={'parent':ordinary(parent/name),'candidate':ordinary(Q/name),'physical_added':len(added),
        'physical_removed':len(removed),'meaningful_added':len(added&meaningful),'meaningful_removed':len(removed&old_meaningful)}
    target=R/(name.replace('/','__')+'.diff')
    with target.open('x',encoding='utf-8',newline='\n') as output:
        output.writelines(difflib.unified_diff(original.splitlines(True),current.splitlines(True),fromfile='frozen-AC4/'+name,tofile='AC5/'+name))
    patches[name]=reference(target)
measures={'at':utc(),'by_path':rows,'comparison':'Exact immutable AC4 parent; all inherited code/tests/native worker/runtime/doc/oracle lines receive zero new executable credit.',
    'new_source_LOC':sum(r['meaningful_added'] for n,r in rows.items() if n.startswith('src/')),
    'source_removed':sum(r['meaningful_removed'] for n,r in rows.items() if n.startswith('src/')),
    'new_test_LOC':sum(r['meaningful_added'] for n,r in rows.items() if n.startswith('tests/')),
    'test_removed':sum(r['meaningful_removed'] for n,r in rows.items() if n.startswith('tests/')),
    'inherited_runtime_generated_oracle_document_LOC_credit':0}
write_new(R/'implementation-measures.json',measures)
write_new(R/'SELF-REVIEW.json',{'at':utc(),'author':ACTOR,'independent_review':False,
    'qualification':reference(R/'focused-r1/RESULT.json'),'literal_closure':reference(R/'literal-closure-r2.json'),
    'diffs':patches,'measures':reference(R/'implementation-measures.json'),
    'existing15test_method_ASTs_exact':True,'all_module_AST_outside_attach_cleanup_exact':True,
    'old_tests_and_native_worker_bytes_exact':True,'public_signatures_and_native_call_order_exact':True,
    'checks':['Exact cleanup and owned process use canonical BaseException storage; refusing setters/getters cannot hide custody.',
        'Best-effort notes consult no overridable method/property/list-subclass hook; prior valid notes and malformed containers remain retained.',
        'Original two native hostile class/method ASTs unchanged; new native recovery uses exposed cleanup, including a repeated failure with the same owner.',
        'Actual native handle validity before exposure and invalid/error6after recovery is observed; all owned token/SID allocations retired.',
        'No predicate, diagnostic measurement, token-buffer, launch, Rust, profile, Source or production authority change outside the precise custody repair.'],
    'Source_application':False,'profile_operations':[],'worker_launches':[],
    'remaining':['Root distinct review is required; current author evidence is not independent acceptance.',
        'Missing historical AC3 token values remain unknown; positive isolation and activation are not qualified.']})
print(json.dumps({'tests':26,'literal_closure':2,'source_added':measures['new_source_LOC'],
    'source_removed':measures['source_removed'],'test_added':measures['new_test_LOC'],'original15_ASTs_exact':True}))
