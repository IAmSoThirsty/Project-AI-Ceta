"""Source-bound scope/AST/LOC self-review, separate from independent review."""
from ac2_support import *
import ast, difflib

inputs = json.loads((R / 'source-inputs.json').read_text())
eligible = inputs['scope']
current = {name: ordinary(Q / name) for name in set(inputs['source_payloads']) | set(eligible)}
assert len(current) == 294
assert all(current[name]['sha256'] == row['sha256'] for name,row in inputs['source_payloads'].items())
for name in eligible:
    try: fs.lstat(F / name)
    except FileNotFoundError: pass
    else: raise AssertionError('CREATE target occupied: ' + name)

def methods(path):
    tree = ast.parse(Path(path).read_bytes())
    return {node.name + '.' + item.name: ast.dump(item, include_attributes=False)
            for node in tree.body if isinstance(node, ast.ClassDef)
            for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))}
old_methods = methods(PARENT / 'tests/contract/test_isolated_worker.py')
new_methods = methods(Q / 'tests/contract/test_isolated_worker.py')
assert all(new_methods[name] == body for name,body in old_methods.items())
assert fs.read_bytes(Q / 'tests/contract/test_windows_jobs.py') == fs.read_bytes(PARENT / 'tests/contract/test_windows_jobs.py')
assert fs.read_bytes(Q / 'native/windows_broker/isolated_worker.rs') == fs.read_bytes(PARENT / 'native/windows_broker/isolated_worker.rs')

def meaningful(raw):
    lines = raw.decode('utf-8').splitlines()
    tree = ast.parse(raw)
    excluded = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                excluded.update(range(first.lineno - 1, first.end_lineno))
    return lines, {index for index,line in enumerate(lines) if line.strip() and not line.lstrip().startswith('#') and index not in excluded}

measures = {}; diff_root = R / 'diffs'; diff_root.mkdir()
for name in eligible:
    prior, now = fs.read_bytes(PARENT / name), fs.read_bytes(Q / name)
    old_lines, new_lines = prior.decode('utf-8').splitlines(), now.decode('utf-8').splitlines()
    diff = ''.join(difflib.unified_diff(prior.decode('utf-8').splitlines(True), now.decode('utf-8').splitlines(True),
                                     fromfile='frozen-AC1/' + name, tofile='AC2/' + name))
    diff_path = diff_root / (name.replace('/', '__') + '.diff'); fs.write_new(diff_path, diff.encode('utf-8'))
    row = {'parent_sha256': digest(prior), 'candidate_sha256': digest(now), 'byte_exact_reuse': prior == now,
           'parent_physical_lines': len(old_lines), 'candidate_physical_lines': len(new_lines),
           'diff': reference(diff_path)}
    if name.endswith('.py'):
        old_lines, old_code = meaningful(prior); new_lines, new_code = meaningful(now)
        added = removed = 0
        for op, a, b, c, d in difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False).get_opcodes():
            if op != 'equal':
                added += sum(index in new_code for index in range(c, d))
                removed += sum(index in old_code for index in range(a, b))
        row.update(new_meaningful_lines=added, removed_meaningful_lines=removed,
                   net_meaningful_lines=added - removed,
                   prospective_source_integration_meaningful_lines=len(new_code))
    measures[name] = row
source_name = 'src/ceta/supervisor/isolated_worker.py'
test_name = 'tests/contract/test_isolated_worker.py'
record = {'observed_at': utc(), 'comparison': 'Fresh successor versus frozen rejected AC1; not all future CREATE payload LOC is newly authored here',
    'by_path': measures, 'new_source_LOC': measures[source_name]['new_meaningful_lines'],
    'removed_parent_source_LOC': measures[source_name]['removed_meaningful_lines'],
    'new_test_LOC': measures[test_name]['new_meaningful_lines'], 'reused_native_Rust_LOC_credit': 0,
    'new_contract_LOC_is_executable': False, 'runtime_helpers_or_generated_artifacts_product_LOC_credit': 0,
    'method': 'Difflib changed lines excluding blanks, comment-only lines and AST docstrings; ABI/import/control declarations retained as source lines'}
write_new(R / 'implementation-measures.json', record)
write_new(R / 'SELF-REVIEW.json', {'observed_at': utc(), 'author': ACTOR, 'independent': False,
    'eligible_paths': eligible, 'changed_parent_paths': [name for name,row in measures.items() if not row['byte_exact_reuse']],
    'all_290_current_source_dependencies_byte_exact': True, 'four_active_source_targets_absent': True,
    'all_original_isolated_test_method_ASTs_exact': len(old_methods), 'all_original_windows_job_test_bytes_exact': True,
    'public_launch_and_appcontainer_sid_signatures_retained': True,
    'native_rust_and_compiled_helper_unchanged_reuse': True,
    'code_review': ['Inspected all changed cleanup methods and launch/token/SID callers.',
        'No mutable global authority or new scheduler/store/issuer.',
        'Duplicate handles are noninheritable and bind exact kernel objects before native retry.',
        'SID/local/attribute uncertainty is recorded before calls; malformed/unknown results cannot authorize another free.',
        'Every independent cleanup list is attempted; original control objects and explicit caller cleanup survive secondary observations/notes.',
        'Concurrent explicit recovery is serialized under API-local RLock; live canonical process close stays governed by its existing owner.'],
    'remaining_requirements': ['Positive restrictive worker and all access/network/escape probes remain unexecuted after actual error2.',
        'Actual post-create restrictive-child cleanup paths remain unqualified.',
        'Unknown post-call finalization is caller-visible unresolved state; no universal retirement or absence-of-leaks claim.',
        'Canonical production authority/evidence/composition and any persistent profile decision remain open.',
        'Separate reviewer must qualify this candidate before Source admission.'],
    'prior_failures': [reference(R / 'baseline-reproduction.json'), reference(R / 'failed-cuts/dll-binding-r1/failure.json'),
        {'classification': 'FIXED_AUTHOR_PATCH_CONTEXT', 'reason': 'One atomic apply_patch expected a different contract heading; no files changed. Correct actual heading read and minimal patch reapplied.'}],
    'measurements': reference(R / 'implementation-measures.json')})
print(json.dumps({'source_LOC_added': record['new_source_LOC'], 'source_parent_LOC_removed': record['removed_parent_source_LOC'],
                  'test_LOC_added': record['new_test_LOC'], 'original_method_ASTs': len(old_methods)}), flush=True)
