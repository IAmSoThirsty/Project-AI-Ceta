"""Bind released author cut before any independent acceptance execution."""
from ac_support import *

assert len(sys.argv) == 4
manifest_sha, implement_sha, readback_sha = sys.argv[1:]
assert sha(Q / 'TRANSFER-MANIFEST.json') == manifest_sha
assert sha(AUTHOR_R / 'implement.json') == implement_sha
assert sha(AUTHOR_R / 'AUTHOR-READBACK.json') == readback_sha
state = json.loads((AUTHOR_R / RUN / 'state.json').read_text())
claims = json.loads((AUTHOR_R / RUN / 'claims.json').read_text())
assert state['nodes']['implement']['state'] == 'SUCCEEDED' and state['nodes']['review']['state'] == 'READY' and not claims
write_new(D / 'FROZEN-BINDING.json', {'observed_at': utc(), 'actor': ACTOR,
    'candidate': str(Q), 'manifest_sha256': manifest_sha, 'implement_sha256': implement_sha,
    'readback_sha256': readback_sha, 'state': state,
    'scope': 'Only runtime/independent-review and own disposable descendants; candidate/Source/E3 read-only',
    'qualification': 'Safe refusal and resource custody; positive restrictive-worker isolation remains unexecuted'})
before = candidate_cut(); source = source_cut()
write_new(D / 'initial-observation.json', {'observed_at': utc(), 'candidate': before, 'source': source,
    'preparation_reader_failures': [
        'First verifier-template lookup omitted operational subdirectory; corrected read used actual path.',
        'First historical rg search traversed owned dangling test links; narrowed explicit support reads followed.']})

# The original native fixture support remains byte-exact. Its globals come from
# this reviewer-owned ac_support, so all created resources stay under D.
for name in ('native_fixture_support.py',):
    manifest = json.loads((Q / 'TRANSFER-MANIFEST.json').read_text())
    assert ordinary(AUTHOR_R / name) == manifest['review_support'][name]
    fs.write_new(D / name, fs.read_bytes(AUTHOR_R / name))
(D / 'build-r2').mkdir()
native = AUTHOR_R / 'build-r2/isolated_worker.exe'
assert sha(native) == '527518104fb84c430e3e9e0be61982c533b0c6fbb13e1a85e959ba1a3866ad0f'
fs.write_new(D / 'build-r2/isolated_worker.exe', fs.read_bytes(native))

# Original Windows job tests derive their fixture/source roots from __file__.
# Use a byte-identical connected harness rather than writing into frozen Q.
harness = D / 'test-harness'
for name, row in before.items():
    if name.startswith('src/') or name == 'tests/contract/test_windows_jobs.py':
        target = harness / name; target.parent.mkdir(parents=True, exist_ok=True)
        fs.write_new(target, fs.read_bytes(Q / name))
        assert sha(target) == row['sha256']
write_new(D / 'reviewer-support-binding.json', {
    'native_fixture_support': {'author': reference(AUTHOR_R / 'native_fixture_support.py'),
                               'reviewer': reference(D / 'native_fixture_support.py'), 'byte_exact': True},
    'native_helper': {'author': ordinary(native), 'reviewer': ordinary(D / 'build-r2/isolated_worker.exe'),
                     'byte_exact': True, 'authored_source_loc_credit': 0},
    'job_harness': 'Byte-identical original test and source dependency closure; all derived fixture paths under reviewer D',
    'source_application': False, 'persistent_profile_creation': False})
done, response = invoke(['node', 'claim', RUN, 'review', '--executor', ACTOR, '--workspace', str(Q)], 'review-claim')
assert done.returncode == 0 and response['allowed'] and response['claim']['executor_id'] == ACTOR
assert candidate_cut() == before
print(json.dumps({'claim_executor': ACTOR, 'candidate_members': len(before), 'source_payloads': len(source)}), flush=True)
