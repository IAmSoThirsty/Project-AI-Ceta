"""Independent archive verification of the admitted portion of HP1 only."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import zipfile

S = Path(__file__).resolve().parents[3]
Q = S / '.agents/hp1-20261014/checkpoint'
OUT = S / '.agents/runtime/hp1-root-review-20261014'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

assert not OUT.exists()
started = datetime.now(timezone.utc).isoformat()
assert sha(Q / 'checkpoint.json') == '41f0da0d4193cf8f496c9b83aa5c0969285ca320cb8f8c01113933ef65125502'
manifest = read(Q / 'checkpoint.json')
assert manifest['complete'] is False and len(manifest['pending']) == 69
assert sha(Q / 'inventory.json') == '1a4ef31c90121750d4730e55edfb2afa781df25e30b6dbb76ae9f6517c679b3f'
assert (Q / 'COMMITTED').read_text().strip() == sha(Q / 'checkpoint.json')
inventory = read(Q / 'inventory.json')
artifacts = []
for artifact in manifest['artifacts']:
    path = Q / artifact['path']
    assert path.stat().st_size == artifact['bytes'] and sha(path) == artifact['sha256']
    artifacts.append(artifact)

def verify_zip(path, entries):
    expected = {item['path']: item for item in entries if item['kind'] == 'file'}
    assert len(expected) == sum(item['kind'] == 'file' for item in entries)
    total = 0
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)) and set(names) == set(expected)
        for name in names:
            record, digest, size = expected[name], hashlib.sha256(), 0
            assert archive.getinfo(name).file_size == record['bytes']
            with archive.open(name) as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(block)
                    size += len(block)
            assert size == record['bytes'] and digest.hexdigest() == record['sha256'], name
            total += size
    return {'archive': path.name, 'ordinary_members': len(expected), 'ordinary_bytes': total,
            'all_admitted_member_names_sizes_and_sha256_match': True}

working = verify_zip(Q / 'working-tree.zip', inventory['entries'])
metadata = verify_zip(Q / 'git-common-metadata.zip', inventory['git']['metadata']['common'])
assert working['ordinary_members'] == 28744 and metadata['ordinary_members'] == 54
assert working['ordinary_bytes'] == 1977186734
OUT.mkdir()
proof = {'schema_version': 1, 'executor': '/root', 'started_at': started,
    'finished_at': datetime.now(timezone.utc).isoformat(), 'source_root': inventory['source_root'],
    'checkpoint': str(Q), 'checkpoint_manifest_sha256': sha(Q / 'checkpoint.json'),
    'inventory_sha256': sha(Q / 'inventory.json'), 'COMMITTED_matches': True,
    'artifacts': artifacts, 'working_tree': working, 'inert_metadata': metadata,
    'complete': False, 'held_entries': len(manifest['pending']),
    'decision': 'ADMITTED_ARCHIVE_BYTES_MATCH_SEALED_PARTIAL_INVENTORY',
    'source_current_bytes_verified_in_this_run': False,
    'complete_restore_executed': False,
    'remaining': ['69 withheld entries remain withheld', 'Full independent restore awaits complete approved capture',
                  'Current source-byte equality beyond the frozen capture observation requires fresh source verification'],
    'source_LOC_added': 0, 'test_LOC_added': 0, 'exit_status': 0}
with (OUT / 'partial-archive-verification.json').open('x', encoding='utf-8') as output:
    json.dump(proof, output, indent=2)
    output.write('\n')
print(json.dumps({'independent_partial_archive_verification': 'PASS',
    'admitted_working_members': working['ordinary_members'], 'inert_metadata_members': metadata['ordinary_members'],
    'held': len(manifest['pending']), 'complete': False,
    'proof_sha256': sha(OUT / 'partial-archive-verification.json')}), flush=True)
