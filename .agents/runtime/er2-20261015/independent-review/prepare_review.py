"""Pin bounded exact ER2 component inputs before independent execution."""
import ast
import copy
import difflib
import json
import uuid
from review_support import F, Q, P, R, V, MANIFEST, read, conservation, s


def main():
    assert conservation() == read(V / 'BEFORE.json')
    parent_source = ast.parse((P / 'src/ceta/application/task_operator.py').read_bytes())
    source = ast.parse((Q / 'src/ceta/application/task_operator.py').read_bytes())
    calls = [node for node in ast.walk(source) if isinstance(node, ast.Call)
        and any(key.arg == 'editor_next_attempt_at' and isinstance(key.value, ast.Constant)
            and key.value.value == 0.0 for key in node.keywords)]
    target = next(node for node in calls if node.lineno == 947)
    repaired = copy.deepcopy(source)
    corresponding = next(node for node in ast.walk(repaired) if isinstance(node, ast.Call) and node.lineno == 947)
    corresponding.keywords = [key for key in corresponding.keywords if key.arg != 'editor_next_attempt_at']
    assert ast.dump(repaired, include_attributes=False) == ast.dump(parent_source, include_attributes=False)
    manifest = read(Q / 'TRANSFER-MANIFEST.json')
    assert len(manifest['payloads']) == 295
    tests = [name for name in read(R / 'SOURCE-INPUTS.json')['parent294'] if name.startswith('tests/')]
    assert len(tests) == 83 and all((P / name).read_bytes() == (Q / name).read_bytes() for name in tests)
    for name, origin, pin in (
        ('resource_observer.py', F / '.agents/runtime/js3-20261015/independent-destination/resource_observer.py',
            'de5deb609eb8b57b2b52e695ec0b38e1eac05f31ada119e83e74b9157074fd4a'),
        ('bounded_custody.py', F / '.agents/runtime/js3-20261015/bounded_custody.py',
            '715b88ab286a524f5815ec3c47b987ba82cc50709272fdc467b7ddc76eeba1b4')):
        assert s.sha(origin) == pin
        s.fs.write_new(V / name, origin.read_bytes())
        assert s.sha(V / name) == pin
    fixture = Q / '.agents/fixtures' / ('er2-independent-' + uuid.uuid4().hex)
    assert not fixture.exists()
    helpers = {name: s.sha(V / name) for name in ('review_support.py', 'run_review.py', 'launch_review.py',
        'independent_retention_checks.py', 'resource_observer.py', 'bounded_custody.py')}
    for name in helpers: ast.parse((V / name).read_bytes())
    source_diff = '\n'.join(difflib.unified_diff((P / 'src/ceta/application/task_operator.py').read_text().splitlines(),
        (Q / 'src/ceta/application/task_operator.py').read_text().splitlines(), fromfile='parent', tofile='ER2'))
    s.fs.write_new(V / 'SOURCE.diff', source_diff.encode('utf-8'))
    s.write_new(V / 'PREPARATION.json', {'at': s.utc(), 'manifest_sha256': MANIFEST,
        'reviewer': '/root/wt1_reviewer', 'helpers': helpers, 'fixture_root': str(fixture),
        'fixture_absent_before_creation': True, 'fixture_creation_authorized_by':
            'Root direct message: inherited12 ordinary native editor cases and one fresh Q/.agents/fixtures/er2-independent-<freshUUID> child.',
        'expected_original_ids': read(R / 'connected-r1/RESULT.json')['expected_ids'],
        'expected_count': 108, 'original_count': 106, 'new_independent_count': 2,
        'original_test_files_unchanged': 83, 'only_product_AST_delta': 'One added editor_next_attempt_at=0.0 keyword at acknowledged old-retain/new-complete-capture branch.',
        'source_diff': s.reference(V / 'SOURCE.diff'), 'observations':
            'Exact original methods/deadlines; transparent returned SQLite registry; native service helper return/canonical closure observations.',
        'prohibited': ['profile creation', 'Hello forwarding', 'CPU Set', 'Source writes', 'historical PID action', 'full acceptance'],
        'copied_helper_authorship_credit': 0, 'Source_publication': False, 'full_gate_complete': False})
    print(json.dumps({'preparation': s.reference(V / 'PREPARATION.json'), 'helpers': helpers,
        'fixture_root': str(fixture), 'tests': 108}), flush=True)


if __name__ == '__main__': main()
