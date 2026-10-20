"""Issue one reviewed engineering release, preserving exact user effect limits."""
from pathlib import Path
import argparse
import hashlib
import importlib
import json
import sys
import time
import uuid
import phase_coordinator as c

F, R, D, Q = c.F, c.R, c.D, c.Q
OLD = F / '.agents/runtime/js9-runtime-20261020/successor-r2'
OLD_AUTH = F / '.agents/runtime/js9-root-execution-20261020/NO-PROFILE-AUTHORIZATION.json'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
ref = lambda path: dict(repository_relative_path=path.relative_to(F).as_posix(), sha256=sha(path))


def unchanged_authorized_operation():
    assert sha(OLD_AUTH) == '2de12485ef5fa2b204a1c5648667b2446105aebf16378238379455f6799ec2b0'
    old_proof = json.loads((OLD / 'candidate-full/NATIVE-CASE-PROOF.json').read_bytes())
    assert not old_proof['entered'] and not old_proof['attempted']
    assert all(not old_proof[key] for key in ('exact_native_calls', 'handles', 'sockets', 'profile_folder_observations'))
    old_packet = json.loads((OLD / 'PACKET.json').read_bytes())
    packet = c.bound_packet()
    assert packet['original_case_id'] == old_packet['original_case_id']
    assert packet['fixture_dependencies'] == old_packet['fixture_dependencies']
    for name in ('fixture_runtime.py', 'bounded_custody.py', 'resource_observer.py'):
        assert sha(D / name) == old_packet['scripts'][name]
    old_gate = (OLD / 'native_case_gate.py').read_text(encoding='utf-8')
    exact_rebinding = old_gate.replace('.agents/runtime/js9-runtime-20261020/successor-r2',
        '.agents/runtime/js9-runtime-20261020/successor-r3')
    exact_rebinding = exact_rebinding.replace("F/'.agents/js9-runtime-20261020'", "F/'.agents/js9-runtime-r5-20261020'")
    exact_rebinding = exact_rebinding.replace("F / '.agents/js9-runtime-20261020'", "F / '.agents/js9-runtime-r5-20261020'")
    assert (D / 'native_case_gate.py').read_text(encoding='utf-8') == exact_rebinding
    original = 'tests/contract/test_isolated_worker.py'
    assert (Q / original).read_bytes() == (F / '.agents/js9-runtime-20261020' / original).read_bytes()
    return dict(original_operator_authorization=ref(OLD_AUTH), predecessor_packet=ref(OLD / 'PACKET.json'),
        successor_packet=ref(D / 'PACKET.json'), failed_preflight_proof=ref(OLD / 'candidate-full/NATIVE-CASE-PROOF.json'),
        original_operation_unchanged=True, prior_no_profile_attempts=0,
        exact_phase_limits=dict(candidate_full=1, destination_full=1),
        repair='Same-project dependency closure and diagnostic repair; native gate path rebinding only',
        new_human_authorization_fabricated=False, automatic_retry=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('native-store', 'native-observer', 'candidate-full', 'destination-full', 'publish'))
    parser.add_argument('--review-path', type=Path, required=True)
    parser.add_argument('--review-sha256', required=True)
    args = parser.parse_args()
    packet = c.bound_packet()
    assert sha(args.review_path) == args.review_sha256
    review = json.loads(args.review_path.read_bytes())
    assert review['decision'] == 'approved' and review['exit_status'] == 0
    assert review['packet'] == ref(D / 'PACKET.json') and review['reviewed_scripts'] == packet['scripts']
    assert review['candidate_manifest'] == packet['candidate_manifest']
    assert review['author'] == packet['author'] and review['reviewer'] not in (packet['author'], '/root')
    node = 'integrate' if args.phase in ('publish', 'destination-full') else 'implement'
    state_path = R / c.RUN / 'state.json'
    claims_path = R / c.RUN / 'claims.json'
    state = json.loads(state_path.read_bytes())
    claims = json.loads(claims_path.read_bytes())
    current = claims[node]
    assert state['nodes'][node]['state'] == 'RUNNING' and current['executor_id'] == '/root'
    assert Path(current['workspace']) == (F if node == 'integrate' else D)
    assert current['input_hash'] == state['nodes'][node]['claim']['input_hash']
    if node == 'integrate':
        assert claims['destination_evidence']['executor_id'] == '/root'
        assert Path(claims['destination_evidence']['workspace']) == D
        assert state['nodes']['destination_evidence']['state'] == 'RUNNING'
    sys.path.insert(0, str(D))
    import js9_support as j
    j.verify(source='after' if args.phase == 'destination-full' else 'before')
    issued = time.time_ns()
    release = dict(schema_version=1, executor='/root', run_id=packet['run_id'], phase=args.phase,
        packet=ref(D / 'PACKET.json'), candidate_manifest=packet['candidate_manifest'],
        reviewed_scripts=packet['scripts'], case_set=packet['case_set'], Source_before=packet['Source_before'],
        automatic_retry=False, create_profiles=False, Source_publication=args.phase == 'publish',
        all_conflicting_Source_pinned_runs_released=True, issued_at_ns=issued,
        expires_at_ns=issued + 1_800_000_000_000, independent_review=ref(args.review_path),
        execution_lease=dict(claims=ref(claims_path), state=ref(state_path), node_id=node, input_hash=current['input_hash']))
    frozen = R / ('lease-observation-' + args.phase)
    frozen.mkdir(exist_ok=False)
    for path in (claims_path, state_path):
        with (frozen / path.name).open('xb') as stream:
            raw = path.read_bytes()
            assert stream.write(raw) == len(raw)
    release['historical_lease_observation'] = dict(claims=ref(frozen / 'claims.json'), state=ref(frozen / 'state.json'))
    directory = D / 'releases'
    directory.mkdir(exist_ok=True)
    if args.phase in ('candidate-full', 'destination-full', 'publish'):
        for field, phase, label in (('native_store_corroboration', 'native-store', 'native_store_r3'),
                ('native_observer_corroboration', 'native-observer', 'native_observer_r3')):
            release[field] = ref(D / (label + '-CORROBORATION.json'))
            j.require_native_corroboration(release[field], phase)
    if args.phase in ('candidate-full', 'destination-full'):
        required = ('candidate_fixtures', 'candidate_cache') if args.phase == 'candidate-full' else ('destination_fixtures',)
        assert all(name in claims and claims[name]['executor_id'] == '/root'
            and state['nodes'][name]['state'] == 'RUNNING' for name in required)
        assert not (D / args.phase).exists() and not (D / (args.phase + '-LAUNCH-ATTEMPT.json')).exists()
        continuity = unchanged_authorized_operation()
        continuity_path = R / ('AUTHORIZATION-CONTINUITY-' + args.phase + '.json')
        c.save(continuity_path, continuity)
        gate = importlib.import_module('native_case_gate')
        nonce = uuid.uuid4().hex
        subject = j.native_case_subject(args.phase, nonce)
        native_case = dict(schema_version=1, kind=gate.KIND, executor='/root', authority_basis=gate.AUTHORITY,
            run_id=gate.RUN, run_nonce=nonce, issued_at_ns=issued, expires_at_ns=issued + 1_800_000_000_000,
            subject=subject, execute_exact_original_case=True, create_profiles=False, expected_denial_winerror=2)
        raw = (json.dumps(native_case, indent=2, allow_nan=False) + '\n').encode()
        gate.validate_release(raw, hashlib.sha256(raw).hexdigest(), subject, time.time_ns())
        case_path = directory / ('native-case-' + args.phase + '.json')
        with case_path.open('xb') as stream:
            assert stream.write(raw) == len(raw)
        release.update(native_case_release=ref(case_path), operator_authorization=ref(OLD_AUTH),
            operation_equivalence=ref(continuity_path))
    if args.phase == 'publish':
        release['candidate_full'] = ref(D / 'candidate-full/RESULT.json')
        release['candidate_full_launch'] = ref(D / 'candidate-full-LAUNCH-RESULT.json')
        j.require_full_result(release['candidate_full'], release['candidate_full_launch'], 'candidate-full')
        release['source_lease'] = dict(release['execution_lease'], run_id=c.RUN, claimed_at=current['claimed_at'])
    path = directory / (args.phase + '-r3.json')
    c.save(path, release)
    j.require_release(path, sha(path), args.phase)
    c.save(R / (args.phase + '-RELEASE.json'), dict(phase=args.phase, release=ref(path)))
    print(json.dumps(dict(phase=args.phase, release=ref(path))), flush=True)


if __name__ == '__main__':
    main()
