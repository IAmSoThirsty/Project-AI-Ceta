"""Compile the two complete local source documents into the canonical inventory.

Fails closed on missing IDs, duplicate IDs, malformed records, or source drift.
Runtime does not require this script; it ships reproducible JSONL resources.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from societal_reasoning.ingest import import_markdown, write_jsonl
from societal_reasoning.merge import merge_concepts
from societal_reasoning.models import Concept


def compile_corpus(*, write: bool) -> dict:
    out = ROOT / 'src' / 'societal_reasoning' / 'resources'
    result = []
    volumes = []
    for volume, start, end in ((1, 1, 1000), (2, 1001, 2000)):
        source = ROOT / 'knowledge' / f'volume-{volume:02}-full.md'
        contents = source.read_text(encoding='utf-8')
        entries, report = import_markdown(
            contents, volume=volume, source_title=source.name,
            expected_start=start, expected_end=end, require_contiguous=True,
        )
        if len(entries) != 1000 or sorted(e.id for e in entries) != list(range(start, end+1)):
            raise ValueError(f'Volume {volume} source incomplete')
        dest = out / f'concepts.volume-{volume:02}.full.jsonl'
        if write:
            write_jsonl(entries, dest)
        else:
            if not dest.is_file():
                raise ValueError(f'Missing compiled resource: {dest}')
            existing = [Concept.from_dict(json.loads(line)) for line in dest.read_text(encoding='utf-8').splitlines() if line.strip()]
            if [i.to_dict() for i in entries] != [i.to_dict() for i in existing]:
                raise ValueError(f'Drift in compiled volume {volume}: {dest}')
        result.append(entries)
        volumes.append({
            'volume': volume, 'source_title': source.name, 'source_sha256': report['source_sha256'],
            'entries': report['imported'], 'first': start, 'last': end,
        })
    combined, report = merge_concepts(result)
    if report['merged_count'] != 2000 or report['source_transcribed_count'] != 2000:
        raise ValueError(f'Incomplete canonical inventory: {report}')
    canonical = out / 'concepts.full.jsonl'
    if write:
        write_jsonl(combined, canonical)
    else:
        if not canonical.is_file():
            raise ValueError(f'Missing canonical resource: {canonical}')
        existing = [Concept.from_dict(json.loads(line)) for line in canonical.read_text(encoding='utf-8').splitlines() if line.strip()]
        if [i.to_dict() for i in combined] != [i.to_dict() for i in existing]:
            raise ValueError('Canonical inventory differs from source-compiled records')
    return {
        'inventory_status': '2000_source_transcribed_not_independently_fact_verified',
        'included': len(combined), 'missing_ids': [], 'conflicts': [],
        'volumes': volumes, 'destination': canonical.relative_to(ROOT).as_posix(),
    }


if __name__ == '__main__':
    write = len(sys.argv) == 2 and sys.argv[1] == '--write'
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and not write):
        raise SystemExit('Usage: python scripts/compile_inventory.py [--write]')
    print(json.dumps(compile_corpus(write=write), indent=2, sort_keys=True))
