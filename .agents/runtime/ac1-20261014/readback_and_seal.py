"""Read actual released author state and seal only the completed AC1 author cut."""
from ac_support import *

response = invoke(['run', 'status', RUN], 'author-final-status')
assert response['states']['discover'] == response['states']['plan'] == response['states']['implement'] == 'SUCCEEDED'
assert response['states']['review'] == 'READY' and response['sequence'] == 7
claims = json.loads((R / RUN / 'claims.json').read_text())
assert claims == {}
submitted = json.loads((R / 'implement.json').read_text())
persisted_path = R / RUN / 'receipts/implement.json'
persisted = json.loads(persisted_path.read_text())
assert len(submitted) == 13
assert {key: persisted[key] for key in submitted} == submitted
assert submitted['result']['isolation_qualified'] is False
assert submitted['result']['activation_ready'] is False
assert sha(Q / 'TRANSFER-MANIFEST.json') == submitted['result']['manifest_sha256']
readback = {'observed_at': utc(), 'run_id': RUN, 'actor': ACTOR,
            'actual_status': reference(R / 'author-final-status.json'),
            'sequence': response['sequence'], 'states': response['states'], 'claims': claims,
            'strict_submitted_receipt': reference(R / 'implement.json'),
            'persisted_receipt': reference(persisted_path),
            'strict_13_field_equality': True,
            'engine_receipt_hash': response['nodes']['implement']['receipt_hash'],
            'manifest': reference(Q / 'TRANSFER-MANIFEST.json'),
            'author_released': True, 'review_ready': True,
            'isolation_qualified': False, 'activation_ready': False,
            'qualification': 'Implementation completion is scoped to the complete fail-closed candidate; native positive isolation, independent review and Source integration remain unaccepted.'}
write_new(R / 'AUTHOR-READBACK.json', readback)

def inventory(root, skip):
    result = {}
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = directory / entry.name
                relative = path.relative_to(root).as_posix()
                if skip(relative):
                    continue
                info = fs.lstat(path)
                assert not fs.reparse(info), path
                if stat.S_ISDIR(info.st_mode):
                    pending.append(path)
                elif stat.S_ISREG(info.st_mode):
                    result[relative] = ordinary(path)
                else:
                    raise AssertionError('Nonordinary author member')
    return dict(sorted(result.items()))

q_members = inventory(Q, lambda _: False)
r_members = inventory(R, lambda relative: relative == RUN or relative.startswith(RUN + '/')
                      or relative == 'independent-review' or relative.startswith('independent-review/')
                      or relative == 'root-integration' or relative.startswith('root-integration/')
                      or relative == 'AUTHOR-SEAL.json')
seal = {'sealed_at': utc(), 'author': ACTOR, 'run_id': RUN,
        'decision': 'FROZEN_AUTHOR_HANDOFF_REVIEW_READY',
        'candidate_root': str(Q), 'runtime_root': str(R),
        'manifest': reference(Q / 'TRANSFER-MANIFEST.json'),
        'readback': reference(R / 'AUTHOR-READBACK.json'),
        'candidate_members': q_members, 'author_evidence_members': r_members,
        'excluded': ['Mutable lifecycle engine run directory', 'Later separately owned independent-review',
                     'Later separately owned root-integration', 'This self-referential seal'],
        'author_claim_released': True,
        'active_source_modified_by_author': False,
        'positive_native_isolation_accepted': False,
        'profile_create_delete': False,
        'sealed_candidate_member_count': len(q_members), 'sealed_author_evidence_member_count': len(r_members)}
write_new(R / 'AUTHOR-SEAL.json', seal)
print(json.dumps({'manifest': seal['manifest'], 'implement': readback['strict_submitted_receipt'],
                  'readback': seal['readback'], 'seal': reference(R / 'AUTHOR-SEAL.json'),
                  'profile_proposal': reference(R / 'PROFILE-CREATION-PROPOSAL.json'),
                  'states': readback['states'], 'sequence': readback['sequence'], 'claims': claims,
                  'candidate_members': len(q_members), 'author_evidence_members': len(r_members)}, indent=2), flush=True)
