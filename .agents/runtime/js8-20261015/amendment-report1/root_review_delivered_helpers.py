"""Record Root's personal delta review and exact helper identity checks."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

F = Path('T:/00-Active/Project-AI-CETA')
R = Path(__file__).parent
V = R / 'independent-destination'
OLD = R.parent / 'amendment-order1/independent-destination'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path):
    return dict(repository_relative_path=path.relative_to(F).as_posix(), sha256=digest(path))


requirements = V / 'RELEASE-REQUIREMENTS-NATIVE-PREFIX.json'
assert digest(requirements) == '9f6a8fadeb40a8fecddf14ed3e84c946f368aa8774a46f810a2b3c74643d3c26'
value = json.loads(requirements.read_bytes())
p = json.loads((V / 'PREPARATION.json').read_bytes())
assert digest(V / 'PREPARATION.json') == 'b834a705bb446168198c3fbd783a17d0742785fcad080295ef871c30441f6f69'
assert digest(V / 'HELPER-DELTA.diff') == '14c6d3efadc9a64c61779d4e26ea8876cf40c2b2f0f176cd837b81aa59e6fa38'
actual = {name: digest(V / name) for name in value['fixed_fields']['reviewer_helpers']}
assert actual == value['fixed_fields']['reviewer_helpers'] == p['helpers']
unchanged = [name for name, pin in actual.items() if digest(OLD / name) == pin]
assert set(actual) - set(unchanged) == {'review_support.py', 'record_actual_delivered_review.py'}
old_preparation = json.loads((OLD / 'PREPARATION.json').read_bytes())
assert p['required_ids'] == old_preparation['required_ids'] and len(p['required_ids']) == 180
assert p['native_cpu_ids'] == old_preparation['native_cpu_ids'] and len(p['native_cpu_ids']) == 7
assert not Path(p['fixture_root']).exists()
out = dict(schema_version=1, reviewer='/root', author='/root/publication_recovery_review',
    at=datetime.now(timezone.utc).isoformat(), decision='approved', exit_status=0,
    scope='Exact independent delivered helper delta and unchanged original methods',
    requirements=ref(requirements), preparation=ref(V / 'PREPARATION.json'),
    helper_delta=ref(V / 'HELPER-DELTA.diff'), helpers=actual,
    byte_identical_helpers=unchanged, required_case_count=180, native_case_count=7,
    findings=[
        'Personally inspected complete changed helper diff, release validator, final release fields and completion-helper review.',
        'Actual reviewer identity and final author pins replace the prior unused preparation.',
        'Original candidate failure is authenticated by publication readiness; canonical destination full remains mandatory.',
        'Current Root claim, exact352 destination hashes, four original native identities and bounded fixture remain required.',
        'Five helper files and all selected original case IDs remain unchanged.',
        'No native execution is authorized until a fresh Root release after destination full.'
    ], Source_accepted=False, native_execution=False)
with (R / 'ROOT-DELIVERY-HELPER-REVIEW.json').open('x', encoding='utf-8') as stream:
    stream.write(json.dumps(out, indent=2) + '\n')
print(json.dumps(ref(R / 'ROOT-DELIVERY-HELPER-REVIEW.json')))
