"""Audit actual narrow diffs, immutable dependencies and qualification scope."""
from et_support import *
import ast, difflib, importlib

parent = F / '.agents/et2-20261014'
staged = json.loads((R / 'STAGED-INPUTS.json').read_text())['payloads']
changed = []
for name, facts in staged.items():
    assert ordinary(parent / name)['sha256'] == facts['sha256']
    if ordinary(Q / name)['sha256'] != facts['sha256']: changed.append(name)
assert set(changed) == {'src/ceta/kernel/effect_transactions.py', 'contracts/OWNED_CPU_OUTCOME_V1.md'}
def definitions(path):
    result = {}
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = ast.dump(node, include_attributes=False)
        elif isinstance(node,ast.ClassDef):
            for child in node.body:
                if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    result[node.name+'.'+child.name] = ast.dump(child, include_attributes=False)
    return result
code = 'src/ceta/kernel/effect_transactions.py'
before, after = definitions(parent / code), definitions(Q / code)
assert set(before) == set(after)
altered = [name for name in before if before[name] != after[name]]
assert altered == ['KernelEffectTransactions.record']
tests = 'tests/contract/test_owned_cpu_outcome_transactions.py'
assert definitions(parent / tests) == definitions(Q / tests)
assert sha(parent / tests) == sha(Q / tests)
new_tests = definitions(Q / 'tests/contract/test_fresh_observer_reconciliation.py')
new_methods = [name for name in new_tests if name.split('.')[-1].startswith('test_')]
assert len(new_methods) == 12

def meaningful(lines):
    return sum(bool(line.strip()) and not line.lstrip().startswith('#') for line in lines)
old = (parent / code).read_text().splitlines()
new = (Q / code).read_text().splitlines()
added = removed = 0
for tag,a,b,c,d in difflib.SequenceMatcher(a=old,b=new,autojunk=False).get_opcodes():
    if tag in ('replace','delete'): removed += meaningful(old[a:b])
    if tag in ('replace','insert'): added += meaningful(new[c:d])
test_lines = (Q / 'tests/contract/test_fresh_observer_reconciliation.py').read_text().splitlines()
write_new(R / 'implementation-measures.json', {'at': utc(), 'new_source_LOC': added,
    'source_removed': removed, 'new_test_LOC': meaningful(test_lines), 'new_methods': len(new_methods),
    'basis': 'Physical nonblank/noncomment added and removed source/test lines; no copied dependency, document, evidence or runtime-support credit.',
    'inherited_payloads_LOC_credit': 0})
for name in changed:
    with (R / (name.replace('/','__') + '.diff')).open('x',encoding='utf-8') as stream:
        stream.write(''.join(difflib.unified_diff((parent/name).read_text().splitlines(True),
            (Q/name).read_text().splitlines(True),fromfile='ET2/'+name,tofile='ET3/'+name)))
sys.path.insert(0,str(Q/'src'))
modules=[]
for path in sorted((Q/'src/ceta').rglob('*.py')):
    relative=path.relative_to(Q/'src').with_suffix('')
    name='.'.join(relative.parts)
    if name.endswith('.__init__'): name=name[:-9]
    loaded=importlib.import_module(name)
    assert Path(loaded.__file__).resolve().is_relative_to((Q/'src').resolve())
    modules.append({'module':name,'path':str(Path(loaded.__file__))})
source=json.loads((R/'SOURCE-INPUTS.json').read_text())['Source290']
assert {name:ordinary(F/name) for name in source} == source
write_new(R/'SELF-REVIEW.json', {'at':utc(), 'reviewer':ACTOR, 'self_review_only':True,
    'changed_parent_paths':changed, 'unchanged_parent_payloads':len(staged)-len(changed),
    'only_changed_code_definition':altered, 'original_test_file_bytes_exact':True,
    'original_method_count':sum(name.split('.')[-1].startswith('test_') for name in definitions(parent/tests)),
    'new_test_methods':new_methods, 'all_imported_modules':modules, 'Source290_native_bytes_exact':True,
    'review_points':[
        'Captured native-owner predicate and its exact-None result remain unchanged before/in/after each transaction.',
        'Fresh lifetime requires equal observer image, strictly greater sequence/time, unchanged request/target/job/observer implementation, and authenticated current proof.',
        'Native child lifetime remains in canonical observer_session and immutable original observation; no evidence overwrite.',
        'Canonical charged liability, cumulative accounting, exact retry and terminal-settlement denial remain unchanged.',
        'New observer-controller restart sequence continuity still requires native composition; a PID change does not reset sequence.',
        'No dispatcher, native observer runtime, issuer, store, capacity limit, authority interface or original test changed.'
    ],
    'limits':['Positive provenance is controlled in these SQLite tests. Actual native provider integration remains unqualified.',
        'This author cut awaits distinct review and guarded joined application.']})
print(json.dumps({'source_added':added,'source_removed':removed,'test_added':meaningful(test_lines),
    'new_methods':len(new_methods),'imports':len(modules),'original_tests_exact':True}))
