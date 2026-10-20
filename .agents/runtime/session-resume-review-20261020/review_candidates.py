"""Read-only JSON/digest/Git review; never runs preparation, tests or native code."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

F = Path(r'T:\00-Active\Project-AI-CETA')
R = F / '.agents/runtime/session-resume-20261020'
O = F / '.agents/runtime/session-resume-review-20261020'
EXPECTED = '0332bac7e3213c05bc59049979d06dbb7ef4dc02847fb475ff9839b712bb56c4'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def emit(name, value):
    with (O / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def difference(a, b, path=''):
    if type(a) is not type(b):
        return [{'path': path, 'before': a, 'candidate': b}]
    if isinstance(a, dict):
        rows = []
        for key in sorted(set(a) | set(b)):
            target = path + '/' + key
            if key not in a:
                rows.append({'path': target, 'operation': 'added', 'candidate': b[key]})
            elif key not in b:
                rows.append({'path': target, 'operation': 'removed', 'before': a[key]})
            else:
                rows += difference(a[key], b[key], target)
        return rows
    if isinstance(a, list):
        return [] if a == b else [{'path': path, 'before': a, 'candidate': b}]
    return [] if a == b else [{'path': path, 'before': a, 'candidate': b}]


assert sha(R / 'PREPARED.json') == EXPECTED
prepared = read(R / 'PREPARED.json')
all_pins = []
documents = {}
whitelist = {
    'build/progress.json': {'current_repository_execution_20261020', 'goal_state'},
    'handoff/continuity.json': {'first_next_action', 'next_action', 'resume_20261020', 'goal_status',
                              'real_implementation_blockers', 'active_workers'}}
for canonical, pins in prepared['paths'].items():
    original = F / canonical
    before = R / (original.name + '.before')
    candidate = F / pins['candidate']['repository_relative_path']
    assert sha(before) == pins['before']['sha256'] == sha(original)
    assert sha(candidate) == pins['candidate']['sha256']
    a, b = read(before), read(candidate)
    changed = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
    assert changed <= whitelist[canonical]
    unchanged_keys = sorted((set(a) | set(b)) - changed)
    protected = {k: a[k] for k in a if any(w in k.lower() for w in ('halt', 'checkpoint', 'histor', 'accept', 'js8'))}
    preserved = {k: a[k] == b.get(k) for k in protected if k not in whitelist[canonical]}
    assert all(preserved.values())
    documents[canonical] = {'original_sha256': sha(original), 'before_sha256': sha(before),
        'candidate_sha256': sha(candidate), 'changed_top_level_fields': sorted(changed),
        'unchanged_top_level_fields': unchanged_keys, 'protected_historical_fields': protected,
        'protected_fields_preserved': preserved, 'diff': difference(a, b)}
    all_pins += [{'path': str(p), 'sha256': sha(p)} for p in (original, before, candidate)]
progress = read(R / 'progress.json.candidate')
continuity = read(R / 'continuity.json.candidate')
observation = progress['current_repository_execution_20261020']
assert observation == continuity['resume_20261020']
git = ['git', '-c', 'safe.directory=T:/00-Active/Project-AI-CETA', '-C', str(F)]
head = subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip()
branch = subprocess.check_output([*git, 'branch', '--show-current'], text=True).strip()
assert observation['Git_HEAD'] == head and observation['branch'] == branch
references = []


def refs(value):
    if isinstance(value, dict):
        if set(('repository_relative_path', 'sha256')) <= set(value):
            p = F / value['repository_relative_path']
            assert p.resolve().is_relative_to(F.resolve())
            actual = sha(p)
            assert actual == value['sha256']
            references.append({'path': str(p), 'sha256': actual})
        for v in value.values():
            refs(v)
    elif isinstance(value, list):
        for v in value:
            refs(v)


refs(observation)
assert observation['accepted_source_baseline']['sha256'] == '5d001e3144805864048edf165e7124fdba21f8d99fc01b36e1f7463877b68bb0'
assert observation['private_joined_candidate']['sha256'] == '212f1913af6ef24c24041628d2dcca23c7b754849ba79de9db8d75a210b3f532'
assert observation['joined_candidate_source_published'] is False
assert observation['joined_native_full_destination_acceptance'] == 'PENDING'
assert observation['full_product_complete'] is False
js9 = read(F / observation['joined_controlled_tests']['repository_relative_path'])
js9_review = read(F / observation['joined_source_review']['repository_relative_path'])
assert js9['tests_run'] == 45 and js9['passed'] is True and js9['native_execution'] is False
assert not js9['failures'] and not js9['skipped'] and not js9['unexpected_successes'] and js9['exception'] is None
assert js9_review['full_application_or_destination_acceptance'] is False
ac7 = read(F / observation['AC7']['result']['repository_relative_path'])
ac7_review = read(F / observation['AC7']['independent_result_review']['repository_relative_path'])
diag = read(F / observation['AC7']['startup_diagnosis']['repository_relative_path'])
assert ac7['positive_isolation_qualified'] is False and ac7['all_captured_resources_retired'] is True
assert ac7['profile_cleanup_status'] == observation['AC7']['recorded_own_profile_cleanup']
assert ac7_review['decision'] == 'approved_as_failed_attempt_and_recorded_cleanup_evidence'
assert ac7_review['retry_approved'] is False and ac7_review['fresh_current_host_inspection_performed'] is False
assert observation['AC7']['attempt_authorization'] == 'CONSUMED' and observation['AC7']['retry_authorized'] is False
assert observation['AC7']['qualification'] == 'FAILED' and observation['AC7']['failing_DLL'] == diag['failed_dll'] == 'UNKNOWN'
assert observation['AC7']['worker_exit_status'] == ac7_review['recorded_worker_exit_hex'] == '0xC0000142'
prepare_source = R / 'prepare_status.py'
ast.parse(prepare_source.read_text(encoding='utf-8-sig'))
all_pins += references + [{'path': str(R / 'PREPARED.json'), 'sha256': EXPECTED},
                          {'path': str(prepare_source), 'sha256': sha(prepare_source)}]
for row in all_pins:
    assert sha(Path(row['path'])) == row['sha256']
emit('CHECKS.json', {'prepared_sha256': EXPECTED, 'author': prepared['author'], 'reviewer': '/root/ac7_native_artifact_review20',
    'scope': 'Two document metadata candidates; file/JSON/AST/Git checks only', 'documents': documents,
    'reference_pins': references, 'all_input_pins': all_pins, 'git': {'head': head, 'branch': branch},
    'duplicate_observation_equal': True, 'js9_45_controlled_cases': True, 'native_test_reruns': False,
    'product_completion_asserted': False, 'tracked_originals_unchanged': True,
    'ac7_review_scope': 'Recorded captured owned-resource retirement and own-profile cleanup; no current host-wide witness',
    'ac7_failure_and_unknown_preserved': True, 'input_drift': 0})
print(json.dumps({'changed_fields': {k: v['changed_top_level_fields'] for k, v in documents.items()},
    'references_matched': len(references), 'tracked_originals_unchanged': True,
    'head': head, 'branch': branch, 'input_drift': 0}, indent=2))
