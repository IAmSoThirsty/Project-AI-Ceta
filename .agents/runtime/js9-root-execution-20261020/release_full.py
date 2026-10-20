"""Bind one reviewed full-suite phase to the actual two-case human authorization."""
from pathlib import Path
import hashlib
import importlib
import json
import sys
import time
import uuid

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).resolve().parent
D = F / '.agents/runtime/js9-runtime-20261020/successor-r2'
assert len(sys.argv) == 2 and sys.argv[1] in ('candidate-full', 'destination-full')
phase = sys.argv[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
ref = lambda path: dict(repository_relative_path=path.relative_to(F).as_posix(), sha256=sha(path))
assert sha(D/'PACKET.json') == 'eb5f4c993a74f7b378db9b2dd10e039fadc64ebff3c31887c78393ce58157055'
review_path = F/'.agents/runtime/js9-successor-tools-review-20261020/R2/review.json'
assert sha(review_path) == 'c480b380416beee3331ae255151d1a59cbe476f433950787ce85fcc1ff2b6a26'
authorization_path = R/'NO-PROFILE-AUTHORIZATION.json'
authorization = json.loads(authorization_path.read_bytes())
assert authorization['answer'] == 'Authorize these two exact no-profile test executions'
assert authorization['executions_per_phase'] == 1 and phase in authorization['permitted_phases']
assert authorization['reviewed_packet_sha256'] == sha(D/'PACKET.json')
assert not authorization['profile_creation'] and not authorization['profile_deletion'] and not authorization['automatic_retry']
node = 'integrate' if phase == 'destination-full' else 'implement'
state_path = R/'js9-root-execution-20261020/state.json'
claims_path = R/'js9-root-execution-20261020/claims.json'
state = json.loads(state_path.read_bytes())
claim = json.loads(claims_path.read_bytes())[node]
assert state['nodes'][node]['state'] == 'RUNNING' and claim['executor_id'] == '/root'
assert claim['workspace'] == str(F if phase == 'destination-full' else D)
assert not (D/phase).exists() and not (D/(phase+'-LAUNCH-ATTEMPT.json')).exists()
sys.path.insert(0, str(D))
import js9_support as j
j.verify(source='after' if phase == 'destination-full' else 'before')
packet = j.packet()
store = ref(D/'native_store_r2-CORROBORATION.json')
observer = ref(D/'native_observer_r2-CORROBORATION.json')
j.require_native_corroboration(store, 'native-store')
j.require_native_corroboration(observer, 'native-observer')
issued = time.time_ns()
nonce = uuid.uuid4().hex
subject = j.native_case_subject(phase, nonce)
gate = importlib.import_module('native_case_gate')
native_case = dict(schema_version=1, kind=gate.KIND, executor='/root', authority_basis=gate.AUTHORITY,
    run_id=gate.RUN, run_nonce=nonce, issued_at_ns=issued, expires_at_ns=issued+1_800_000_000_000,
    subject=subject, execute_exact_original_case=True, create_profiles=False, expected_denial_winerror=2)
raw = (json.dumps(native_case, indent=2, allow_nan=False)+'\n').encode()
gate.validate_release(raw, hashlib.sha256(raw).hexdigest(), subject, time.time_ns())
case_path = D/'releases'/('native-case-'+phase+'.json')
with case_path.open('xb') as stream:
    assert stream.write(raw) == len(raw)
release = dict(schema_version=1, executor='/root', run_id=packet['run_id'], phase=phase,
    packet=ref(D/'PACKET.json'), candidate_manifest=packet['candidate_manifest'],
    reviewed_scripts=packet['scripts'], case_set=packet['case_set'], Source_before=packet['Source_before'],
    automatic_retry=False, create_profiles=False, Source_publication=False,
    all_conflicting_Source_pinned_runs_released=True, issued_at_ns=issued,
    expires_at_ns=issued+1_800_000_000_000, independent_review=ref(review_path),
    native_case_release=ref(case_path), operator_authorization=ref(authorization_path),
    native_store_corroboration=store, native_observer_corroboration=observer,
    execution_lease=dict(claims=ref(claims_path), state=ref(state_path), node_id=node,
        input_hash=claim['input_hash']))
release_path = D/'releases'/(phase+'-r2.json')
with release_path.open('x', encoding='utf-8') as stream:
    json.dump(release, stream, indent=2)
    stream.write('\n')
j.require_release(release_path, sha(release_path), phase)
record = dict(phase=phase, release=ref(release_path), native_case_release=ref(case_path),
    operator_authorization=ref(authorization_path), run_nonce=nonce,
    qualification='One exact phase; no retry or profile creation; execution not yet performed')
with (R/(phase+'-RELEASE.json')).open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(record), flush=True)
