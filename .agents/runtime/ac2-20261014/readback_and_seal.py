"""One fresh actual author readback; never replay completed transitions."""
from ac2_support import *

strict = json.loads((R / 'implement.json').read_text())
stored_path = R / RUN / 'receipts/implement.json'
stored = json.loads(stored_path.read_text())
assert len(strict) == 12 and set(stored) == set(strict) | {'git_baseline', 'observed_git', 'receipt_hash'}
def typed(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
assert all(typed(stored[key]) == typed(value) for key,value in strict.items())
state = json.loads((R / RUN / 'state.json').read_text())
claims = json.loads((R / RUN / 'claims.json').read_text())
assert state['nodes']['implement']['state'] == 'SUCCEEDED' and state['nodes']['review']['state'] == 'READY' and not claims
manifest = json.loads((Q / 'TRANSFER-MANIFEST.json').read_text())
assert len(manifest['payloads']) == 294
assert all(ordinary(Q / name) == row for name,row in manifest['payloads'].items())
write_new(R / 'AUTHOR-READBACK.json', {'observed_at': utc(), 'run_id': RUN, 'author': ACTOR,
    'sequence': state['sequence'], 'states': {name:row['state'] for name,row in state['nodes'].items()}, 'claims': claims,
    'strict_submitted_receipt': reference(R / 'implement.json'), 'persisted_receipt': reference(stored_path),
    'strict_12_authored_fields_type_exact': True, 'manifest': reference(Q / 'TRANSFER-MANIFEST.json'),
    'all294_payloads_exact': True, 'review_ready': True, 'author_released': True,
    'isolation_qualified': False, 'activation_ready': False, 'source_published': False})
members = {path.relative_to(Q).as_posix(): ordinary(path) for path in Q.rglob('*') if path.is_file()}
assert len(members) == 295 and set(members) == set(manifest['payloads']) | {'TRANSFER-MANIFEST.json'}
write_new(R / 'AUTHOR-SEAL.json', {'sealed_at': utc(), 'author': ACTOR, 'candidate': str(Q),
    'candidate_members': members, 'manifest': reference(Q / 'TRANSFER-MANIFEST.json'),
    'readback': reference(R / 'AUTHOR-READBACK.json'), 'handoff': reference(R / 'HANDOFF.json'),
    'author_claim_released': True, 'independent_review_pending': True,
    'old_cuts_Source_E3_external_roots_read_only': True})
print(json.dumps({'implement': 'SUCCEEDED', 'review': 'READY', 'sequence': state['sequence'], 'claims': claims,
    'manifest': reference(Q / 'TRANSFER-MANIFEST.json'), 'implement_receipt': reference(R / 'implement.json'),
    'readback': reference(R / 'AUTHOR-READBACK.json'), 'seal': reference(R / 'AUTHOR-SEAL.json')}), flush=True)
