"""Exact successor credit, original method/caller conservation and self-review."""
from et_support import *
import ast,collections,difflib,importlib
proof=json.loads((R/'connected-r1.json').read_text())
assert proof['tests_run']==proof['unique_methods']==394 and proof['exit_status']==0
assert proof['expected_ids']==proof['executed_ids']==proof['stopped_ids']
assert not proof['failures'] and not proof['errors'] and not proof['skips']
assert proof['all_fixture_stores_closed'] and not proof['new_threads_remaining']
assert sorted(row['exit_code'] for row in proof['crash_observations'])==[71,72]
assert proof['candidate_before']==proof['candidate_after'] and len(proof['candidate_after'])==316
for name,row in proof['candidate_after'].items():assert ordinary(Q/name)==row
inputs=json.loads((R/'SOURCE-INPUTS.json').read_text());scope=inputs['eligible_paths']
parent=F/'.agents/et1-20261014';old_proof=json.loads((F/'.agents/runtime/et1-20261014/connected-r1.json').read_text())
old_ids=set(old_proof['executed_ids']);new_ids=set(proof['executed_ids'])-old_ids
assert old_ids<=set(proof['executed_ids']) and len(old_ids)==385 and len(new_ids)==9
test_path='tests/contract/test_owned_cpu_outcome_transactions.py'
def methods(path):
    tree=ast.parse(Path(path).read_text());node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='OutcomeTransactionsTests')
    return {n.name:ast.dump(n,include_attributes=False) for n in node.body if isinstance(n,ast.FunctionDef)}
old_methods,new_methods=methods(parent/test_path),methods(Q/test_path)
old_tests={n for n in old_methods if n.startswith('test_')}
intentional='test_restoration_requires_distinct_approval_consumption_attempt_and_proof'
assert len(old_tests)==33
for name in old_tests-{intentional}:assert old_methods[name]==new_methods[name]
assert old_methods[intentional]!=new_methods[intentional]
assert fs.read_bytes(parent/'src/ceta/kernel/transactions.py')==fs.read_bytes(Q/'src/ceta/kernel/transactions.py')
write_new(R/'original-method-conservation.json',{'at':utc(),'original385_ids_retained':True,
    'original32_method_ASTs_exact':True,'intentional_method':intentional,
    'intentional_change':'Restoration operation explicitly uses the same declared32KiB finite success reserve/budget. Assertions, separate approval, proof denial, consumption and actual settlement remain unchanged.',
    'fixture_amendment':'Controlled enrollment65,536bytes/32,768restore and evidence; operation written-byte allowance equals explicit finite reserve. Parent/shared contracts unchanged.',
    'new_method_ids':sorted(new_ids),'parent_385_proof':reference(F/'.agents/runtime/et1-20261014/connected-r1.json'),
    'transactions_delegate_bytes_exact':True,'parent_implementation_review':reference(F/'.agents/runtime/et1-20261014/independent-review/review.json')})
measurement=ast.parse((F/'.agents/runtime/na1-20261014/self_review.py').read_text());space={'ast':ast}
node=next(n for n in measurement.body if isinstance(n,ast.FunctionDef) and n.name=='python_lines')
exec(compile(ast.Module(body=[node],type_ignores=[]),'<retained-LOC-measurement>','exec'),space)
rows={};patches={}
for name in scope:
    original=(parent/name).read_text();current=(Q/name).read_text()
    old,new=original.splitlines(),current.splitlines();added=set();removed=set()
    for tag,a,b,c,d in difflib.SequenceMatcher(a=old,b=new,autojunk=False).get_opcodes():
        if tag in ('insert','replace'):added.update(range(c+1,d+1))
        if tag in ('delete','replace'):removed.update(range(a+1,b+1))
    meaningful=space['python_lines'](current)[1] if name.endswith('.py') else set()
    old_meaningful=space['python_lines'](original)[1] if name.endswith('.py') else set()
    rows[name]={'parent':ordinary(parent/name),'candidate':ordinary(Q/name),
        'physical_added':len(added),'physical_removed':len(removed),
        'meaningful_added':len(added&meaningful),'meaningful_removed':len(removed&old_meaningful)}
    out=R/(name.replace('/','__')+'.diff')
    with out.open('x',encoding='utf-8',newline='\n') as stream:
        stream.writelines(difflib.unified_diff(original.splitlines(True),current.splitlines(True),
            fromfile='frozen-ET1/'+name,tofile='ET2/'+name))
    patches[name]=reference(out)
measures={'at':utc(),'by_path':rows,'comparison':'Exact rejected ET1 before-images. All inherited ET1/KA1/dependencies/runtime/oracle bodies are uncredited.',
    'new_source_LOC':sum(row['meaningful_added'] for name,row in rows.items() if name.startswith('src/')),
    'source_removed':sum(row['meaningful_removed'] for name,row in rows.items() if name.startswith('src/')),
    'new_test_LOC':sum(row['meaningful_added'] for name,row in rows.items() if name.startswith('tests/')),
    'test_removed':sum(row['meaningful_removed'] for name,row in rows.items() if name.startswith('tests/')),
    'inherited_ET1_product_LOC_credit':0,'runtime_generated_document_oracle_LOC_credit':0}
write_new(R/'implementation-measures.json',measures)
sys.path.insert(0,str(Q/'src'))
from ceta.store.sqlite_runtime import load_sqlite,runtime_identity
load_sqlite();imports={}
for path in sorted((Q/'src/ceta').rglob('*.py')):
    parts=path.relative_to(Q/'src').with_suffix('').parts
    name='.'.join(parts[:-1] if parts[-1]=='__init__' else parts)
    module=importlib.import_module(name);assert Path(module.__file__)==path
    imports[name]=ordinary(path)
assert len(imports)==82
write_new(R/'all-source-imports.json',{'at':utc(),'count':len(imports),'imports':imports,'sqlite_identity':runtime_identity()})
closure=json.loads((R/'parent-closure-r2.json').read_text());assert closure['exit_status']==0 and closure['tests_run']==2
baseline=json.loads((R/'baseline-r1.json').read_text());assert baseline['failures']==1 and baseline['errors']==0
assert closure['literal_class_ast_sha256']==baseline['literal_class_ast_sha256']
write_new(R/'SELF-REVIEW.json',{'at':utc(),'author':ACTOR,'independent_review':False,
    'qualification':reference(R/'connected-r1.json'),'parent_closure':reference(R/'parent-closure-r2.json'),
    'original_method_conservation':reference(R/'original-method-conservation.json'),
    'diffs':patches,'measures':reference(R/'implementation-measures.json'),'imports':reference(R/'all-source-imports.json'),
    'cohort_composition':dict(collections.Counter(n.split('.')[0] for n in proof['executed_ids'])),
    'inspected':['All ET2 changed code, existing begin/record/recover callers and typed request/enrollment budgets.',
        'Prior projection is verified against canonical attempt/settlement decisions before cumulative increment; same-store cell CAS prevents competing reuse.',
        'Original attempt count is separately immutable-bound; current projection totals cannot reset or replace that initial charge.',
        'Every logical canonical event/payload/projection/native-evidence batch is added, including replaced values; exact retries add no bytes.',
        'Recovery independently recomputes the latest batch; tests independently sum every retained canonical commit/change value for whole-request equality.',
        'Bounded fixed-point serialization includes its own decimal counters and decision commitments without a hash cycle.',
        'No changes to unique issuer/journal/public APIs/charged permit or intent, no refund/replay/new authority.',
        'Prior8KiB success assumption is rejected; finite controlled32KiB success inputs are explicit, shared contracts and production constants byte-exact.'],
    'limits':['Logical canonical evidence payloads counted once per write; internal transaction metadata/duplicate physical rows/SQLite index/page/WAL overhead remain separately unqualified.',
        'Actual native proof/currentness/evidence producer and observer integration remain unqualified; controlled fixtures are not production proof.',
        'No Source publication, native policy operation, Hello/profile/production activation performed.'],
    'Source_application':False,'genuine_native_effect_invocation':False})
print(json.dumps({'tests':394,'source_added':measures['new_source_LOC'],'source_removed':measures['source_removed'],
    'test_added':measures['new_test_LOC'],'modules':len(imports)}))
