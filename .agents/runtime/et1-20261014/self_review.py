"""Finite author review of the exact functional cut and existing consumers."""
from et_support import *
import ast, collections, difflib, importlib
proof = json.loads((R / 'connected-r1.json').read_text())
assert proof['tests_run'] == proof['unique_methods'] == 385 and proof['exit_status'] == 0
assert not proof['failures'] and not proof['errors'] and not proof['skips']
assert proof['expected_ids'] == proof['executed_ids'] == proof['stopped_ids']
assert proof['candidate_before'] == proof['candidate_after'] and len(proof['candidate_after']) == 316
for name, row in proof['candidate_after'].items(): assert ordinary(Q / name) == row
assert len(proof['crash_observations']) == 2
assert sorted(row['exit_code'] for row in proof['crash_observations']) == [71, 72]
assert proof['all_fixture_stores_closed'] and not proof['new_threads_remaining']
inputs = json.loads((R / 'SOURCE-INPUTS.json').read_text())
scope = inputs['eligible_paths']
before = R / 'before-images/src/ceta/kernel/transactions.py'
old_tree, new_tree = ast.parse(before.read_text()), ast.parse((Q / scope[1]).read_text())
old_class = next(n for n in old_tree.body if isinstance(n, ast.ClassDef) and n.name == 'KernelTransactions')
new_class = next(n for n in new_tree.body if isinstance(n, ast.ClassDef) and n.name == 'KernelTransactions')
old_methods = {n.name: n for n in old_class.body if isinstance(n, ast.FunctionDef)}
new_methods = {n.name: n for n in new_class.body if isinstance(n, ast.FunctionDef)}
added = set(new_methods) - set(old_methods)
assert added == {'begin_owned_cpu_attempt', 'record_owned_cpu_outcome', 'recover_owned_cpu_outcome'}
for name, node in old_methods.items():
    replacement = new_methods[name]
    assert ast.dump(node.args, include_attributes=False) == ast.dump(replacement.args, include_attributes=False)
    if name != '__init__': assert ast.dump(node, include_attributes=False) == ast.dump(replacement, include_attributes=False)
assert len(new_methods['__init__'].body) == len(old_methods['__init__'].body) + 1
write_new(R / 'baseline-API-inspection.json', {'recorded_at': utc(), 'KA1_before_image': ordinary(before),
    'new_APIs_absent_at_baseline': sorted(added), 'existing_consumption_and_all_other_method_ASTs_exact': True,
    'classification': 'Missing dependency-ready functionality; no old native effect/outcome implementation was claimed.'})

measurement = ast.parse((F / '.agents/runtime/na1-20261014/self_review.py').read_text())
space = {'ast': ast}
node = next(n for n in measurement.body if isinstance(n, ast.FunctionDef) and n.name == 'python_lines')
exec(compile(ast.Module(body=[node], type_ignores=[]), '<retained-LOC-measurement>', 'exec'), space)
by_path, patches = {}, {}
for name in scope:
    text = (Q / name).read_text()
    original = before.read_text() if name == scope[1] else ''
    old_lines = original.splitlines(); new_lines = text.splitlines()
    if name.endswith('.py'):
        tree, meaningful = space['python_lines'](text)
        old_meaningful = space['python_lines'](original)[1]
    else: meaningful, old_meaningful, tree = set(), set(), None
    added_lines, removed_lines, excluded = set(), set(), set()
    for tag, a, b, c, d in difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False).get_opcodes():
        if tag in ('replace', 'insert'): added_lines.update(range(c + 1, d + 1))
        if tag in ('replace', 'delete'): removed_lines.update(range(a + 1, b + 1))
    # Conservative zero credit for adapted canonical owner elapsed/record/index
    # scaffolding. New outcome-specific validation and transaction logic remains
    # counted, with the exact exclusion ranges available to the reviewer.
    adapted = []
    if name == scope[0]:
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef) and n.name in ('__init__', '_guard', '_decision', '_index', '_resolve'):
                excluded.update(range(n.lineno, n.end_lineno + 1)); adapted.append({'name': n.name, 'start': n.lineno, 'end': n.end_lineno})
    by_path[name] = {'sha256': sha(Q / name), 'physical_lines': len(new_lines),
        'physical_added': len(added_lines), 'physical_removed': len(removed_lines),
        'meaningful_added_before_reuse_exclusion': len(added_lines & meaningful),
        'meaningful_added_credited': len(added_lines & meaningful - excluded),
        'meaningful_removed': len(removed_lines & old_meaningful),
        'adapted_patterns_zero_credit': adapted, 'adapted_lines_excluded': len(added_lines & meaningful & excluded)}
    path = R / (name.replace('/', '__') + '.diff')
    with path.open('x', encoding='utf-8', newline='\n') as output:
        output.writelines(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
            fromfile='frozen-KA1/' + name if original else 'absent/' + name, tofile='ET1/' + name))
    patches[name] = reference(path)
measures = {'recorded_at': utc(), 'by_path': by_path,
    'new_source_LOC': sum(r['meaningful_added_credited'] for n, r in by_path.items() if n.startswith('src/')),
    'new_test_LOC': sum(r['meaningful_added_credited'] for n, r in by_path.items() if n.startswith('tests/')),
    'physical_source_added': sum(r['physical_added'] for n, r in by_path.items() if n.startswith('src/')),
    'source_removed': sum(r['meaningful_removed'] for n, r in by_path.items() if n.startswith('src/')),
    'uncredited_staged_dependencies': 312, 'runtime_evidence_or_native_artifact_LOC_credit': 0,
    'comparison': 'transactions.py delta is against exact frozen KA1; other three product paths are CREATE. Dependencies, adapted scaffolding, documentation and runtime artifacts have zero executable LOC credit.'}
write_new(R / 'implementation-measures.json', measures)
sys.path.insert(0, str(Q / 'src'))
from ceta.store.sqlite_runtime import load_sqlite, runtime_identity
load_sqlite()
imports = {}
for path in sorted((Q / 'src/ceta').rglob('*.py')):
    parts = path.relative_to(Q / 'src').with_suffix('').parts
    name = '.'.join(parts[:-1] if parts[-1] == '__init__' else parts)
    module = importlib.import_module(name); assert Path(module.__file__) == path
    imports[name] = ordinary(path)
write_new(R / 'all-source-imports.json', {'recorded_at': utc(), 'count': len(imports), 'imports': imports,
    'sqlite_identity': runtime_identity()})
write_new(R / 'SELF-REVIEW.json', {'recorded_at': utc(), 'author': ACTOR, 'independent_review': False,
    'qualification': reference(R / 'connected-r1.json'), 'raw': reference(R / 'connected-r1.txt'),
    'cohort_composition': dict(collections.Counter(n.split('.')[0] for n in proof['executed_ids'])),
    'baseline_API': reference(R / 'baseline-API-inspection.json'), 'diffs': patches,
    'measures': reference(R / 'implementation-measures.json'), 'imports': reference(R / 'all-source-imports.json'),
    'source_conservation': reference(R / 'input-conservation.json'),
    'checks': ['One existing kernel and captured journal; no new issuer, scheduler, policy engine or competing evidence store.',
        'Original ADMISSION_REDEEMED intent/consumed permit/charged allocation and old recovery consumers retained exactly.',
        'A reserved attempt is not native Set evidence; all returned values are historical data, not dispatch permission.',
        'Producer/observer proof must be authenticated by the captured native owner; missing/malformed/default provider denies.',
        'Receipt, optional independent observation, settlement, task outcome and immutable native bytes share one transaction/CAS.',
        'No refund or no-effect inference from missing telemetry; uncertain evidence can reconcile with strict sequence/time/lifetime advancement.',
        'Exact settlement counts/clock/revision are bound to canonical history; wrong event indexes and projection tampering fail.',
        'Actual serialized bytes remain within the declared reservation; physical filesystem/SQLite overhead guarantee is not claimed.',
        'Read-only recovery and exact retry issue no permit or native operation; restoration needs separate approval/consumption/proof.',
        'Real SQLite rollback, two real process crash exits, concurrency, primary/control failures and all mandatory old consumers executed.'],
    'remaining': ['Actual native outcome/currentness provider and independent observer wiring require Root composition and distinct qualification.',
        'No native CPU effect, real authentication, durable public runtime activation or physical power-loss qualification executed.'],
    'Source_application': False, 'genuine_native_effect_invocation': False})
print(json.dumps({'tests': 385, 'new_source_LOC': measures['new_source_LOC'], 'new_test_LOC': measures['new_test_LOC'],
    'source_removed': measures['source_removed'], 'modules': len(imports), 'journals_closed': len(proof['fixture_stores'])}))
