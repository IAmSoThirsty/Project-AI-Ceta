"""Root's one-shot reviewed provisional publication and canonical full run."""
import json
import subprocess
import time
import uuid
import amendment_support as j

s = j.s
assert s.sha(j.R / 'AMENDMENT.json') == 'ad3091e4ac129d0efcecae70b45ff15d45d6dedcc0c52dc30efead3714929776'
assert s.sha(j.Q / 'TRANSFER-MANIFEST.json') == '2a3abde78bd4ab25af268ad1b16cef9eeaf9e2c30586c06fac4600876ba3c7c6'
review_path = j.F / '.agents/runtime/js8-publication-recovery-review-20261017/REVIEW-R2.json'
assert s.sha(review_path) == 'cc71f54a116bb57e6d6cd01d40f7a58611c856ef08f25815348b26526ff31b4e'
review = j.current_json(review_path)
assert review['decision'] == 'approved' and review['exit_status'] == 0
assert review['author'] == '/root/full_report_repair'
assert review['reviewer'] == '/root/publication_recovery_review'
assert review['amendment'] == j.exact_ref(j.R / 'AMENDMENT.json')
assert review['reviewed_scripts'] == j.scripts()
assert review['manifest_sha256'] == s.sha(j.Q / 'TRANSFER-MANIFEST.json')
v, m = j.verify(), j.manifest()
state = j.current_json(j.PARENT / j.RUN / 'state.json')
assert state['nodes']['validate']['state'] == 'RUNNING'
assert state['nodes']['validate']['claim']['executor_id'] == '/root'
assert not (j.R / 'SOURCE-PUBLICATION-PREFLIGHT.json').exists()
assert not (j.R / 'active-application').exists()
assert not (j.R / 'destination-full').exists()


def common(phase):
    return dict(schema_version=1, executor='/root', run_id=j.RUN, phase=phase,
        amendment=j.exact_ref(j.R / 'AMENDMENT.json'),
        manifest_sha256=s.sha(j.Q / 'TRANSFER-MANIFEST.json'),
        reviewed_scripts=j.scripts(), Source_publication=(phase == 'publish'), automatic_retry=False,
        all_conflicting_Source_pinned_runs_released=True,
        amendment_review=j.exact_ref(review_path), expected_ids_sha256=m['case_set']['sha256'],
        Source_before_map_sha256=m['Source_before_map_sha256'])


def execute(label, command, release_path=None):
    started = s.utc()
    print(json.dumps({'phase': label, 'command': command, 'cwd': str(j.F)}), flush=True)
    with (j.R / (label + '.stdout')).open('xb') as out, (j.R / (label + '.stderr')).open('xb') as err:
        result = subprocess.run(command, cwd=j.F, stdout=out, stderr=err)
    receipt = dict(command=command, cwd=str(j.F), started_at=started,
        finished_at=s.utc(), exit_status=result.returncode)
    if release_path is not None:
        receipt['release'] = j.exact_ref(release_path)
    s.write_new(j.R / (label + '-COMMAND.json'), receipt)
    if result.returncode:
        raise SystemExit(result.returncode)
    return {'command': subprocess.list2cmdline(command), 'exit_status': result.returncode}


release_path = j.R / 'releases/publication-preflight.json'
s.write_new(release_path, common('publication-preflight'))
pin = s.sha(release_path)
j.require_release(release_path, pin, 'publication-preflight')
preflight_command = [str(j.PY), '-B', '-X', 'utf8', str(j.R / 'publication_preflight.py'),
    '--release-path', str(release_path), '--release-sha256', pin]
commands = [execute('publication-preflight', preflight_command, release_path)]
commands.append(execute('publication-diff', ['git', '-C', str(j.parent.Q), 'diff', '--check']))
readiness_ref = j.exact_ref(j.R / 'SOURCE-PUBLICATION-PREFLIGHT.json')
readiness = j.require_candidate_readiness(readiness_ref)
original_author = s.AUTHOR
try:
    s.AUTHOR = '/root'
    s.complete('validate', {
        'manifest_sha256': s.sha(j.Q / 'TRANSFER-MANIFEST.json'),
        'qualification_kind': 'SOURCE_PUBLICATION_PREFLIGHT',
        'candidate_full_status': 'FAILED', 'final_acceptance': 'PENDING',
        'source_publication_preflight': readiness_ref,
        'prior_failed_candidate': readiness['prior_failed_candidate'],
        'reviewed_scripts': j.scripts(), 'amendment': j.exact_ref(j.R / 'AMENDMENT.json'),
        'Source_accepted': False,
    }, commands, [('exact_publication_preflight_and_graph_diff', True)])
finally:
    s.AUTHOR = original_author
j.require_validation(readiness_ref)
claim = s.claim('integrate', workspace=j.F, executor='/root')
release = common('publish')
release.update(candidate_readiness=readiness_ref,
    claim_input_hash=claim['input_hash'], claim_started_at=claim['claimed_at'],
    application_paths=m['application_paths'])
release_path = j.R / 'releases/publish.json'
s.write_new(release_path, release)
pin = s.sha(release_path)
j.require_release(release_path, pin, 'publish')
execute('publish', [str(j.PY), '-B', '-X', 'utf8', str(j.R / 'publish_source.py'),
    '--release-path', str(release_path), '--release-sha256', pin], release_path)
j.verify(source='after')
print(json.dumps({'published_paths': len(m['application_paths']),
    'application': j.exact_ref(j.R / 'active-application/APPLIED.json'),
    'Source_accepted': False, 'final_acceptance': 'PENDING'}), flush=True)

nonce = uuid.uuid4().hex
subject = j.native_case_subject('destination-full', nonce)
issued = time.time_ns()
native = dict(schema_version=1, kind='JS8_DISPOSABLE_NO_PROFILE_CASE_ROOT_RELEASE_V1', executor='/root',
    authority_basis='existing_user_authorized_disposable_acceptance_tests', run_id=j.RUN, run_nonce=nonce,
    issued_at_ns=issued, expires_at_ns=issued + 1_800_000_000_000, subject=subject,
    execute_exact_original_case=True, create_profiles=False, expected_denial_winerror=2)
native_path = j.R / 'releases/destination-full-native.json'
s.write_new(native_path, native)
s.write_new(j.R / 'NATIVE-EXPECTATION-BASIS.json', dict(
    executor='/root', at=s.utc(), release=j.exact_ref(native_path),
    expectation_evidence=j.exact_ref(j.F / '.agents/runtime/js8-denial-diagnosis-20261017/FINDINGS.json'),
    limits='Exact observed launch refusal, profile absence and custody only; missing-profile causality and positive isolation remain unproved.'))
release = common('destination-full')
release['native_case_release'] = j.exact_ref(native_path)
release_path = j.R / 'releases/destination-full.json'
s.write_new(release_path, release)
pin = s.sha(release_path)
j.require_release(release_path, pin, 'destination-full')
execute('destination-full', [str(j.PY), '-B', '-X', 'utf8', str(j.R / 'launch_full.py'),
    'destination-full', '--release-path', str(release_path), '--release-sha256', pin], release_path)
full_ref = j.exact_ref(j.R / 'destination-full/RESULT.json')
launch_ref = j.exact_ref(j.R / 'destination-full-LAUNCH-RESULT.json')
_, full = j.proof(full_ref)
_, launch = j.proof(launch_ref)
j.require_full(full, launch, 'destination-full', full_ref)
print(json.dumps({'destination_full': full_ref, 'destination_launch': launch_ref,
    'exit_status': 0, 'Source_accepted': False, 'independent_delivered_review': 'PENDING'}), flush=True)
