"""Independent standard-library verification of a Version-1 distribution ZIP."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def validate(archive: Path) -> dict:
    if archive.name != 'Societal-Reasoning-Core-v1.zip':
        raise ValueError('Incorrect filename: expected the owner-fixed Version 1 ZIP')
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        names = [m.filename for m in members]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate paths in ZIP')
        prefix = 'Societal-Reasoning-Core/'
        for m in members:
            path = PurePosixPath(m.filename)
            if not m.filename.startswith(prefix) or path.is_absolute() or '..' in path.parts or m.is_dir():
                raise ValueError(f'Unsafe member path {m.filename!r}')
            if (m.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f'Symlink in archive: {m.filename}')
        stored = {name[len(prefix):]: z.read(name) for name in names}
    if stored.get('manifest.json') is None or stored.get('SHA256SUMS') is None:
        raise ValueError('Missing integrity metadata')
    manifest = json.loads(stored['manifest.json'])
    if manifest['version'] != '1' or manifest['archive_name'] != archive.name:
        raise ValueError('Manifest version mismatch')
    file_entries = manifest.get('files', [])
    file_map = {row['path']: row for row in file_entries}
    payloads = set(stored) - {'SHA256SUMS', 'manifest.json'}
    if len(file_map) != len(file_entries) or set(file_map) != payloads:
        raise ValueError('Manifest paths do not exactly match archive paths')
    for name, row in file_map.items():
        if sha(stored[name]) != row['sha256'] or len(stored[name]) != row['bytes']:
            raise ValueError(f'Content hash/size mismatch: {name}')
    checksum_rows = [line.split('  ', 1) for line in stored['SHA256SUMS'].decode('utf-8').splitlines()]
    if any(len(row) != 2 for row in checksum_rows):
        raise ValueError('Malformed SHA256SUMS')
    expected = {name: digest for digest, name in checksum_rows}
    if len(expected) != len(checksum_rows) or set(expected) != (set(stored) - {'SHA256SUMS'}):
        raise ValueError('SHA256SUMS must contain exactly the other archive files')
    for name, digest in expected.items():
        if sha(stored[name]) != digest:
            raise ValueError(f'SHA256SUMS mismatch: {name}')
    source_prefix = 'src/societal_reasoning/resources/'
    records = [json.loads(s) for s in stored[source_prefix + 'concepts.full.jsonl'].splitlines() if s]
    ids = [x['id'] for x in records]
    if ids != list(range(1, 2001)):
        raise ValueError('Canonical inventory missing, duplicated, or reordered')
    for volume in (1, 2):
        path = f'knowledge/volume-{volume:02}-full.md'
        expected_hash = sha(stored[path])
        records_in_volume = [x for x in records if x['source']['volume'] == volume]
        if len(records_in_volume) != 1000:
            raise ValueError(f'Incomplete volume {volume}')
        for record in records_in_volume:
            if record['source']['source_sha256'] != expected_hash:
                raise ValueError(f'Source hash mismatch at {record["id"]}')
            if record['source']['entry_sha256'] != sha(record['original_text'].encode('utf-8')):
                raise ValueError(f'Entry hash mismatch at {record["id"]}')
            if record['status'] != 'source_transcribed' or not record['summary'].strip():
                raise ValueError(f'Unverified/missing source text at {record["id"]}')
    sidecar = archive.parent / (archive.name + '.sha256')
    if sidecar.exists():
        want = sidecar.read_text(encoding='utf-8').strip()
        if want != f'{sha(archive.read_bytes())}  {archive.name}':
            raise ValueError('Outer ZIP checksum does not match sidecar')
    return {
        'version': '1', 'sha256': sha(archive.read_bytes()),
        'unique_entries': len(records), 'missing_ids': 0,
        'source_volume_counts': [1000, 1000],
        'files_integrity_verified': len(stored),
        'status': 'SOURCE_PACKAGE_VERIFIED_NOT_FACTUALLY_CERTIFIED',
    }


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python scripts/verify_release.py /path/to/Societal-Reasoning-Core-v1.zip')
    print(json.dumps(validate(Path(sys.argv[1])), indent=2, sort_keys=True))
