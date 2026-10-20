"""Release exact bounded ER1 implementation for a distinct reviewer."""
from pathlib import Path
import ast
import difflib
import json
import sys

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q, P = F / '.agents/er1-20261015', F / '.agents/js2-20261015'
sys.dont_write_bytecode = True
sys.path.insert(0, str(F / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q, s.R, s.RUN, s.ACTOR = Q, R, Q.name, '/root'


def read(path):
    return json.loads(path.read_bytes())


def meaningful(path):
    lines = path.read_text(encoding='utf-8').splitlines()
    doc = set()
    for node in ast.walk(ast.parse('\n'.join(lines))):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                if isinstance(node.body[0].value.value, str):
                    doc.update(range(node.body[0].lineno - 1, node.body[0].end_lineno))
    return lines, {i for i, text in enumerate(lines)
                   if text.strip() and not text.lstrip().startswith('#') and i not in doc}


def public_signatures(path):
    tree = ast.parse(path.read_bytes())
    return {node.name: ast.dump(node.args, include_attributes=False)
        for node in tree.body if isinstance(node, ast.FunctionDef)}


def main():
    assert len(sys.argv) == 1
    inputs = read(R / 'SOURCE-INPUTS.json')
    binding = read(R / 'TASK-BINDING.json')
    proof = read(R / 'pure-r1/RESULT.json')
    assert proof['tests_run'] == 85 and proof['expected_ids'] == proof['executed_ids'] == proof['stopped_ids']
    assert all(proof[key] == 0 for key in ('failures', 'errors', 'skips', 'exit_status'))
    assert proof['all_imports_from_candidate_pure_leaf'] and not proof['remaining_threads']
    assert not proof['blocked_noncontract_import_attempts']
    assert proof['candidate_before'] == proof['candidate_after']
    assert proof['Source290_after'] == inputs['Source290']
    assert proof['parent292_after'] == inputs['parent292']
    selected = set(binding['eligible_paths'])
    names = [*inputs['parent292'], 'tests/contract/test_wire_scanning.py']
    candidate = {name: s.ordinary(Q / name) for name in names}
    assert candidate == proof['candidate_after'] and len(candidate) == 293
    for name, row in inputs['parent292'].items():
        assert s.ordinary(P / name) == row
        if name not in selected:
            assert candidate[name]['sha256'] == row['sha256'], name
    assert {name: s.ordinary(F / name) for name in inputs['Source290']} == inputs['Source290']
    changes = []
    added = removed = 0
    for name in sorted(selected):
        if name.startswith('src/'):
            assert public_signatures(P / name) == public_signatures(Q / name)
            old, oi = meaningful(P / name)
            new, ni = meaningful(Q / name)
            a = d = 0
            for tag, i, j, k, l in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes():
                if tag != 'equal':
                    d += sum(index in oi for index in range(i, j))
                    a += sum(index in ni for index in range(k, l))
            changes.append({'path': name, 'source_added': a, 'source_removed': d})
            added += a
            removed += d
    test = Q / 'tests/contract/test_wire_scanning.py'
    _, ti = meaningful(test)
    node = next(n for n in ast.parse(test.read_bytes()).body
                if isinstance(n, ast.FunctionDef) and n.name == 'retained_preflight')
    copied = sum(i in ti for i in range(node.lineno - 1, node.end_lineno))
    old = next(n for n in ast.parse((P / 'src/ceta/contracts/wire.py').read_bytes()).body
               if isinstance(n, ast.FunctionDef) and n.name == '_preflight')
    assert ast.dump(ast.Module(body=node.body[1:], type_ignores=[]), include_attributes=False) == ast.dump(
        ast.Module(body=old.body, type_ignores=[]), include_attributes=False)
    loc = {'definition': 'Nonblank, noncomment physical Python lines excluding AST docstrings; source diff only; copied oracle excluded from authored tests',
        'source_added': added, 'source_removed': removed, 'test_added_physical': len(ti),
        'test_copied_oracle_uncredited': copied, 'test_added_authored': len(ti) - copied,
        'copied_dependency_source_credit': 0, 'integrated_source_credit': 0, 'source_paths': changes}
    s.write_new(R / 'LOC.json', loc)
    before = read(R / 'CODEC-PROFILE-R1.json')
    after = read(R / 'CODEC-PROFILE-AFTER-R1.json')
    assert before['request'] == after['request'] and after['exact_historical_request_binding_preserved']
    limits = ['Bounded pure-contract component; no native, journal, Qt, complete full-suite or Source acceptance is established.',
        'Earlier JS2 full qualification remains FAILED and integration BLOCKED; its journal component review remains separately bounded.',
        'Single profiled decode observations include profiling overhead; they establish neither a general performance ratio nor historical timeout cause.',
        'Original protocol APIs, byte/depth/Unicode/hex rules and original test payloads remain exact. The JSON parser still validates full syntax.',
        'Any later integration binds current accepted Source and distinct reviewed complete candidate; no old parent overlay or Source publication here.']
    s.write_new(R / 'SELF-REVIEW.json', {'at': s.utc(), 'author': '/root', 'independent_review': False,
        'inspected': ['Canonical profile requirements and complete changed source/callers',
            'Original strict-load and lowercase-hex rejection semantics',
            'Exact copied old scanner body as disclosed differential oracle',
            'All85 test IDs/execution and unchanged original tests',
            'Actual old staging request commitment and exact optimized decode binding',
            'Existing reference/chunk constants and state transitions reflected in corrected documentation'],
        'limits': limits, 'LOC': s.reference(R / 'LOC.json')})
    manifest = {'schema_version': 1, 'at': s.utc(), 'author': '/root', 'candidate_root': str(Q),
        'parent_manifest': inputs['parent_manifest'], 'parent_complete_gate': inputs['failed_full_gate'],
        'payload_count': 293, 'REUSE': 288, 'EXTEND': 4, 'CREATE': 1,
        'eligible_application_paths': sorted(selected), 'payloads': {
            name: {'candidate': row, 'parent': inputs['parent292'].get(name),
                   'classification': ('EXTEND' if name in inputs['parent292'] else 'CREATE') if name in selected else 'REUSE'}
            for name, row in candidate.items()},
        'original_parent_tests_byte_exact': True, 'public_signatures_unchanged': True,
        'tests': s.reference(R / 'pure-r1/RESULT.json'), 'LOC': loc,
        'profiles': [s.reference(R / 'CODEC-PROFILE-R1.json'), s.reference(R / 'CODEC-PROFILE-AFTER-R1.json')],
        'preserved_setup_failure': s.reference(R / 'BOOTSTRAP-COPY-FAILURE-R1.json'),
        'scripts': {name: s.sha(R / name) for name in ('bootstrap.py', 'resume_copy.py', 'run_pure.py',
            'profile_request.py', 'profile_after.py', 'freeze.py')},
        'limits': limits, 'Source_publication': False, 'full_gate_complete': False, 'Source_accepted': False}
    s.write_new(Q / 'TRANSFER-MANIFEST.json', manifest)
    s.complete('implement', {'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'),
        'tests': manifest['tests'], 'LOC': loc, 'profiles': manifest['profiles'], 'limits': limits},
        [{'command': str(s.PY) + ' -B -X utf8 ' + str(R / 'run_pure.py') + ' pure-r1', 'exit_status': 0},
         {'command': str(s.PY) + ' -B -X utf8 ' + str(R / 'profile_after.py'), 'exit_status': 0}],
        [('all85 pure contract methods pass with exact IDs and no forbidden import', True),
         ('all288 unselected parent payloads and Source290 unchanged', True),
         ('prior scanner oracle exact and public signatures preserved', True),
         ('historical staging request commitment preserved', True)])
    state, claims = read(R / s.RUN / 'state.json'), read(R / s.RUN / 'claims.json')
    assert state['nodes']['implement']['state'] == 'SUCCEEDED' and state['nodes']['review']['state'] == 'READY'
    assert claims == {} and state['sequence'] == 7
    s.write_new(R / 'AUTHOR-READBACK.json', {'at': s.utc(), 'implement': 'SUCCEEDED', 'review': 'READY',
        'sequence': 7, 'claims': {}, 'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'),
        'receipt': s.reference(R / 'implement.json'), 'Source_publication': False})
    paths = [Q / name for name in candidate]
    paths += [Q / 'TRANSFER-MANIFEST.json', *[R / name for name in manifest['scripts']],
              R / 'SOURCE-INPUTS.json', R / 'TASK-BINDING.json', R / 'COPIED-INPUTS.json', R / 'LOC.json',
              R / 'SELF-REVIEW.json', R / 'BOOTSTRAP-COPY-FAILURE-R1.json', R / 'AUTHOR-READBACK.json',
              R / 'implement.json', R / 'pure-r1/RESULT.json', R / 'pure-r1/RAW.txt',
              R / 'CODEC-PROFILE-R1.json', R / 'CODEC-PROFILE-R1.txt',
              R / 'CODEC-PROFILE-AFTER-R1.json', R / 'CODEC-PROFILE-AFTER-R1.txt']
    s.write_new(R / 'AUTHOR-SEAL.json', {'at': s.utc(), 'critical_members': [s.reference(p) for p in paths],
        'Source_publication': False, 'full_gate_complete': False})
    s.write_new(R / 'READY-FOR-REVIEW.json', {'at': s.utc(), 'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'),
        'author_readback': s.reference(R / 'AUTHOR-READBACK.json'), 'seal': s.reference(R / 'AUTHOR-SEAL.json'),
        'review': 'READY', 'claims': {}, 'pure_tests': 85, 'limits': limits})
    print(json.dumps({'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'),
        'readback': s.reference(R / 'AUTHOR-READBACK.json'), 'seal': s.reference(R / 'AUTHOR-SEAL.json'),
        'LOC': loc, 'review': 'READY', 'claims': {}}))


if __name__ == '__main__':
    main()
