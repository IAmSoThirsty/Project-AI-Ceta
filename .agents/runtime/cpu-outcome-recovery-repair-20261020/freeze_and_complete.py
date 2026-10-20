"""Freeze the narrow registration repair and retain its actual test receipt."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json
import os
import subprocess
import sys

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/cpu-outcome-recovery-r4-20261020'
OLD = F / '.agents/cpu-outcome-recovery-20261017'
RUN = 'cpu-outcome-recovery-r4-20261020'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()

def save(p, v):
    with p.open('x', encoding='utf8') as s:
        json.dump(v, s, indent=2)

inputs = json.loads((R / 'INPUTS.json').read_bytes())
source = 'src/ceta/kernel/cpu_execution.py'
test = 'tests/contract/test_cpu_recovery_registration.py'
pins = {n: sha(Q / n) for n in sorted(set(inputs['payload_hashes']) | {test})}
assert len(pins) == 375
assert [n for n in inputs['payload_hashes'] if pins[n] != inputs['payload_hashes'][n]] == [source]
before, after = (OLD / source).read_text(), (Q / source).read_text()
old_tree, new_tree = ast.parse(before), ast.parse(after)
old_class = next(n for n in old_tree.body if isinstance(n, ast.ClassDef) and n.name == '_CpuExecutionCoordinator')
new_class = next(n for n in new_tree.body if isinstance(n, ast.ClassDef) and n.name == '_CpuExecutionCoordinator')
old_methods = {n.name: ast.dump(n, include_attributes=False) for n in old_class.body if isinstance(n, ast.FunctionDef)}
new_methods = {n.name: ast.dump(n, include_attributes=False) for n in new_class.body if isinstance(n, ast.FunctionDef)}
assert set(old_methods) == set(new_methods)
assert [n for n in old_methods if old_methods[n] != new_methods[n]] == ['claim_recovery_liveness']
for tree in (old_tree, new_tree):
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == '_CpuExecutionCoordinator')
    cls.body = [n for n in cls.body if not (isinstance(n, ast.FunctionDef) and n.name == 'claim_recovery_liveness')]
assert ast.dump(old_tree, include_attributes=False) == ast.dump(new_tree, include_attributes=False)
delta = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='cut-r3/' + source, tofile='cut-r4/' + source))
with (R / 'REGISTRATION-REPAIR.diff').open('x', encoding='utf8') as s:
    s.write(delta)
code = 'import sys,unittest;sys.path[:0]=' + repr([str(Q / 'src'), str(Q / 'tests/contract')]) + ';s=unittest.defaultTestLoader.loadTestsFromName("test_cpu_recovery_registration");assert s.countTestCases()==8;r=unittest.TextTestRunner(verbosity=2).run(s);sys.exit(not r.wasSuccessful())'
command = [sys.executable, '-B', '-X', 'utf8', '-c', code]
start = now()
done = subprocess.run(command, cwd=F, capture_output=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
for suffix, raw in [('stdout', done.stdout), ('stderr', done.stderr)]:
    with (R / ('targeted8.' + suffix)).open('xb') as s:
        s.write(raw)
save(R / 'TARGETED-RESULT.json', dict(started_at=start, finished_at=now(), command=command, exit_status=done.returncode,
     tests=8, stdout_sha256=sha(R / 'targeted8.stdout'), stderr_sha256=sha(R / 'targeted8.stderr'),
     fixture_kind='Actual method with controlled typed coordinator/lease and publication maps; no SQLite/native operations'))
assert done.returncode == 0
assert all(sha(Q / n) == pin for n, pin in pins.items())
baseline = json.loads((F / '.agents/runtime/js8-20261015/amendment-report1/ACCEPTED-SOURCE-BASELINE.json').read_bytes())
assert all(sha(F / n) == pin for n, pin in baseline['effective_payload_hashes'].items())
save(R / 'MANIFEST.json', dict(at=now(), candidate=str(Q), base=inputs['base_manifest'], payload_hashes=pins,
     authored_changes=[source, test], isolated_changed_method='claim_recovery_liveness', source_publication=False,
     copied_source_LOC_credit=0, targeted_result_sha256=sha(R / 'TARGETED-RESULT.json'),
     affected_full_regression='PENDING_177_CASE_SUCCESSOR', independent_review='PENDING'))
claim = inputs['claim']
receipt = R / 'implement-receipt.json'
save(receipt, dict(schema_version=1, run_id=RUN, node_id='implement', executor_id='/root', started_at=claim['claimed_at'],
     finished_at=now(), input_hash=claim['input_hash'], changed_files=[(Q / n).relative_to(Path('T:/')).as_posix() for n in pins],
     result=dict(manifest=str(R / 'MANIFEST.json'), manifest_sha256=sha(R / 'MANIFEST.json'), finding='RJR20-01',
                 targeted_tests=8, Source_publication=False, full_regression_and_independent_acceptance='PENDING'),
     commands=[dict(argv=command, exit_status=done.returncode)],
     validations=[dict(name='8_registration_success_failure_custody_tests', passed=True),
                  dict(name='all_other_production_method_ASTs_and_374_parent_payloads_preserved_except_named_method', passed=True)], exit_status=0))
command = ['powershell', '-NoProfile', '-File', 'T:/02-Config/agents/taar-orchestrate.ps1', 'node', 'complete', RUN, 'implement', str(receipt), '--runtime-root', str(R)]
done = subprocess.run(command, cwd=F, capture_output=True)
for suffix, raw in [('stdout', done.stdout), ('stderr', done.stderr)]:
    with (R / ('implement-complete.' + suffix)).open('xb') as s:
        s.write(raw)
response = json.loads(done.stdout.decode('utf-8-sig'))
save(R / 'implement-complete.json', dict(command=command, exit_status=done.returncode, response=response))
assert done.returncode == 0 and response['allowed'] is True, response
print(json.dumps(dict(manifest=str(R / 'MANIFEST.json'), sha256=sha(R / 'MANIFEST.json'), targeted_tests=8, Source_published=False)), flush=True)
