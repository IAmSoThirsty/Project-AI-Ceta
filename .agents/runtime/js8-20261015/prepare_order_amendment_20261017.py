"""Preserve the failed cut and stage one explicit integration-test amendment."""
from pathlib import Path
import ast
import copy
import difflib
import json
import sys

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import js8_support as parent

s, F = parent.s, parent.F
A = P / 'amendment-order1'
Q = F / '.agents/js8-amendment-order1-20261017'
assert not A.exists() and not Q.exists()
original, pin = parent.manifest_record()
assert pin == '64e424cece2cda9c5f91934fe1c2f503eab0fdf4364bd9b73c603464f33c38f1'
v = parent.verify()
failed = parent.current_json(P / 'candidate-full-LAUNCH-RESULT.json')
assert failed['exit_status'] == 1
assert failed['primary_error']['type'] == 'TimeoutError'
assert failed['record']['timeout_seconds'] == 900
assert all(failed['record']['native_owner_after'].values())
assert not (P / 'candidate-full/RESULT.json').exists()
name = 'tests/contract/test_cpu_execution_timing_diagnostics.py'
old = parent.pinned_bytes(parent.Q / name, original['expected_payload_hashes'][name])
text = old.decode('utf-8')
method = '    def test_authenticated_stop_and_slow_capacity_retains_timing_cause_without_consumption(self):\n'
assert text.count(method) == 1
assert text.count('        self.assertFalse(original.NATIVE_ADMISSION_RECEIPTS)') == 1
new = text.replace('import unittest\n', 'import unittest\nfrom copy import deepcopy\n', 1)
new = new.replace(method, method + '        native_receipts_before = deepcopy(original.NATIVE_ADMISSION_RECEIPTS)\n')
new = new.replace('        self.assertFalse(original.NATIVE_ADMISSION_RECEIPTS)',
                  '        self.assertEqual(original.NATIVE_ADMISSION_RECEIPTS, native_receipts_before)')
changed_method = method.strip().split('(')[0].split()[-1]
methods = lambda raw: {n.name: ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(raw))
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
before_methods, after_methods = methods(text), methods(new)
assert before_methods.keys() == after_methods.keys()
assert [k for k in before_methods if before_methods[k] != after_methods[k]] == [changed_method]
A.mkdir(); Q.mkdir()
for path in sorted(set(original['expected_payload_hashes']) | set(v['auxiliary_copies11'])):
    origin = parent.Q / path
    expected = original['expected_payload_hashes'].get(path, v['auxiliary_copies11'].get(path, {}).get('sha256'))
    raw = parent.pinned_bytes(origin, expected)
    destination = Q / path
    s.fs.safe_components(destination.parent, allow_missing=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    parent.write_bytes(destination, new.encode('utf-8') if path == name else raw)
parent.write_bytes(A / 'TEST-DIFF.patch', ''.join(difflib.unified_diff(
    text.splitlines(True), new.splitlines(True), fromfile='frozen/'+name, tofile='amended/'+name)).encode())
parent.write_bytes(A / 'STAGED.json', (json.dumps(dict(
    at=s.utc(), author='/root', original_manifest=parent.exact_ref(parent.Q/'TRANSFER-MANIFEST.json'),
    failed_launch=parent.exact_ref(P/'candidate-full-LAUNCH-RESULT.json'),
    failed_command=parent.exact_ref(P.parent/'js8-root-execution-20261015/candidate-full-COMMAND.json'),
    failed_raw=parent.exact_ref(P/'candidate-full/RAW.txt'),
    changed_path=name, before_sha256=s.digest(old), after_sha256=s.digest(new.encode()),
    all_other_methods_unchanged=True, changed_method=changed_method,
    candidate_root=str(Q), product_source_changes=0, all_2334_case_ids_retained=True,
    auxiliary_copies11={n:s.ordinary(Q/n) for n in v['auxiliary_copies11']},
    source_published=False, copy_LOC_credit=0), indent=2)+'\n').encode())
print(json.dumps({'staged': str(Q), 'test_after_sha256': s.digest(new.encode()), 'Source_published': False}))
