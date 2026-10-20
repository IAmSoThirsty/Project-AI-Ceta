"""Issue Root engineering releases for the two reviewed non-profile native gates."""
from pathlib import Path
import hashlib
import json
import sys
import time

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
D = F / '.agents/runtime/js9-runtime-20261020/successor-r2'
PACKET = 'eb5f4c993a74f7b378db9b2dd10e039fadc64ebff3c31887c78393ce58157055'
REVIEW = F / '.agents/runtime/js9-successor-tools-review-20261020/R2/review.json'
REVIEW_PIN = 'c480b380416beee3331ae255151d1a59cbe476f433950787ce85fcc1ff2b6a26'


def ref(path):
    return dict(repository_relative_path=path.relative_to(F).as_posix(),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    assert ref(D / 'PACKET.json')['sha256'] == PACKET
    assert ref(REVIEW)['sha256'] == REVIEW_PIN
    packet = json.loads((D / 'PACKET.json').read_bytes())
    review = json.loads(REVIEW.read_bytes())
    assert review['decision'] == 'approved' and review['reviewed_scripts'] == packet['scripts']
    state_path = R / 'js9-root-execution-20261020/state.json'
    claims_path = R / 'js9-root-execution-20261020/claims.json'
    state = json.loads(state_path.read_bytes())
    claim = json.loads(claims_path.read_bytes())['implement']
    assert state['nodes']['implement']['state'] == 'RUNNING'
    assert claim['executor_id'] == '/root' and claim['workspace'] == str(D)
    assert claim['input_hash'] == state['nodes']['implement']['claim']['input_hash']
    prior_claims = json.loads((F / '.agents/runtime/js9-runtime-20261020/lease-r2/js9-runtime-r4-20261020/claims.json').read_bytes())
    assert 'evidence' not in prior_claims, 'PRIOR_EVIDENCE_OWNER_NOT_HANDED_OFF'
    sys.path.insert(0, str(D))
    import js9_support as j
    j.verify(source='before')
    directory = D / 'releases'
    directory.mkdir(exist_ok=False)
    issued = time.time_ns()
    result = {}
    for phase in ('native-store', 'native-observer'):
        release = dict(schema_version=1, executor='/root', run_id='js9-runtime-20261020', phase=phase,
            packet=ref(D / 'PACKET.json'), candidate_manifest=packet['candidate_manifest'],
            reviewed_scripts=packet['scripts'], case_set=packet['case_set'], Source_before=packet['Source_before'],
            automatic_retry=False, create_profiles=False, Source_publication=False,
            all_conflicting_Source_pinned_runs_released=True,
            issued_at_ns=issued, expires_at_ns=issued + 1_800_000_000_000,
            independent_review=ref(REVIEW),
            execution_lease=dict(claims=ref(claims_path), state=ref(state_path),
                input_hash=claim['input_hash'], node_id='implement'),
            authority_basis='Existing user-directed implementation and disposable component acceptance tests; no AppContainer profile API',
            qualification_scope='Disposable Windows component gate; no product authorization or full-product acceptance')
        path = directory / (phase + '-r2.json')
        with path.open('x', encoding='utf-8') as stream:
            json.dump(release, stream, indent=2)
            stream.write('\n')
        j.require_release(path, ref(path)['sha256'], phase)
        result[phase] = ref(path)
    with (R / 'NATIVE-RELEASES.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
