"""Read-only conservation and integrity gate; no product-acceptance inference."""
from pathlib import Path, PurePosixPath
import json
import zipfile
from prepare_checkpoint import checkout_state, digest, git, stable_read, verify

W = Path(__file__).resolve().parent
F = Path('T:/00-Active/Project-AI-CETA')


def audit():
    p = json.loads((W / 'prepared-0001/PREPARED.json').read_bytes())
    result = verify(W / 'prepared-0001/PREPARED.json')
    assert p['parent'] == 'c7bcf2bfc0b6e6085d39967d4559a97c705411ec'
    before = json.loads((W / 'CANONICAL-BEFORE.json').read_bytes())
    assert checkout_state(F) == before['checkout']
    assert stable_read(F / '.git/index')[1] == before['normal_index_native']
    assert all(stable_read(F / rel)[1] == pin for rel,pin in before['canonical_pins'].items())
    def tree(commit):
        entries = {}
        for row in git(F, ['ls-tree', '-r', '-z', commit], env=p['git_environment']).split(b'\0'):
            if row:
                header, name = row.split(b'\t', 1); entries[name.decode()] = header.decode().split()
        return entries
    parent = tree(p['parent']); child = tree(p['commit'])
    changed_existing = sorted(n for n in parent if parent[n] != child.get(n))
    assert changed_existing == ['DEVELOPMENT-CHECKPOINT.json', 'DEVELOPMENT-CHECKPOINT.md']
    assert set(parent) <= set(child)
    assert all(parent[n][0] == child[n][0] for n in parent)
    status = json.loads((W / 'public/STATUS.json').read_bytes())
    fixtures = status['preserved_registry_fixtures']
    assert len(fixtures) == 5 and all(parent[n] == child[n] for n in fixtures)
    assert sorted(n for n in child if n.startswith('.local-build-cache/')) == sorted(fixtures)
    pdf = [n for n in parent if 'pdf' in n.casefold()]
    assert pdf and all(parent[n] == child[n] for n in pdf)
    assert not any('oversized' in n.casefold() for n in set(child) - set(parent))
    manifest = json.loads((W / 'SOURCE-MANIFEST.json').read_bytes())
    assert manifest['payload_count'] == len(manifest['payload_hashes']) == 559
    assert set(manifest['payload_hashes']) == set(before['canonical_pins'])
    for rel, pin in manifest['payload_hashes'].items():
        assert before['canonical_pins'][rel]['sha256'] == pin
        raw = stable_read(F / rel)[0]
        if rel.endswith('.py'): compile(raw, rel, 'exec')
    transport = json.loads((W / 'public/TRANSPORT.json').read_bytes())
    archive = W / 'public/REVIEWED-CANDIDATE-AND-EVIDENCE.zip'
    assert digest(archive.read_bytes()) == transport['archive_sha256']
    with zipfile.ZipFile(archive) as z:
        assert z.namelist() == [v['member'] for v in transport['members']]
        assert z.testzip() is None
        for member, info in zip(transport['members'], z.infolist(), strict=True):
            n = info.filename
            assert not n.startswith('/') and '..' not in PurePosixPath(n).parts and ':' not in n and '\\' not in n
            assert info.compress_type == zipfile.ZIP_STORED and info.date_time == (1980, 1, 1, 0, 0, 0)
            raw, pin = stable_read(member['source'])
            assert digest(raw) == member['sha256'] and len(raw) == member['bytes'] and z.read(n) == raw
        candidate_prefix = 'journal-read-budget-candidate/source/'
        assert sum(n.startswith(candidate_prefix) for n in z.namelist()) == 560
        assert sum(n.startswith(candidate_prefix + '.local-build-cache/') for n in z.namelist()) == 5
    for name in ('public/RAW-SECRET-SCAN.json', 'prepared-0001/EXACT-EXPORT-SECRET-SCAN.json'):
        scan = json.loads((W / name).read_bytes()); assert not scan['findings'] and scan['result'] == 'PASS'
    assert status['preserved_candidate']['canonical_promoted'] is False and status['full_product_acceptance'] is False
    assert status['latest_test_state']['joined_successor638'] == dict(failures=5, errors=2, passed=False)
    assert status['latest_test_state']['fixture_runner_review']['decision'] == 'rejected'
    if (W / 'WORK-FREEZE.json').exists():
        freeze = json.loads((W / 'WORK-FREEZE.json').read_bytes())
        actual = {v.relative_to(W).as_posix():digest(stable_read(v)[0]) for v in W.rglob('*')
            if v.is_file() and v != W / 'WORK-FREEZE.json'}
        assert actual == freeze['hashes'], 'Frozen preparation changed'
    return dict(status='PASS', commit=p['commit'], tree=p['tree'], parent=p['parent'], parent_paths=len(parent),
        changed_existing=changed_existing, new_paths=len(set(child)-set(parent)), canonical_payloads=559,
        candidate_payloads=560, archive_members=len(transport['members']), parent_modes_fixtures_pdf_preserved=True,
        normal_checkout_native_index_source_preserved=True, product_acceptance=False, generic=result)


if __name__ == '__main__': print(json.dumps(audit(), indent=2))
