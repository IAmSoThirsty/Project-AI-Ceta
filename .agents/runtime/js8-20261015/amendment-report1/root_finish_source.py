"""Root-only one-attempt completion; every prerequisite must already exist."""
from pathlib import Path
import json
import subprocess
import amendment_support as j


def run_completion(command, root, receipt_root, release_reference, write_new, utc):
    """Record the attempt before spawn and retain the primary failure on cleanup."""
    started = utc()
    attempt = dict(command=command, cwd=str(root), started_at=started,
                   release=release_reference, automatic_retry=False)
    write_new(receipt_root / 'complete-ATTEMPT.json', attempt)
    print(json.dumps(dict(phase='complete', **attempt)), flush=True)
    streams = []
    result = None
    primary = None
    primary_traceback = None
    secondary = []
    try:
        out = (receipt_root / 'complete.stdout').open('xb')
        streams.append(out)
        err = (receipt_root / 'complete.stderr').open('xb')
        streams.append(err)
        result = subprocess.run(command, cwd=root, stdout=out, stderr=err)
    except BaseException as error:
        primary, primary_traceback = error, BaseException.__dict__['__traceback__'].__get__(error)
    finally:
        for stream in reversed(streams):
            try:
                stream.close()
            except BaseException as error:
                if primary is None:
                    primary, primary_traceback = error, BaseException.__dict__['__traceback__'].__get__(error)
                else:
                    secondary.append(error)
    terminal = dict(**attempt, finished_at=utc(),
                    child_returned=result is not None,
                    exit_status=result.returncode if result is not None else None,
                    primary_error_type=type(primary).__name__ if primary is not None else None,
                    cleanup_error_types=[type(error).__name__ for error in secondary])
    try:
        write_new(receipt_root / 'complete-COMMAND.json', terminal)
    except BaseException as error:
        if primary is None:
            primary, primary_traceback = error, BaseException.__dict__['__traceback__'].__get__(error)
        else:
            secondary.append(error)
    if primary is not None:
        if secondary:
            BaseException.__dict__['__dict__'].__get__(primary)['completion_secondary_errors'] = tuple(secondary)
        raise BaseException.with_traceback(primary, primary_traceback)
    if result.returncode:
        raise SystemExit(result.returncode)


def finish():
    s, R, F, P = j.s, j.R, j.F, j.PARENT
    assert s.sha(R / 'AMENDMENT.json') == 'ad3091e4ac129d0efcecae70b45ff15d45d6dedcc0c52dc30efead3714929776'
    assert s.sha(j.Q / 'TRANSFER-MANIFEST.json') == '2a3abde78bd4ab25af268ad1b16cef9eeaf9e2c30586c06fac4600876ba3c7c6'
    assert s.sha(R / 'complete_source.py') == '72aa88d041a50e728a477e9632cec956c2a57c0fbcee503d25261ad2da60193b'
    review_path = F / '.agents/runtime/js8-publication-recovery-review-20261017/REVIEW-R2.json'
    assert s.sha(review_path) == 'cc71f54a116bb57e6d6cd01d40f7a58611c856ef08f25815348b26526ff31b4e'
    helper_path = R / 'independent-destination/COMPLETION-HELPER-REVIEW-R2.json'
    assert s.sha(helper_path) == '4ec105fd63463c41bb286089c7d081e981c53be5c509d1b1bf0358bd19b312a9'
    baseline_path = R / 'ACCEPTED-SOURCE-BASELINE.json'
    assert not baseline_path.exists()
    m = j.manifest()
    j.verify(source='after')
    claim = j.require_current_claim()
    assert claim['executor_id'] == '/root'
    readiness_ref = j.exact_ref(R / 'SOURCE-PUBLICATION-PREFLIGHT.json')
    readiness = j.require_candidate_readiness(readiness_ref, source='after')
    j.require_validation(readiness_ref, source='after')
    full_ref = j.exact_ref(R / 'destination-full/RESULT.json')
    launch_ref = j.exact_ref(R / 'destination-full-LAUNCH-RESULT.json')
    _, full = j.proof(full_ref)
    _, launch = j.proof(launch_ref)
    j.require_full(full, launch, 'destination-full', full_ref)
    delivered_path = R / 'independent-destination/amendment-fixture2/DELIVERED-REVIEW.json'
    delivered = j.current_json(delivered_path)
    assert delivered['reviewer'] == '/root/publication_recovery_review'
    assert delivered['decision'] == 'approved' and delivered['exit_status'] == 0
    assert delivered['destination_full'] == full_ref and delivered['destination_full_launch'] == launch_ref
    assert delivered['completion_helper_review'] == j.exact_ref(helper_path)
    application_ref = j.exact_ref(R / 'active-application/APPLIED.json')
    assert delivered['application'] == application_ref
    release = dict(schema_version=1, executor='/root', run_id=j.RUN, phase='complete',
        amendment=j.exact_ref(R / 'AMENDMENT.json'), manifest_sha256=s.sha(j.Q / 'TRANSFER-MANIFEST.json'),
        reviewed_scripts=j.scripts(), Source_publication=False, automatic_retry=False,
        all_conflicting_Source_pinned_runs_released=True, amendment_review=j.exact_ref(review_path),
        expected_ids_sha256=m['case_set']['sha256'], Source_before_map_sha256=m['Source_before_map_sha256'],
        claim_input_hash=claim['input_hash'], claim_started_at=claim['claimed_at'],
        candidate_readiness=readiness_ref, destination_full=full_ref, destination_full_launch=launch_ref,
        application=application_ref, delivered_review=j.exact_ref(delivered_path),
        completion_helper_review=j.exact_ref(helper_path))
    release_path = R / 'releases/complete.json'
    s.write_new(release_path, release)
    pin = s.sha(release_path)
    j.require_release(release_path, pin, 'complete')
    command = [str(j.PY), '-B', '-X', 'utf8', str(R / 'complete_source.py'),
               '--release-path', str(release_path), '--release-sha256', pin]
    run_completion(command, F, R, j.exact_ref(release_path), s.write_new, s.utc)
    # Only the actual installed coordinator completion can support acceptance.
    state_path = P / j.RUN / 'state.json'
    claims_path = P / j.RUN / 'claims.json'
    receipt_path = P / j.RUN / 'receipts/integrate.json'
    result_path = P / j.RUN / 'results/integrate.json'
    state, claims = j.current_json(state_path), j.current_json(claims_path)
    receipt, stored = j.current_json(receipt_path), j.current_json(result_path)
    states = {name: row['state'] for name, row in state['nodes'].items()}
    assert set(states) == {'discover', 'plan', 'implement', 'review', 'validate', 'integrate'}
    assert all(value == 'SUCCEEDED' for value in states.values()) and claims == {}
    assert state['nodes']['integrate']['receipt_hash'] == receipt['receipt_hash'] == stored['receipt_hash']
    assert receipt['input_hash'] == claim['input_hash'] and receipt['executor_id'] == '/root'
    assert receipt['exit_status'] == 0 and receipt['result']['Source_accepted'] is True
    assert receipt['result'] == stored['result'] and receipt['result']['destination_full'] == full_ref
    assert receipt['result']['delivered_review'] == j.exact_ref(delivered_path)
    j.verify(source='after')
    applied = j.current_json(R / 'active-application/APPLIED.json')
    source = {name: s.ordinary(F / name) for name in m['expected_payload_hashes']}
    assert source == applied['source352']
    previous = F / '.agents/runtime/js7-20261015/amendment-fixture1/ACCEPTED-SOURCE-BASELINE.json'
    assert s.sha(previous) == 'bd7af13da30e54aa916696cb9c4dbcd32539e2600e0fdc02f8af56f63d47fbbf'
    baseline = dict(at=s.utc(), project='Project-AI: CETA', source_root=str(F),
        accepted_by='Actual installed integration receipt and distinct delivered-source review',
        manifest=j.exact_ref(j.Q / 'TRANSFER-MANIFEST.json'), amendment=j.exact_ref(R / 'AMENDMENT.json'),
        previous_baseline=j.exact_ref(previous), integrate=j.exact_ref(receipt_path),
        integrate_result=j.exact_ref(result_path), integrate_fingerprint=receipt['receipt_hash'],
        actual_integrate_state='SUCCEEDED', actual_sequence=state['sequence'], ledger_head=state['ledger_head'],
        state=j.exact_ref(state_path), claims_reference=j.exact_ref(claims_path), claims=claims,
        all_six_states=states, Source_accepted=True, Source_payloads=len(source),
        product_python_modules=sum(name.startswith('src/ceta/') and name.endswith('.py') for name in source),
        source=source, effective_payload_hashes=m['expected_payload_hashes'], application_paths=m['application_paths'],
        application=application_ref, source_publication_preflight=readiness_ref,
        prior_failed_candidate=readiness['prior_failed_candidate'], destination_full=full_ref,
        destination_full_launch=launch_ref, delivered_review=j.exact_ref(delivered_path),
        completion_helper_review=j.exact_ref(helper_path), full_cases=2334, independent_cases=180,
        copied_code_new_authorship_credit=0, finite_Source_snapshot_only=True,
        full_product_complete=False, live_isolation_accepted=False, genuine_owner_effect_accepted=False,
        limits=['The prior failed candidate remains failed and is preserved with its exact evidence.',
                'This accepts the published source cut only; application, installed, model, endurance and human gates remain separate.',
                'The bounded no-profile result proves the observed refusal and retirement; its causal explanation and positive isolation remain unproved.'])
    s.write_new(baseline_path, baseline)
    print(json.dumps(dict(baseline=j.exact_ref(baseline_path), Source_accepted=True,
        Source_payloads=len(source), full_product_complete=False)), flush=True)


if __name__ == '__main__':
    finish()
