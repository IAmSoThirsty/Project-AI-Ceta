"""Claim or accept the exact reviewed two-file progress/continuity update."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import unittest

R = Path(__file__).resolve().parent
F, RUN = R.parents[2], 'ct3-20261014'
Q, OUT = F / '.agents' / RUN, R / 'active-application'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
now = lambda: datetime.now(timezone.utc).isoformat()
def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
def invoke(label, args):
    argv = ['powershell', '-NoProfile', '-File', r'T:\02-Config\agents\taar-orchestrate.ps1',
            *args, '--runtime-root', str(R)]
    started = now()
    done = subprocess.run(argv, capture_output=True)
    for suffix, data in (('stdout', done.stdout), ('stderr', done.stderr)):
        with (R / (label + '.' + suffix)).open('xb') as stream:
            stream.write(data)
    response = json.loads(done.stdout.decode('utf-8-sig'))
    save(R / (label + '.json'), {'argv': argv, 'started_at': started, 'finished_at': now(),
                               'exit_status': done.returncode, 'response': response})
    assert done.returncode == 0 and response['allowed'] is True, response

assert sys.flags.optimize == 0
assert Path(sys.executable) == F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'
mode = sys.argv[1]
assert mode in {'claim', 'complete'}
manifest_path = Q / 'TRANSFER-MANIFEST.json'
review_path = R / 'independent-review/review.json'
manifest, review, stored = read(manifest_path), read(review_path), read(R / RUN / 'receipts/review.json')
keys = {'schema_version', 'run_id', 'node_id', 'executor_id', 'started_at', 'finished_at',
        'input_hash', 'changed_files', 'result', 'commands', 'validations', 'exit_status', 'decision'}
assert set(review) == keys and set(stored) == keys | {'git_baseline', 'observed_git', 'receipt_hash'}
assert review['decision'] == 'approved' and type(review['exit_status']) is int and review['exit_status'] == 0
assert review['executor_id'] != '/root' and review['run_id'] == RUN and review['node_id'] == 'review'
assert json.dumps(review, sort_keys=True, separators=(',', ':'), allow_nan=False) == json.dumps(
    {key: stored[key] for key in keys}, sort_keys=True, separators=(',', ':'), allow_nan=False)
assert review['result']['manifest_sha256'] == sha(manifest_path)
helper = read(R / 'independent-review/publication-helper-review.json')
assert helper['decision'] == 'approved' and type(helper['exit_status']) is int and helper['exit_status'] == 0
assert helper['publication_script_sha256'] == sha(R / 'apply_reviewed_status.py')
assert helper['manifest_sha256'] == sha(manifest_path)
assert review['result']['integration_script_sha256'] == sha(Path(__file__))
assert set(manifest['application_paths']) == {'build/progress.json', 'handoff/continuity.json'}
assert len(manifest['payloads']) == 2
source_proof_path = F / manifest['source_suite']['repository_relative_path']
assert sha(source_proof_path) == manifest['source_suite']['sha256']
source = read(source_proof_path)['after_hashes']
assert len(source) == 286 and all(sha(F / relative) == value for relative, value in source.items())
if mode == 'claim':
    state = read(R / RUN / 'state.json')
    assert state['sequence'] == 9 and state['nodes']['review']['state'] == 'SUCCEEDED'
    assert read(R / RUN / 'claims.json') == {}
    for item in manifest['payloads']:
        assert sha(F / item['relative_path']) == item['active_before_sha256']
        assert sha(Q / item['relative_path']) == item['candidate_sha256']
    invoke('validate-claim', ['node', 'claim', RUN, 'validate', '--executor', '/root', '--workspace', str(Q)])
    invoke('validate-gate', ['node', 'run-gate', RUN, 'validate'])
    invoke('active-integrate-claim', ['node', 'claim', RUN, 'integrate', '--executor', '/root', '--workspace', str(F)])
    print(json.dumps({'integrate': 'RUNNING', 'input_hash': read(R / RUN / 'claims.json')['integrate']['input_hash']}), flush=True)
    sys.exit(0)

claim = read(R / RUN / 'claims.json')['integrate']
assert claim['executor_id'] == '/root' and claim['workspace'] == str(F)
journal = read(OUT / 'APPLIED.json')
assert journal['claim_input_hash'] == claim['input_hash'] and journal['manifest_sha256'] == sha(manifest_path)
assert {row['relative_path'] for row in journal['completed']} == set(manifest['application_paths'])
assert len(journal['completed']) == len(journal['before_images']) == 2
for item in manifest['payloads']:
    relative = item['relative_path']
    assert sha(F / relative) == sha(Q / relative) == item['candidate_sha256']
    backup, logical = OUT / 'native-backups' / (relative + '.original'), OUT / 'before' / (relative + '.source')
    before, after = read(logical), read(F / relative)
    assert sha(backup) == sha(logical) == item['active_before_sha256']
    original = next(row for row in journal['before_images'] if row['relative_path'] == relative)
    with backup.open('rb') as stream:
        facts = os.fstat(stream.fileno())
        assert hashlib.sha256(stream.read()).hexdigest() == original['sha256']
    assert (facts.st_dev, facts.st_ino, facts.st_mode, facts.st_size, facts.st_mtime_ns) == (
        original['device'], original['inode'], original['mode'], original['bytes'], original['mtime_ns'])
    assert all(after[key] == value for key, value in before.items() if key not in item['allowed_changed_keys'])
    assert after['repository_execution_history_20261014'][-1]['previous_current_observation'] == before['current_repository_execution_20261014']
    if relative == 'handoff/continuity.json':
        for key, value in after['historical_fields_before_ct3_20261014'].items():
            assert before[key] == value
        assert after['latest_source_tests']['passed'] == 1416 and after['latest_source_tests']['whole_product_acceptance'] is False
sys.path[:0] = [str(F / 'src'), str(F / 'tools'), str(F / 'tests/contract')]
sys.dont_write_bytecode = True
import build_measurements
actual_measurements = build_measurements.collect(F)
assert actual_measurements['implementation']['runtime_state'] == read(F / 'build/progress.json')['runtime_implementation']
assert actual_measurements['full_product'] == read(F / 'build/progress.json')['goal_state']
assert actual_measurements['conformance_verification']['installed_state'] == read(F / 'build/progress.json')['installed_qualification']
save(OUT / 'actual-register-measurements.json', actual_measurements)
suite = unittest.defaultTestLoader.loadTestsFromName('test_build_measurements')
def ids(item):
    if isinstance(item, unittest.TestSuite):
        for child in item:
            yield from ids(child)
    else:
        yield item.id()
expected, executed = list(ids(suite)), []
assert expected and len(expected) == len(set(expected))
class Result(unittest.TextTestResult):
    def startTest(self, test):
        executed.append(test.id()); super().startTest(test)
with (OUT / 'metadata-consumer-tests.txt').open('x', encoding='utf-8') as stream:
    tests = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
proof = {'recorded_at': now(), 'tests_run': tests.testsRun, 'expected_ids': expected, 'executed_ids': executed,
    'failures': len(tests.failures), 'errors': len(tests.errors), 'skips': len(tests.skipped),
    'raw_sha256': sha(OUT / 'metadata-consumer-tests.txt'), 'source_hashes_retained': 286,
    'test_scope': 'Three existing pure consumer unit cases; actual current repository input collection recorded separately',
    'actual_register_measurements_sha256': sha(OUT / 'actual-register-measurements.json'),
    'whole_product_acceptance': False, 'exit_status': 0 if tests.wasSuccessful() and not tests.skipped and executed == expected else 1}
save(OUT / 'metadata-consumer-tests.json', proof)
assert proof['exit_status'] == 0 and all(sha(F / relative) == value for relative, value in source.items())
destination = {'recorded_at': now(), 'source_root': str(F), 'manifest_sha256': sha(manifest_path),
    'review_sha256': sha(review_path), 'application_journal_sha256': sha(OUT / 'APPLIED.json'),
    'metadata_paths': 2, 'retained_source_payloads': 286, 'native_and_logical_originals': 2,
    'prior_observations_and_global_axes_preserved': True, 'metadata_consumer_tests': proof,
    'previous1416_Source_run_retained': manifest['source_suite'], 'runtime_code_changes': 0}
save(R / 'destination-verification.json', destination)
sys.path.insert(0, r'T:\01-Projects\TAAR-Agent-Taskforce\TAAR-Agent-Taskforce')
from taar.orchestration_runtime import _snapshot_workspace, _changed_files
from taar.orchestration_receipts import validate_receipt, load_receipt
print(json.dumps({'stage': 'actual_Source_snapshot', 'metadata_paths': 2, 'code_payloads_retained': 286}), flush=True)
changed = _changed_files(claim['baseline_snapshot'], _snapshot_workspace(F, Path('T:/')))
assert changed == sorted((F / relative).relative_to(Path('T:/')).as_posix() for relative in manifest['application_paths'])
receipt = {'schema_version': 1, 'run_id': RUN, 'node_id': 'integrate', 'executor_id': '/root',
    'started_at': journal['started_at'], 'finished_at': now(), 'input_hash': claim['input_hash'], 'changed_files': changed,
    'result': destination | {'destination_verification_sha256': sha(R / 'destination-verification.json')},
    'commands': [{'command': 'Reviewed native two-status-file replacement with exact original bytes/identities', 'exit_status': 0},
        {'command': 'Actual repository metadata collect(F), plus three existing consumer unit cases with unique IDs and zero skips', 'exit_status': 0},
        {'command': 'Installed Source snapshot delta equals precisely two approved metadata paths', 'exit_status': 0}],
    'validations': [{'name': name, 'passed': True} for name in ('prior_global_states_and_observations_retained',
        'exact_current_source_and_ledger_pointers', 'actual_two_path_destination_and_native_originals',
        'metadata_consumer_tests_and_source286_conservation')], 'exit_status': 0}
kwargs = {'run_id': RUN, 'node_id': 'integrate', 'executor_id': '/root', 'input_hash': claim['input_hash'],
    'claimed_at': claim['claimed_at'], 'node': read(R / RUN / 'graph.json')['graph']['nodes']['integrate']}
validate_receipt(receipt, **kwargs); save(R / 'integrate.json', receipt)
validate_receipt(load_receipt(R / 'integrate.json'), **kwargs)
invoke('active-integrate-complete', ['node', 'complete', RUN, 'integrate', str(R / 'integrate.json')])
state, claims = read(R / RUN / 'state.json'), read(R / RUN / 'claims.json')
assert state['sequence'] == 13 and claims == {} and all(row['state'] == 'SUCCEEDED' for row in state['nodes'].values())
save(R / 'actual-acceptance.json', {'recorded_at': now(), 'sequence': 13, 'claims': claims,
    'actual_states': {key: row['state'] for key, row in state['nodes'].items()},
    'integrate_receipt_sha256': sha(R / 'integrate.json'), 'metadata_paths': 2,
    'retained_source_payloads': 286, 'runtime_code_changes': 0, 'metadata_consumer_tests': tests.testsRun})
print(json.dumps({'all6': 'SUCCEEDED', 'sequence': 13, 'claims': claims, 'integrate_sha256': sha(R / 'integrate.json')}), flush=True)
