"""Controlled release checks; no product import, live claim or native effect."""
from pathlib import Path
from types import SimpleNamespace
import ast
import copy
import datetime
import hashlib
import json
import sys

V = Path(__file__).resolve().parent
R = V.parent
F = Path('T:/00-Active/Project-AI-CETA')
Q = F / '.agents/js8-amendment-report1-20261017'
ACTOR = '/root/publication_recovery_review'
rows = []

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def ref(path): return dict(repository_relative_path=path.relative_to(F).as_posix(), sha256=sha(path))
def save(name, value):
    with (V / name).open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')

p = read(V / 'PREPARATION.json')
m = read(Q / 'TRANSFER-MANIFEST.json')
PIN = '8ba8bee2d4bea486c6940c9ddddde0df03972c1bf3a6eba818476d4ee87ac0ad'
AMENDMENT_PIN = 'fc5aec39792b2ba086fc70854549257fd014841c26c0c30e25d726c4f1938d7f'
assert sha(Q / 'TRANSFER-MANIFEST.json') == p['manifest_sha256'] == PIN
assert sha(R / 'AMENDMENT.json') == p['amendment']['sha256'] == AMENDMENT_PIN
assert sha(R / 'complete_source.py') == '72aa88d041a50e728a477e9632cec956c2a57c0fbcee503d25261ad2da60193b'
source = ast.parse((V / 'review_support.py').read_bytes())
selected = [node for node in source.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
            and node.name in ('preparation', 'require_delivery_release', 'FixtureRoot')]
assert len(selected) == 3

class ClaimFenceReached(Exception): pass
class ReadinessFenceReached(Exception): pass
class ValidationFenceReached(Exception): pass
class DestinationFenceReached(Exception): pass
def claim_fence(): raise ClaimFenceReached('BEFORE_REAL_CLAIM_OR_SOURCE_OPERATIONS')

current = dict(preparation=p, release=None)
helper = dict(reviewer=ACTOR, decision='approved', exit_status=0, manifest_sha256=PIN,
              completion_script_sha256=sha(R / 'complete_source.py'))
j = SimpleNamespace(current_json=lambda path: copy.deepcopy(current['preparation']),
    exact_ref=ref, manifest=lambda: m, pinned_json=lambda path, pin: copy.deepcopy(current['release']),
    proof=lambda reference: (V / 'COMPLETION-HELPER-REVIEW.json', copy.deepcopy(helper)),
    require_current_claim=claim_fence)
s = SimpleNamespace(sha=sha, fs=SimpleNamespace(safe_components=lambda path: path))
env = dict(Path=Path, F=F, R=R, Q=Q, V=V, ACTOR=ACTOR, PIN=PIN, AMENDMENT_PIN=AMENDMENT_PIN,
           j=j, s=s, helper_pins=lambda: {name: sha(V / name) for name in p['helpers']})
exec(compile(ast.Module(body=selected, type_ignores=[]), str(V / 'review_support.py'), 'exec'), env)

def check(name, action, expected=None):
    try: action()
    except BaseException as error:
        if expected is None or type(error) is not expected: raise
        rows.append(dict(name=name, passed=True, observed=type(error).__name__))
    else:
        assert expected is None, name
        rows.append(dict(name=name, passed=True, observed='returned'))

check('exact_preparation_metadata_passes', lambda: env['preparation']())
for key, value in (('manifest_sha256', '0' * 64), ('required_ids', p['required_ids'][:-1]),
                   ('helpers', {}), ('expected_payload_hashes', {}), ('amendment', {})):
    current['preparation'] = copy.deepcopy(p); current['preparation'][key] = value
    check('preparation_rejects_' + key, lambda: env['preparation'](), AssertionError)
current['preparation'] = p
release = dict(schema_version=1, phase='DELIVERY-REVIEW', executor='/root', reviewer=ACTOR,
    manifest_sha256=PIN, reviewer_helpers=p['helpers'], amendment=p['amendment'],
    preparation=ref(V / 'PREPARATION.json'), fixture_root=p['fixture_root'], one_attempt=True,
    automatic_retry=False, timeout_seconds=600, Source_publication=False,
    all_conflicting_Source_runs_released=True, profile_operations=False, restricted_launch=False,
    native_cpu_case_ids=p['native_cpu_ids'], completion_script_sha256=sha(R / 'complete_source.py'),
    completion_helper_review={'controlled_probe': True})
current['release'] = release
call = lambda: env['require_delivery_release'](R / 'releases/delivery-review.json', 'controlled-pin')
check('valid_controlled_release_reaches_claim_fence_only', call, ClaimFenceReached)
for key, value in (('schema_version', True), ('reviewer', '/root'), ('manifest_sha256', '0' * 64),
    ('reviewer_helpers', {}), ('amendment', {}), ('preparation', {}), ('fixture_root', 'C:/wrong'),
    ('one_attempt', False), ('automatic_retry', True), ('timeout_seconds', True), ('timeout_seconds', 601),
    ('Source_publication', True), ('all_conflicting_Source_runs_released', False),
    ('profile_operations', True), ('restricted_launch', True), ('native_cpu_case_ids', []),
    ('completion_script_sha256', '0' * 64)):
    current['release'] = copy.deepcopy(release); current['release'][key] = value
    check('release_rejects_' + key + '_' + str(value)[:8], call, AssertionError)
current['release'] = release
check('nested_release_path_denied', lambda: env['require_delivery_release'](
    R / 'releases/nested/delivery-review.json', 'controlled-pin'), AssertionError)
mapper = env['FixtureRoot'](F, Path(p['fixture_root']))
check('fixture_prefix_routes', lambda: exec("assert mapper/'.agents/fixtures/a' == Path(p['fixture_root'])/'a'", globals()))
check('source_path_remains_exact', lambda: exec("assert mapper/'src/ceta' == F/'src/ceta'", globals()))
for name in ('../outside', 'C:/outside', 'T:/outside'):
    check('fixture_rejects_' + name, lambda name=name: mapper / name, AssertionError)

# Proceed only through controlled ports to verify the new gates remain ordered.
claim = dict(input_hash='a' * 64, claimed_at='controlled-claim')
ready = {'controlled_readiness': True}
full_ref, launch_ref = {'controlled_destination': True}, {'controlled_launch': True}
live = copy.deepcopy(release)
live.update(claim_input_hash=claim['input_hash'], claim_started_at=claim['claimed_at'],
            candidate_readiness=ready, destination_full=full_ref, destination_full_launch=launch_ref)
current['release'] = live
j.require_current_claim = lambda: claim
def readiness_fence(reference, *, source):
    assert reference == ready and source == 'after'
    raise ReadinessFenceReached()
j.require_candidate_readiness = readiness_fence
check('readiness_is_required_after_exact_claim', call, ReadinessFenceReached)
current['release'] = copy.deepcopy(live); current['release']['claim_input_hash'] = 'b' * 64
check('wrong_claim_rejected_before_readiness', call, AssertionError)
current['release'] = live
j.require_candidate_readiness = lambda reference, source: None
def validation_fence(reference, *, source):
    assert reference == ready and source == 'after'
    raise ValidationFenceReached()
j.require_validation = validation_fence
check('actual_validation_receipt_is_required', call, ValidationFenceReached)
j.require_validation = lambda reference, source: None
def proof(reference):
    if reference == full_ref: return R / 'destination-full/RESULT.json', {'full': True}
    if reference == launch_ref: return R / 'destination-full-LAUNCH-RESULT.json', {'launch': True}
    return V / 'COMPLETION-HELPER-REVIEW.json', copy.deepcopy(helper)
j.proof = proof
def destination_fence(full, launch, phase, reference):
    assert phase == 'destination-full' and full == {'full': True} and launch == {'launch': True} and reference == full_ref
    raise DestinationFenceReached()
j.require_full = destination_fence
check('strict_destination_full_required_before_application', call, DestinationFenceReached)
assert not Path(p['fixture_root']).exists()
assert not any(name == 'ceta' or name.startswith('ceta.') for name in sys.modules)
assert all(sha(V / name) == value for name, value in p['helpers'].items())
save('PURE-CHECKS.json', dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    author=ACTOR, preparation=ref(V / 'PREPARATION.json'), probe=ref(Path(__file__)),
    source_AST=ref(V / 'review_support.py'), checks=rows, exit_status=0,
    limitations=['Exact AST functions with controlled ports; no actual claim, Source or native operations.',
                 'Root must independently review these reviewer-authored helpers before a bounded release.'],
    source_imports=False, native_execution=False, fixture_created=False, Source_accepted=False))
save('RELEASE-REQUIREMENTS.json', dict(purpose='Root release construction requirements; not an executable release.',
    exact_release_parent=str(R / 'releases'), preparation=ref(V / 'PREPARATION.json'),
    completion_helper_review_path=str(V / 'COMPLETION-HELPER-REVIEW.json'),
    fixed_fields={key: value for key, value in release.items() if key != 'completion_helper_review'},
    required_live_fields=['claim_input_hash', 'claim_started_at', 'candidate_readiness',
                          'destination_full', 'destination_full_launch', 'application', 'completion_helper_review'],
    launch_script=ref(V / 'launch_delivered.py'), review_recorder=ref(V / 'record_actual_delivered_review.py'),
    exact_interpreter=str(F / '.agents/source-assembly-20261014T021300Z/.agents/e3/Scripts/python.exe'),
    switches=['-B', '-X', 'utf8'], release_arguments=['--release-path', '--release-sha256'],
    authorized_attempts=0, held_until='Root personally reviews helper delta and provides exact one-attempt release.',
    mandatory_native_denials=['Profile creation/deletion', 'Restricted launch', 'No-profile isolation test'],
    independent_full_suite_runs=0, Source_publication=False))
print(json.dumps(dict(checks=len(rows), exit_status=0, pure_checks=ref(V / 'PURE-CHECKS.json'),
    release_requirements=ref(V / 'RELEASE-REQUIREMENTS.json'))))
