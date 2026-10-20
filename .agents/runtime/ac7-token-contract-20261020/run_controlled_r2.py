"""Pure AC7 parent-token checks; native/process/network/database calls denied."""
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
import ctypes
import hashlib
import json
import sys
import unittest

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/ac7-token-contract-20261020'
now = lambda: datetime.now(timezone.utc).isoformat()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def save(path, value):
    with path.open('x', encoding='utf8') as stream: json.dump(value, stream, indent=2)
inputs = json.loads((R / 'INPUTS.json').read_bytes())
assert all(sha(F / n) == h for n,h in inputs['payload_hashes'].items())
changed = [n for n,h in inputs['payload_hashes'].items() if sha(Q / n) != h]
candidate_before = {n: sha(Q / n) for n in inputs['payload_hashes']}
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
blocked = []
def deny(*args, **kwargs):
    blocked.append('native_library_load')
    raise AssertionError('Native API loading excluded from controlled token tests')
def audit(event, args):
    if event in {'subprocess.Popen', 'socket.bind', 'socket.connect', 'sqlite3.connect'}:
        blocked.append(event)
        raise AssertionError('Controlled test attempted an excluded operation: ' + event)
sys.addaudithook(audit)
started = now()
with patch.object(ctypes, 'WinDLL', deny):
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        'test_isolated_worker.IsolationFactsContractTests',
        'test_isolation_token_diagnostics.IsolationTokenDiagnosticTests',
        'test_isolation_qualification_oracle.IsolationQualificationOracleTests',
    ])
    count = suite.countTestCases()
    with (R / 'CONTROLLED-PARENT-ORACLE-R2.txt').open('x', encoding='utf8') as output:
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
checks = dict(Source352_unchanged=all(sha(F / n) == h for n,h in inputs['payload_hashes'].items()),
    candidate_unchanged=all(sha(Q / n) == h for n,h in candidate_before.items()), no_excluded_calls=not blocked)
success = result.wasSuccessful() and result.testsRun == count and not result.skipped and all(checks.values())
save(R / 'CONTROLLED-PARENT-ORACLE-R2.json', dict(started_at=started, finished_at=now(),
    command=[sys.executable, '-B', '-X', 'utf8', str(Path(__file__))], tests=result.testsRun,
    failures=len(result.failures), errors=len(result.errors), skips=len(result.skipped),
    checks=checks, changed_candidate_paths=changed, blocked_calls=blocked,
    raw_sha256=sha(R / 'CONTROLLED-PARENT-ORACLE-R2.txt'), success=success,
    qualification='CONTROLLED_VALUES_ONLY_NO_NATIVE_ISOLATION_CLAIM'))
print(json.dumps(dict(success=success, tests=result.testsRun, failures=len(result.failures), errors=len(result.errors))), flush=True)
sys.exit(0 if success else 1)
