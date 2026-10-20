"""Prepare two provenance-preserving continuity candidates; never publish them."""
from datetime import datetime, timezone
from pathlib import Path
import copy
import hashlib
import json
import subprocess

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, raw):
    with path.open('xb') as stream:
        if stream.write(raw) != len(raw):
            raise RuntimeError('SHORT_STATUS_WRITE')


def ref(name):
    path = F / name
    return dict(repository_relative_path=name, sha256=digest(path.read_bytes()))


def main():
    stamp = datetime.now(timezone.utc).isoformat()
    originals = {}
    candidates = {}
    for name in ('build/progress.json', 'handoff/continuity.json'):
        path = F / name
        before = path.read_bytes()
        originals[name] = dict(sha256=digest(before), bytes=len(before))
        write_new(R / (path.name + '.before'), before)
        candidates[name] = json.loads(before.decode('utf-8-sig'))

    ac7_name = '.agents/runtime/ac7-token-contract-20261020/q-6be3c32cb832461093c6d15dc9c538f8/RESULT.json'
    ac7 = json.loads((F / ac7_name).read_bytes())
    assert ac7['positive_isolation_qualified'] is False
    assert ac7['all_captured_resources_retired'] is True
    assert ac7['profile_cleanup_status'] == 'DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED'
    assert ac7['Source352_native_and_hash_conserved'] is True
    source = ref('.agents/runtime/js8-20261015/amendment-report1/ACCEPTED-SOURCE-BASELINE.json')
    assert source['sha256'] == '5d001e3144805864048edf165e7124fdba21f8d99fc01b36e1f7463877b68bb0'
    joined = ref('.agents/runtime/js9-runtime-20261020/MANIFEST-R4.json')
    assert joined['sha256'] == '212f1913af6ef24c24041628d2dcca23c7b754849ba79de9db8d75a210b3f532'
    observation = dict(
        recorded_at=stamp, state='RESUMED_IMPLEMENTATION_AND_TESTS',
        authoritative_repository=str(F), display_identity='Project-AI: CETA',
        Git_HEAD=subprocess.check_output(['git', '-C', str(F), 'rev-parse', 'HEAD']).decode().strip(),
        branch=subprocess.check_output(['git', '-C', str(F), 'branch', '--show-current']).decode().strip(),
        accepted_source_baseline=source,
        private_joined_candidate=joined,
        joined_source_review=ref('.agents/runtime/js9-composition-review-20261020/R3/DISPOSITION.json'),
        joined_controlled_tests=ref('.agents/runtime/js9-runtime-20261020/controlled_r3/RESULT.json'),
        joined_candidate_source_published=False,
        joined_native_full_destination_acceptance='PENDING',
        AC7=dict(result=ref(ac7_name),
            independent_result_review=ref('.agents/runtime/ac7-result-review-20261020/review.json'),
            startup_diagnosis=ref('.agents/runtime/ac7-startup-diagnosis-20261020/HANDOFF-DISPOSITION.json'),
            attempt_authorization='CONSUMED', qualification='FAILED',
            worker_exit_status='0xC0000142', failing_DLL='UNKNOWN',
            recorded_process_retirement=True,
            recorded_own_profile_cleanup=ac7['profile_cleanup_status'],
            retry_authorized=False),
        scope_frozen=True, full_product_complete=False,
        remaining_requirements=[
            'Joined candidate native and complete integration verification, canonical publication and destination acceptance',
            'Positive restricted-worker qualification after concrete failure attribution and separately authorized successor',
            'Genuine owner approval and canonical public authorization-to-effect execution',
            'Production request compiler, actual model/runtime integration and remaining full-product acceptance'
        ])
    first = ('Finish the reviewed JS9 native/full execution tools, perform authorized verification, '
             'publish the exact changed/new paths into the canonical application and verify at the destination. '
             'The consumed AC7 grant supplies no retry or post-cleanup regression authority. '
             'Preserve Source352 acceptance until a qualified successor is accepted.')
    continuity = candidates['handoff/continuity.json']
    continuity['first_next_action'] = first
    continuity['next_action'] = first
    continuity['resume_20261020'] = copy.deepcopy(observation)
    continuity['goal_status'] = 'ACTIVE_NOT_COMPLETE'
    continuity['real_implementation_blockers'] = ' '.join(observation['remaining_requirements'])
    continuity['active_workers'] = [
        dict(agent='/root/recovery_regression20', job='JS9 execution tool repair and preparation'),
        dict(agent='/root/recovery_join_review20', job='Independent JS9 execution tool review'),
        dict(agent='/root/ac7_native_artifact_review20', job='Read-only loader diagnostic capability inventory')
    ]
    progress = candidates['build/progress.json']
    progress['current_repository_execution_20261020'] = copy.deepcopy(observation)
    progress['goal_state'] = 'ACTIVE_NOT_COMPLETE'
    rows = {}
    for name, value in candidates.items():
        raw = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
        target = R / (Path(name).name + '.candidate')
        write_new(target, raw)
        rows[name] = dict(before=originals[name], candidate=ref(target.relative_to(F).as_posix()))
    report = dict(at=stamp, author='/root', scope='TWO_STATUS_DOCUMENTS_ONLY', paths=rows,
        historical_checkpoint_preserved=True, canonical_writes_performed=False,
        review_required=True, source_acceptance_promoted=False)
    write_new(R / 'PREPARED.json', (json.dumps(report, indent=2) + '\n').encode())
    print(json.dumps(dict(prepared=ref((R / 'PREPARED.json').relative_to(F).as_posix()), canonical_writes=False)))


if __name__ == '__main__':
    main()
