"""Run only the authored pure cohort with native/effect entrypoints forbidden."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import sys
import unittest

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
Q = F / '.agents/real-effect-entrypoint-20261020'
attempt = R / sys.argv[1]
attempt.mkdir(exist_ok=False)
sys.dont_write_bytecode = True
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
boundary_attempts = []

def audit(event, args):
    if event in ('ctypes.dlopen', 'subprocess.Popen', 'os.system',
                 'socket.bind', 'socket.connect', 'socket.getaddrinfo', 'sqlite3.connect'):
        boundary_attempts.append(event)
        raise RuntimeError('PURE_ENTRYPOINT_BOUNDARY_FORBIDDEN:' + event)

# Importing ctypes initializes the Python runtime's existing extension module;
# no application DLL is selected or loaded. Guard subsequent explicit loads.
import ctypes
sys.addaudithook(audit)
paths = [Q / name for name in (
    'src/ceta/composition/real_effect_cli.py', 'src/ceta/composition/real_effect_runtime.py',
    'src/ceta/composition/real_effect_service.py', 'src/ceta/composition/real_effect_host.py',
    'src/ceta/composition/real_effect_client.py', 'src/ceta/contracts/manual_effect.py',
    'src/ceta/composition/service_process.py',
    'src/ceta/contracts/local_ipc.py', 'src/ceta/contracts/local_results.py',
    'src/ceta/identity/windows_pipe.py', 'tests/contract/test_real_effect_entrypoint.py')]
before = {str(p.relative_to(Q)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
for path in paths:
    ast.parse(path.read_text('utf8'), filename=str(path))
suite = unittest.TestSuite()
for pattern in ('test_real_effect_entrypoint.py', 'test_local_ipc.py', 'test_local_results.py', 'test_boundaries.py'):
    suite.addTests(unittest.defaultTestLoader.discover(str(Q / 'tests/contract'),
        pattern=pattern, top_level_dir=str(Q / 'tests/contract')))
def ids(value):
    for case in value:
        if isinstance(case, unittest.TestSuite):
            yield from ids(case)
        else:
            yield case.id()
expected = list(ids(suite))
started = datetime.now(timezone.utc).isoformat()
with (attempt / 'tests.stderr').open('x', encoding='utf8') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
after = {str(p.relative_to(Q)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
value = dict(started_at=started, finished_at=datetime.now(timezone.utc).isoformat(),
    argv=sys.orig_argv, executable=sys.executable, base_executable=sys._base_executable,
    expected_ids=expected, tests_run=result.testsRun, passed=result.wasSuccessful(),
    failures=[(test.id(), text) for test,text in result.failures],
    errors=[(test.id(), text) for test,text in result.errors],
    skipped=[(test.id(), reason) for test,reason in result.skipped],
    boundary_attempts=boundary_attempts, payload_hashes=after, source_unchanged=before == after,
    scope='PURE_CONTROL_ONLY; NO ACTUAL HELLO/WORKER/APP/VFS/CPU EFFECT')
with (attempt / 'RESULT.json').open('x', encoding='utf8') as stream:
    json.dump(value, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(passed=value['passed'], tests_run=result.testsRun,
    expected=len(expected), boundary_attempts=boundary_attempts,
    failures=[t.id() for t,_ in result.failures], errors=[t.id() for t,_ in result.errors],
    source_unchanged=before == after)), flush=True)
sys.exit(0 if result.wasSuccessful() and not boundary_attempts and before == after else 1)
