"""Prepare the two-path metadata publisher with the qualified native body retained."""
from pathlib import Path
import hashlib
import json

R = Path(__file__).resolve().parent
F, Q = R.parents[2], R.parents[2] / '.agents/ct3-20261014'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest_path = Q / 'TRANSFER-MANIFEST.json'
manifest_sha = sha(manifest_path)
parent = F / '.agents/runtime/rs-owner2-20261014/root-integration/apply_reviewed_reservations.py'
assert sha(parent) == 'af88b03f04593ae1a20d785bcc2fb0f8f604b68a5a36cce43b62d78cc4d848ed'
text = parent.read_text(encoding='utf-8')
body = text[text.index('    native.fs.safe_components(OUT, allow_missing=True)'):]
old_join = """    save(OUT / 'JOINED-SOURCE.json', {'accepted_base_full_sha256': sha(base_path),
        'accepted_base_integrate_sha256': sha(accepted_root / 'integrate.json'),
        'reservation_manifest_sha256': sha(manifest_path), 'before_hashes': before, 'after_hashes': after,
        'preserved_forward_reuse_paths': sorted(known_forward_reuse),
        'retained_forward_created_paths': ['tests/contract/test_process_observation_timing.py',
            'tests/contract/test_process_observation_validation.py', 'tests/contract/test_pressure_lifecycle.py'],
        'only_reservation_application_paths': sorted(ALLOWED)})"""
new_join = """    save(OUT / 'JOINED-SOURCE.json', {'accepted_source_full_sha256': sha(suite_path),
        'accepted_source_integrate_sha256': sha(accepted / 'integrate.json'),
        'metadata_manifest_sha256': sha(manifest_path),
        'retained_source_hashes': suite['after_hashes'],
        'metadata_before_hashes': {item['relative_path']: item['active_before_sha256'] for item in selected},
        'metadata_after_hashes': {item['relative_path']: item['candidate_sha256'] for item in selected},
        'only_metadata_application_paths': sorted(ALLOWED)})"""
assert body.count(old_join) == 1
body = body.replace(old_join, new_join)
body = body.replace('FIVE_RESERVATION_PATHS_APPLIED_WITH_ACCEPTED_BASE_RETAINED_AWAITING_DESTINATION_VERIFICATION',
                    'TWO_STATUS_PATHS_APPLIED_WITH_ACCEPTED_SOURCE_RETAINED_AWAITING_DESTINATION_VERIFICATION')
body = body.replace('exact five paths', 'exact two metadata paths').replace('actual_reservation_paths_applied', 'actual_status_paths_applied')
head = '''"""Publish only two independently reviewed status files, preserving native originals."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, importlib.util, json, os, stat

R = Path(__file__).resolve().parent
F, Q, RUN = R.parents[2], R.parents[2] / '.agents/ct3-20261014', 'ct3-20261014'
OUT = R / 'active-application'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
PUBLICATION = F / '.agents/runtime/rs2-20261014/apply_joined_source.py'
assert sha(PUBLICATION) == '4592a2ccee83904c6fd698a2145d82279e07c0cc27cabb45fd1c13b844baec77'
spec = importlib.util.spec_from_file_location('ct3_qualified_native_publication', PUBLICATION)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
ALLOWED = {'build/progress.json', 'handoff/continuity.json'}

def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\\n'); stream.flush(); os.fsync(stream.fileno())

def main():
    assert __debug__
    claim = read(R / RUN / 'claims.json')['integrate']
    assert claim['executor_id'] == '/root' and claim['workspace'] == str(F)
    state = read(R / RUN / 'state.json')
    assert state['nodes']['review']['state'] == state['nodes']['validate']['state'] == 'SUCCEEDED'
    review_path = R / 'independent-review/review.json'
    review, stored = read(review_path), read(R / RUN / 'receipts/review.json')
    keys = {'schema_version', 'run_id', 'node_id', 'executor_id', 'started_at', 'finished_at',
            'input_hash', 'changed_files', 'result', 'commands', 'validations', 'exit_status', 'decision'}
    assert set(review) == keys and set(stored) == keys | {'git_baseline', 'observed_git', 'receipt_hash'}
    assert review['decision'] == 'approved' and review['exit_status'] == 0 and review['executor_id'] != '/root'
    assert json.dumps(review, sort_keys=True, separators=(',', ':'), allow_nan=False) == json.dumps(
        {key: stored[key] for key in keys}, sort_keys=True, separators=(',', ':'), allow_nan=False)
    manifest_path = Q / 'TRANSFER-MANIFEST.json'
    assert sha(manifest_path) == MANIFEST_SHA
    manifest = read(manifest_path)
    assert review['result']['manifest_sha256'] == sha(manifest_path)
    helper = read(R / 'independent-review/publication-helper-review.json')
    assert helper['decision'] == 'approved' and helper['exit_status'] == 0
    assert helper['publication_script_sha256'] == sha(Path(__file__))
    assert helper['manifest_sha256'] == sha(manifest_path)
    assert set(manifest['application_paths']) == ALLOWED and len(manifest['payloads']) == 2
    accepted = F / '.agents/runtime/rs-owner2-20261014'
    accepted_state = read(accepted / 'rs-owner2-20261014/state.json')
    assert accepted_state['sequence'] == 13 and all(row['state'] == 'SUCCEEDED' for row in accepted_state['nodes'].values())
    assert read(accepted / 'rs-owner2-20261014/claims.json') == {}
    assert sha(accepted / 'integrate.json') == manifest['accepted_source_ledger']['integrate_receipt']['sha256']
    suite_path = F / manifest['source_suite']['repository_relative_path']
    assert sha(suite_path) == manifest['source_suite']['sha256']
    suite = read(suite_path)
    assert type(suite['tests_run']) is int and suite['tests_run'] == 1416 and len(suite['after_hashes']) == 286
    assert all(type(suite[key]) is int and suite[key] == 0 for key in ('failures', 'errors', 'skips', 'exit_status'))
    assert suite['expected_ids'] == suite['executed_ids'] and len(set(suite['executed_ids'])) == 1416
    assert all(sha(F / relative) == value for relative, value in suite['after_hashes'].items())
    selected, initial_identities = [], {}
    for item in manifest['payloads']:
        relative = item['relative_path']
        assert relative in ALLOWED and item['application_action'] == 'EXTEND_PRESERVE_BEFORE_IMAGE'
        assert native.exact_hash(Q / relative) == item['candidate_sha256']
        assert native.exact_hash(F / relative) == item['active_before_sha256']
        identity = native.fs.file_identity(native.fs.lstat(native.fs.safe_components(F / relative)))
        declared = dict(item['source_native_identity'])
        declared['mode'] = stat.S_IMODE(declared['mode'])
        assert identity == declared
        initial_identities[relative] = identity
        selected.append(item)
    assert len(selected) == 2
'''
head = head.replace('MANIFEST_SHA', repr(manifest_sha))
publisher = head + body
compile(publisher, str(R / 'apply_reviewed_status.py'), 'exec')
with (R / 'apply_reviewed_status.py').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(publisher)
with (R / 'publisher-lineage.json').open('x', encoding='utf-8') as stream:
    json.dump({'parent_publication_sha256': sha(parent), 'manifest_sha256': manifest_sha,
        'publication_script_sha256': sha(R / 'apply_reviewed_status.py'),
        'qualified_stage_preserve_replace_backup_interruption_body_reused': True,
        'new_scope': 'Two existing JSON paths; native identity includes full-mode normalization to same qualified file_identity representation',
        'Source_application': False}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'publisher_sha256': sha(R / 'apply_reviewed_status.py'), 'manifest_sha256': manifest_sha}))
