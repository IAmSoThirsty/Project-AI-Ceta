"""Execute the isolated controlled producer/provenance cohort with effect audit."""
from datetime import datetime, timezone
from pathlib import Path
import ctypes
import hashlib
import json
import os
import sys
import threading
import unittest

F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/cpu-outcome-provenance-20261017'
R = Path(__file__).resolve().parent
label = sys.argv[1]
assert label.isidentifier()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def utc(): return datetime.now(timezone.utc).isoformat()
inputs = json.loads((R / 'INPUTS.json').read_bytes())
for name, row in inputs['payloads'].items():
    assert sha(row['path']) == row['sha256'] and sha(Q / name) == row['sha256'], name
new_paths = ('src/ceta/identity/native_cpu_outcome.py', 'src/ceta/composition/native_cpu_outcome.py',
             'tests/contract/test_native_cpu_outcome_provenance.py')
before = {name: sha(Q / name) for name in new_paths}
events = []
def audit(event, args):
    if event in ('ctypes.dlopen', 'subprocess.Popen', 'os.system', 'sqlite3.connect',
                 'os.startfile', 'os.startfile/2', 'socket.connect', 'socket.bind'):
        events.append(event); raise AssertionError('CONTROLLED_COHORT_FORBIDS_' + event)
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        flags = args[2]
        if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            assert Path(os.fsdecode(args[0])).resolve().is_relative_to(R), 'WRITE_OUTSIDE_EVIDENCE'
sys.addaudithook(audit)
sys.path[:0] = [str(Q / 'src'), str(Q / 'tests/contract')]
import test_native_cpu_outcome_provenance as tests
suite = unittest.defaultTestLoader.loadTestsFromTestCase(tests.CpuOutcomeProvenanceTests)
ids = [case.id() for case in suite]
executed, completed = [], []
class Recorded(unittest.TextTestResult):
    def startTest(self, case): executed.append(case.id()); super().startTest(case)
    def stopTest(self, case): completed.append(case.id()); super().stopTest(case)
started = utc(); threads = {thread.ident for thread in threading.enumerate()}
with (R / (label + '.txt')).open('x', encoding='utf8') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorded).run(suite)
after = {name: sha(Q / name) for name in new_paths}
imports = {}
for name, module in tuple(sys.modules.items()):
    if name == 'ceta' or name.startswith('ceta.'):
        file = getattr(module, '__file__', None)
        if file:
            path = Path(file).resolve(); assert path.is_relative_to(Q / 'src')
            imports[name] = dict(path=str(path), sha256=sha(path))
receipt = dict(author='/root/publication_recovery_review', started_at=started, finished_at=utc(),
    mode='CONTROLLED_NO_NATIVE_NO_SQL', command=[sys.executable, '-B', '-X', 'utf8', *sys.argv],
    runner_sha256=sha(__file__), interpreter_sha256=sha(sys.executable), cwd=str(Path.cwd()),
    before=before, after=after, imports=imports, expected_ids=ids, executed_ids=executed, completed_ids=completed,
    tests_run=result.testsRun, failures=[(case.id(), trace) for case, trace in result.failures],
    errors=[(case.id(), trace) for case, trace in result.errors], skips=[(case.id(), reason) for case, reason in result.skipped],
    forbidden_events=events, callback_elapsed_ns=tests.TIMINGS,
    new_threads_remaining=[thread.name for thread in threading.enumerate() if thread.ident not in threads],
    raw_sha256=sha(R / (label + '.txt')), passed=result.wasSuccessful(),
    native_cases_executed=0, SQL_connections_opened=0, Source_publication=False,
    limitations=['Controlled native observation, admitted lease state, dispatch and canonical write; actual integration remains pending.',
                 'No post-retainer-exit recovery entry or public composition qualification.'])
with (R / (label + '.json')).open('x', encoding='utf8') as stream:
    json.dump(receipt, stream, indent=2, allow_nan=False); stream.write('\n')
assert before == after and ids == executed == completed and not events and not receipt['new_threads_remaining']
assert all(sha(Q / name) == row['sha256'] for name, row in inputs['payloads'].items())
print(json.dumps(dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
    skips=len(result.skipped), receipt=str(R / (label + '.json')))))
sys.exit(0 if result.wasSuccessful() else 1)
