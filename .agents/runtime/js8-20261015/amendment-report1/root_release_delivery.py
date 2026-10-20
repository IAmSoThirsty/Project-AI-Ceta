"""Issue the reviewed one-attempt delivered-source check after terminal full proof."""
import json
import sys
import amendment_support as j

V = j.R / 'independent-destination'
requirements_path = V / 'RELEASE-REQUIREMENTS-NATIVE-PREFIX.json'
assert j.s.sha(requirements_path) == '9f6a8fadeb40a8fecddf14ed3e84c946f368aa8774a46f810a2b3c74643d3c26'
requirements = j.current_json(requirements_path)
assert j.s.sha(V / 'PREPARATION.json') == 'b834a705bb446168198c3fbd783a17d0742785fcad080295ef871c30441f6f69'
assert j.s.sha(V / 'COMPLETION-HELPER-REVIEW-R2.json') == '4ec105fd63463c41bb286089c7d081e981c53be5c509d1b1bf0358bd19b312a9'
command = j.current_json(j.R / 'destination-full-COMMAND.json')
assert type(command['exit_status']) is int and command['exit_status'] == 0
full_ref = j.exact_ref(j.R / 'destination-full/RESULT.json')
launch_ref = j.exact_ref(j.R / 'destination-full-LAUNCH-RESULT.json')
_, full = j.proof(full_ref)
_, launch = j.proof(launch_ref)
j.require_full(full, launch, 'destination-full', full_ref)
claim = j.require_current_claim()
assert claim['executor_id'] == '/root'
j.verify(source='after')
release = dict(requirements['fixed_fields'])
release.update(claim_input_hash=claim['input_hash'], claim_started_at=claim['claimed_at'],
    candidate_readiness=j.exact_ref(j.R / 'SOURCE-PUBLICATION-PREFLIGHT.json'),
    destination_full=full_ref, destination_full_launch=launch_ref,
    application=j.exact_ref(j.R / 'active-application/APPLIED.json'),
    completion_helper_review=j.exact_ref(V / 'COMPLETION-HELPER-REVIEW-R2.json'))
assert all(name in release for name in requirements['required_live_fields'])
path = j.R / 'releases/delivered-review.json'
j.s.write_new(path, release)
sys.path.insert(0, str(V))
from review_support import require_delivery_release
require_delivery_release(path, j.s.sha(path))
print(json.dumps(dict(release=j.exact_ref(path), reviewer=release['reviewer'],
    exact_command=[str(j.PY), '-B', '-X', 'utf8', str(V / 'launch_delivered.py'),
                   '--release-path', str(path), '--release-sha256', j.s.sha(path)],
    one_attempt=True, timeout_seconds=600, Source_accepted=False)), flush=True)
