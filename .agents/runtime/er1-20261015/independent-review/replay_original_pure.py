"""Original ER1 helper with only its output expression relocated for this review.

The helper's static executor='/root' field remains original author metadata;
REPLAY-READBACK identifies the actual independent caller and the exact transform.
"""
import ast
import json
import sys
from review_support import R, V, s, read, conservation, ACTOR


def main():
    assert len(sys.argv) == 1
    source = R / 'run_pure.py'
    assert s.sha(source) == '59037bb0d471110139e1909596c1b388cb975cf29fb4b3c2b8d10bd8ef0cc68a'
    before = conservation()
    s.write_new(V / 'CONSERVATION-BEFORE.json', before)
    tree = ast.parse(source.read_bytes(), filename=str(source))
    original_dump = ast.dump(tree, include_attributes=False)
    main_function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    matches = [node for node in main_function.body if isinstance(node, ast.Assign)
        and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'output']
    assert len(matches) == 1
    target = matches[0]
    assert ast.dump(target.value, include_attributes=False) == ast.dump(ast.parse('R / label', mode='eval').body, include_attributes=False)
    old_value = target.value
    target.value = ast.parse('Path(' + repr(str(V)) + ') / label', mode='eval').body
    relocated_dump = ast.dump(tree, include_attributes=False)
    target.value = old_value
    assert ast.dump(tree, include_attributes=False) == original_dump
    target.value = ast.parse('Path(' + repr(str(V)) + ') / label', mode='eval').body
    ast.fix_missing_locations(tree)
    s.write_new(V / 'REPLAY-TRANSFORM.json', {'at': s.utc(), 'actual_executor': ACTOR,
        'original': s.reference(source), 'original_AST_sha256': s.digest(original_dump.encode()),
        'relocated_AST_sha256': s.digest(relocated_dump.encode()),
        'only_transformed_expression': 'output = R / label -> output = Path(V) / label',
        'original_input_R_preserved': str(R), 'output_V': str(V),
        'static_executor_literal': '/root', 'static_executor_literal_role': 'Original helper author field, not the independent caller'})
    namespace = {'__name__': 'er1_exact_pure_helper_for_independent_review', '__file__': str(source)}
    exec(compile(tree, str(source), 'exec'), namespace)
    previous_argv = sys.argv
    try:
        sys.argv = [str(source), 'pure-independent-r1']
        status = namespace['main']()
    finally:
        sys.argv = previous_argv
    after = conservation()
    assert before == after
    result = read(V / 'pure-independent-r1/RESULT.json')
    parent = read(R / 'pure-r1/RESULT.json')
    assert result['expected_ids'] == result['executed_ids'] == result['stopped_ids'] == parent['expected_ids']
    assert result['tests_run'] == 85 and result['failures'] == result['errors'] == result['skips'] == 0 and status == 0
    s.write_new(V / 'REPLAY-READBACK.json', {'at': s.utc(), 'actual_executor': ACTOR,
        'source_helper_author_literal_preserved': result['executor'], 'helper_output_executor_is_actual_caller': False,
        'scope': 'Independent pure85 replay, original helper author literal explicitly separated',
        'tests_run': 85, 'failures': 0, 'errors': 0, 'skips': 0,
        'exact_author85_ID_arrays_preserved': True, 'result': s.reference(V / 'pure-independent-r1/RESULT.json'),
        'transform': s.reference(V / 'REPLAY-TRANSFORM.json'), 'before': s.reference(V / 'CONSERVATION-BEFORE.json'),
        'conservation_after': after, 'Source_publication': False, 'full_gate_complete': False})
    print(json.dumps({'readback': s.reference(V / 'REPLAY-READBACK.json'), 'tests_run': 85, 'exit_status': status}), flush=True)
    return status


if __name__ == '__main__':
    sys.exit(main())
