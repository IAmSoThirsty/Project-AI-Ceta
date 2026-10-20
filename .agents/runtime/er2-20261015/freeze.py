"""Seal only the narrow executed ER2 repair for an independent reviewer."""
from pathlib import Path
import ast
import difflib
import io
import json
import sys
import tokenize

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q, P = F / '.agents/er2-20261015', F / '.agents/js3-20261015'
sys.path.insert(0, str(F / '.agents/runtime/ka1-20261014'))
import ka1_support as s
s.Q, s.R, s.RUN, s.ACTOR = Q, R, Q.name, '/root'


def read(path):
    return json.loads(path.read_bytes())


def meaningful(raw):
    text = raw.decode('utf-8')
    docs = set()
    for node in ast.walk(ast.parse(text)):
        body = getattr(node, 'body', None)
        if (isinstance(body, list) and body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant) and type(body[0].value.value) is str):
            docs.update(range(body[0].lineno, body[0].end_lineno + 1))
    ignored = {tokenize.COMMENT, tokenize.ENCODING, tokenize.INDENT,
               tokenize.DEDENT, tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER}
    active = set()
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type not in ignored and token.string.strip():
            active.update(range(token.start[0], token.end[0] + 1))
    return text.splitlines(), active - docs


def main():
    inputs, binding = read(R / 'SOURCE-INPUTS.json'), read(R / 'TASK-BINDING.json')
    selected = set(binding['eligible_paths'])
    names = [*inputs['parent294'], 'tests/contract/test_editor_retention_queue.py']
    candidate = {name: s.ordinary(Q / name) for name in names}
    assert len(candidate) == 295
    for name, row in inputs['parent294'].items():
        assert s.ordinary(P / name) == row
        if name not in selected:
            assert candidate[name]['sha256'] == row['sha256'], name
    for name, row in inputs['auxiliary_parent11'].items():
        assert s.ordinary(P / name) == row
        assert s.ordinary(Q / name)['sha256'] == row['sha256']
    for name, row in inputs['Source290'].items():
        assert s.ordinary(F / name) == row
    for name, row in inputs['E33601'].items():
        assert s.ordinary(s.PY.parents[1] / name) == row
    assert s.ordinary(s.PY) == inputs['python']
    assert s.ordinary(Path(sys._base_executable)) == inputs['base_python']
    assert s.fs.text_git(F, 'rev-parse', 'HEAD') == inputs['Git']['HEAD']
    source_name = 'src/ceta/application/task_operator.py'
    old_tree, new_tree = ast.parse((P / source_name).read_bytes()), ast.parse((Q / source_name).read_bytes())
    signatures = lambda tree: [(node.name, ast.dump(node.args, include_attributes=False))
        for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert signatures(old_tree) == signatures(new_tree)
    original_tests = [name for name in inputs['parent294'] if name.startswith('tests/')]
    assert all(candidate[name]['sha256'] == inputs['parent294'][name]['sha256'] for name in original_tests)
    before = read(R / 'before-r2/RESULT.json')
    assert before['tests_run'] == 5 and before['failures'] == 2 and before['errors'] == before['skips'] == 0
    qualified = []
    for label, count in (('after-r1', 5), ('connected-r1', 106)):
        proof, outer = read(R / label / 'RESULT.json'), read(R / (label + '-LAUNCH.json'))
        assert proof['tests_run'] == count
        assert all(type(proof[k]) is int and proof[k] == 0 for k in ('failures', 'errors', 'skips', 'exit_status'))
        assert proof['expected_ids'] == proof['executed_ids'] == proof['stopped_ids']
        assert len(set(proof['expected_ids'])) == count and proof['remaining_threads'] == []
        assert proof['all_observed_fixture_connections_closed'] is True
        assert proof['candidate_before'] == proof['candidate_after'] == candidate
        assert proof['Source290_exact'] is proof['parent294_exact'] is proof['all_ceta_imports_from_candidate'] is True
        assert outer['exit_status'] == 0 and outer['primary_error'] is None
        assert outer['record']['child_exit'] == 0 and outer['record']['retirement_error'] is None
        assert all(value is True for value in outer['record']['native_owner_after'].values())
        assert outer['record']['child_result'] == s.reference(R / label / 'RESULT.json')
        qualified.append({'proof': s.reference(R / label / 'RESULT.json'),
                          'outer': s.reference(R / (label + '-LAUNCH.json'))})
    old, old_active = meaningful((P / source_name).read_bytes())
    new, new_active = meaningful((Q / source_name).read_bytes())
    added = removed = 0
    for tag, a, b, c, d in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_opcodes():
        if tag != 'equal':
            removed += sum(n + 1 in old_active for n in range(a, b))
            added += sum(n + 1 in new_active for n in range(c, d))
    _, test_lines = meaningful((Q / 'tests/contract/test_editor_retention_queue.py').read_bytes())
    loc = {'definition': 'Physical executable Python lines excluding blanks, comments and AST docstrings; component diff only.',
           'source_added': added, 'source_removed': removed, 'test_added': len(test_lines),
           'copied_parent_payloads_new_authorship_credit': 0, 'integrated_source_credit': 0,
           'fixture_reuse': 'Existing helper methods and original test body called unchanged; no borrowed body copied or counted as newly authored.'}
    limits = ['Component qualification only; Source remains290 and JS3validateFAILED11 is preserved.',
        '106 unique connected IDs include five new controlled-clock methods and101 unchanged originals; separate five-method run is repeat evidence, not five additional unique cases.',
        'Fixture delivery/authentication/Stop are controlled; real Qt and SQLite are exercised; native production owner authorization is not established.',
        'Physical SQLite probes cover exact retained fixture-returned connections; no generic unobserved-resource completeness is claimed.',
        'Full successor integration, destination full and distinct delivered acceptance remain required.']
    s.write_new(R / 'LOC.json', loc)
    s.write_new(R / 'SELF-REVIEW.json', {'at': s.utc(), 'author': '/root', 'independent_review': False,
        'inspected': ['Actual original failing Qt method and held-delivery completion loop',
            'Every capture/drain/result/Stop/uncertainty branch and original method callers',
            'Deterministic two failures before/zero after with unchanged five test method bodies',
            'Exact106 IDs, original test bytes, public signatures, physical closed-connection and held-job proof',
            'One-line source behavior; documentation preserves normal150ms coalescing and authority limits'],
        'limits': limits, 'LOC': loc})
    manifest = {'schema_version': 1, 'at': s.utc(), 'author': '/root', 'candidate_root': str(Q),
        'parent_manifest': inputs['parent_manifest'], 'parent_complete_gate': inputs['parent_complete_failure'],
        'payload_count': 295, 'REUSE': 292, 'EXTEND': 2, 'CREATE': 1,
        'eligible_application_paths': sorted(selected), 'payloads': {
            name: {'candidate': row, 'parent': inputs['parent294'].get(name),
                'classification': ('EXTEND' if name in inputs['parent294'] else 'CREATE') if name in selected else 'REUSE'}
            for name, row in candidate.items()},
        'public_signatures_unchanged': True, 'original_parent_test_files_byte_exact': len(original_tests),
        'qualified': qualified, 'tests': qualified[-1]['proof'], 'LOC': loc,
        'deterministic_before': s.reference(R / 'DETERMINISTIC-REPRODUCTION.json'),
        'prior_preparation_failure': s.reference(R / 'WRAPPER-PREPARATION-FAILURE-R1.json'),
        'scripts': {name: s.sha(R / name) for name in ('bootstrap.py', 'run_tests.py', 'launch_tests.py', 'freeze.py')},
        'limits': limits, 'Source_publication': False, 'full_gate_complete': False, 'Source_accepted': False}
    s.write_new(Q / 'TRANSFER-MANIFEST.json', manifest)
    commands = [{'command': str(s.PY) + ' -B -X utf8 ' + str(R / 'launch_tests.py') + ' after-r1', 'exit_status': 0},
                {'command': str(s.PY) + ' -B -X utf8 ' + str(R / 'launch_tests.py') + ' connected-r1 --cohort', 'exit_status': 0}]
    s.complete('implement', {'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'),
        'manifest_sha256': s.sha(Q / 'TRANSFER-MANIFEST.json'), 'tests': manifest['tests'], 'LOC': loc,
        'failure_lineage': manifest['deterministic_before'], 'limits': limits}, commands,
        [('all106_connected_methods_pass_with_unchanged_original_tests_and_closed_known_custody', True),
         ('two_deterministic_before_failures_repaired_without_original_assertion_or_deadline_changes', True),
         ('Source290_parent294_E33601_conserved_and_no_publication', True)])
    state, claims = read(R / s.RUN / 'state.json'), read(R / s.RUN / 'claims.json')
    assert state['nodes']['implement']['state'] == 'SUCCEEDED' and state['nodes']['review']['state'] == 'READY'
    assert state['sequence'] == 7 and claims == {}
    s.write_new(R / 'AUTHOR-READBACK.json', {'at': s.utc(), 'state': state, 'claims': claims,
        'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'), 'implement': s.reference(R / 'implement.json'),
        'Source_publication': False, 'Source_accepted': False})
    members = [Q / name for name in candidate]
    members += [Q / 'TRANSFER-MANIFEST.json', *[R / name for name in manifest['scripts']],
        R / 'SOURCE-INPUTS.json', R / 'TASK-BINDING.json', R / 'LOC.json', R / 'SELF-REVIEW.json',
        R / 'DETERMINISTIC-REPRODUCTION.json', R / 'WRAPPER-PREPARATION-FAILURE-R1.json',
        R / 'AUTHOR-READBACK.json', R / 'implement.json']
    for label in ('before-r2', 'after-r1', 'connected-r1'):
        members += [R / label / 'RESULT.json', R / label / 'RAW.txt', R / (label + '-LAUNCH.json')]
    s.write_new(R / 'AUTHOR-SEAL.json', {'at': s.utc(), 'members': [s.ordinary(path) for path in members],
        'Source_publication': False, 'Source_accepted': False, 'full_gate_complete': False})
    print(json.dumps({'manifest': s.reference(Q / 'TRANSFER-MANIFEST.json'),
        'readback': s.reference(R / 'AUTHOR-READBACK.json'), 'seal': s.reference(R / 'AUTHOR-SEAL.json'),
        'LOC': loc, 'implement': 'SUCCEEDED', 'review': 'READY', 'claims': {}}), flush=True)


if __name__ == '__main__':
    main()
