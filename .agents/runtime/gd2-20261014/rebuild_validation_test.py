"""Preserve the independent class exactly and separate new unique test methods."""
import ast
import hashlib
import json
from pathlib import Path

R = Path(__file__).resolve().parent
F = R.parents[2]
target = F / '.agents/gd2-20261014/tests/contract/test_process_observation_validation.py'
oracle = F / '.agents/runtime/gd1-20261014/independent-review/hostile_timing_probes.py'
before = target.read_bytes()
with (R / 'validation-test-edit-attempt-r1.py').open('xb') as stream:
    stream.write(before)
text = before.decode('utf-8')
tree = ast.parse(text)
new = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'NestedMeasurementValidationTests')
last = next(node for node in new.body if isinstance(node, ast.FunctionDef) and node.name == 'test_unavailable_value_and_reason_mutations_are_rejected_without_order_adoption')
new_text = '\n'.join(text.splitlines()[new.lineno - 1:last.end_lineno])
old_text = oracle.read_text(encoding='utf-8')
old = next(node for node in ast.parse(old_text).body if isinstance(node, ast.ClassDef) and node.name == 'IndependentTimingBoundaryTests')
prefix = '\n'.join(text.splitlines()[:13])
result = prefix + '\n' + ast.get_source_segment(old_text, old) + '\n\n# Retain the fixture function without duplicate imported TestCase discovery.\ndel ProcessObservationTimingTests\n\n' + new_text + '\n'
out = ast.parse(result)
classes = [node for node in out.body if isinstance(node, ast.ClassDef)]
assert [node.name for node in classes] == ['IndependentTimingBoundaryTests', 'NestedMeasurementValidationTests']
assert ast.dump(classes[0], include_attributes=False) == ast.dump(old, include_attributes=False)
assert [sum(isinstance(item, ast.FunctionDef) and item.name.startswith('test_') for item in node.body) for node in classes] == [7, 6]
target.write_text(result, encoding='utf-8', newline='\n')
with (R / 'validation-test-correction.json').open('x', encoding='utf-8') as stream:
    json.dump({'before_sha256': hashlib.sha256(before).hexdigest(),
               'after_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
               'original_seven_class_AST_exact': True, 'new_methods': 6,
               'historical_baseline_and_closure': '33 methods included 26 imported fixture methods; retained as recorded, not newly authored',
               'edit_correction': 'First patch context landed before remaining independent methods; original class restored exactly before tests'}, stream, indent=2)
    stream.write('\n')
print('Exact seven original methods and six new methods separated; imported fixture class retired from discovery.')
