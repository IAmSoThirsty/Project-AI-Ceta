"""Verify the single real author completion and seal the immutable ET2 cut."""
from et_support import *
local_path, persisted_path = R / 'implement.json', R / RUN / 'receipts/implement.json'
local, persisted = json.loads(local_path.read_text()), json.loads(persisted_path.read_text())
fields = {'schema_version', 'run_id', 'node_id', 'executor_id', 'started_at', 'finished_at',
    'input_hash', 'changed_files', 'result', 'commands', 'validations', 'exit_status'}
assert set(local) == fields and set(persisted) == fields | {'git_baseline', 'observed_git', 'receipt_hash'}
typed = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
for name in fields: assert typed(local[name]) == typed(persisted[name])
state = json.loads((R / RUN / 'state.json').read_text())
claims = json.loads((R / RUN / 'claims.json').read_text())
assert state['nodes']['implement']['state'] == 'SUCCEEDED' and state['nodes']['review']['state'] == 'READY'
assert state['sequence'] == 7 and claims == {}
manifest = json.loads((Q / 'TRANSFER-MANIFEST.json').read_text())
assert local['result']['manifest'] == reference(Q / 'TRANSFER-MANIFEST.json')
for name, row in manifest['payloads'].items(): assert ordinary(Q / name) == row
source = json.loads((R / 'SOURCE-INPUTS.json').read_text())['Source290']
assert {name: ordinary(F / name) for name in source} == source
write_new(R / 'AUTHOR-READBACK.json', {'recorded_at': utc(), 'manifest': reference(Q / 'TRANSFER-MANIFEST.json'),
    'local_implement': reference(local_path), 'persisted_implement': reference(persisted_path),
    'all12_authored_fields_typed_exact': True, 'state': state, 'claims': claims,
    'frozen_payload_count': 316, 'Source290_retained': True, 'Source_application': False})
names = ('HANDOFF.json', 'implement.json', 'AUTHOR-READBACK.json', 'SELF-REVIEW.json', 'connected-r1.json',
    'connected-r1.txt', 'input-conservation-final.json', 'environment-final.json', 'implementation-measures.json',
    'all-source-imports.json', 'original-method-conservation.json', 'publication-before-images.json',
    'PRIOR-FAILURES.json', 'owned-fixture-inventory.json')
write_new(R / 'AUTHOR-SEAL.json', {'sealed_at': utc(), 'author': ACTOR,
    'manifest': reference(Q / 'TRANSFER-MANIFEST.json'), 'members': {name: reference(R / name) for name in names},
    'candidate_immutable': True, 'actual_author_claim_released': True, 'distinct_review_required': True,
    'Source_application': False, 'genuine_native_effect_invocation': False})
print(json.dumps({'implement': 'SUCCEEDED', 'review': 'READY', 'sequence': 7, 'claims': claims,
    'manifest': reference(Q / 'TRANSFER-MANIFEST.json'), 'implement_receipt': reference(local_path),
    'readback': reference(R / 'AUTHOR-READBACK.json'), 'seal': reference(R / 'AUTHOR-SEAL.json')}))
