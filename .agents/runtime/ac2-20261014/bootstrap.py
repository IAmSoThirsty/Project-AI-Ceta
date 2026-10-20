"""Actual fresh AC2 claims, current Source binding, exact AC1 defect lineage."""
from ac2_support import *

assert not Q.exists(); Q.mkdir()
assert sha(PARENT / 'TRANSFER-MANIFEST.json') == 'dbb2aec8f60a72fde258dd972c260dccc8beaed564812ca8147671ba0a4a4160'
parent = json.loads((PARENT / 'TRANSFER-MANIFEST.json').read_text())
prior_review = PRIOR_R / 'independent-review'
assert sha(prior_review / 'actual-review-readback.json') == '9c8ced266743ac40b36bad7ae01336167ec102cfb818f998c63aa284c6b07bc9'
assert json.loads((PRIOR_R / 'ac1-20261014/state.json').read_text())['nodes']['review']['state'] == 'FAILED'
assert not json.loads((PRIOR_R / 'ac1-20261014/claims.json').read_text())
invoke(['run', 'init', '--root', 'T:/', '--scope', str(Q), '--run-id', RUN], 'run-init')
claim('discover')
root_join = F / '.agents/runtime/perf1-20261014/active-application/JOINED-SOURCE.json'
assert sha(root_join) == '700fafa5f50f536a363700edf714e60a6d32bf1358424142a9a7b12706470f57'
joined = json.loads(root_join.read_text()); hashes = joined['after_hashes']; assert len(hashes) == 290
source = {name: ordinary(F / name) for name in hashes}
assert {name:row['sha256'] for name,row in source.items()} == hashes
scope = parent['eligible_paths']; assert len(scope) == 4
for name in scope:
    try: fs.lstat(F / name)
    except FileNotFoundError: pass
    else: raise AssertionError('CREATE target exists: ' + name)
parent_rows = {name: ordinary(PARENT / name) for name in parent['payloads']}
assert all(parent_rows[name] == row for name,row in parent['payloads'].items())
inputs = {'observed_at': utc(), 'root': str(F), 'source_payloads': source,
    'source_join': reference(root_join), 'source_count': 290,
    'parent_manifest': reference(PARENT / 'TRANSFER-MANIFEST.json'), 'parent_payloads': parent_rows,
    'scope': scope, 'rejected_review': reference(prior_review / 'review.json'),
    'original_hostile_code': reference(prior_review / 'hostile_cleanup.py'),
    'original_failed_native_oracles': reference(prior_review / 'hostile-cleanup-r1.json'),
    'HEAD': fs.text_git(F, 'rev-parse', 'HEAD'), 'branch': fs.text_git(F, 'branch', '--show-current'),
    'dirty_tracked': fs.text_git(F, 'status', '--porcelain=v1', '-uno'),
    'source_writes_authorized': False, 'profile_creation_authorized': False,
    'forward_reuse': {name: {'old_sha256': row['sha256'], 'current_sha256': source[name]['sha256']}
                       for name,row in parent_rows.items() if name in source and row['sha256'] != source[name]['sha256']}}
write_new(R / 'source-inputs.json', inputs)
command = {'command': subprocess.list2cmdline([sys.executable, '-B', '-X', 'utf8', str(Path(__file__))]), 'exit_status': 0}
complete('discover', {'inputs': reference(R / 'source-inputs.json'), 'original_source_count': 290}, [command],
    [('Current Source290 and frozen rejected AC1 pinned', True), ('Exact four absent Source targets', True)])
claim('plan')
binding = {'run_id': RUN, 'actor': ACTOR, 'coordinator': '/root', 'role': 'R10 Tool and Execution Engineer',
    'scope': scope, 'classification': {'cleanup_custody': 'EXTEND', 'native_helper': 'REUSE', 'positive_isolation': 'BLOCKED'},
    'repair': 'Preserve primary control identity and caller-visible pending resources across attribute, SID and token finalization; independent cleanup attempts and explicit uncertainty prevent blind finalizer replay.',
    'acceptance': 'Original39 unchanged method bodies, retained three faulty-cleanup methods/six subcases with narrowly declared closed-job oracle adaptation, and focused native retry/uncertainty/concurrency cases.',
    'effect_boundary': 'Only fresh own native T fixtures; no profile/Source/E3/host ACL/config changes; actual restrictive error2 remains unqualified positive isolation.',
    'source_input': reference(R / 'source-inputs.json')}
write_new(R / 'TASK-BINDING.json', binding)
complete('plan', {'binding': reference(R / 'TASK-BINDING.json')}, [command],
    [('Single finite cleanup successor without new architecture', True), ('Activation/profile boundary stays closed', True)])
current = claim('implement'); assert current['baseline_snapshot'] == {}
for name, row in source.items():
    target = Q / name; target.parent.mkdir(parents=True, exist_ok=True)
    raw = fs.read_bytes(F / name); assert digest(raw) == row['sha256']; fs.write_new(target, raw)
for name in scope:
    raw = fs.read_bytes(PARENT / name); assert digest(raw) == parent_rows[name]['sha256']
    target = Q / name; target.parent.mkdir(parents=True, exist_ok=True); fs.write_new(target, raw)
    before = R / 'AC1-before-images' / name; before.parent.mkdir(parents=True, exist_ok=True); fs.write_new(before, raw)
write_new(R / 'implementation-started.json', {'observed_at': utc(), 'claim': current,
    'staged_current_source_files': 290, 'only_AC1_overlay': scope, 'payloads': 294,
    'historical_reuse_not_overlaid': inputs['forward_reuse'], 'new_reuse_LOC': 0})
print(json.dumps({'implement_claimed': True, 'payloads': 294, 'input_hash': current['input_hash']}), flush=True)
