"""Count actual published physical line deltas; dependency copies receive no credit."""
from pathlib import Path
import difflib
import hashlib
import json
import phase_coordinator as c

p = c.bound_packet()
publication = c.D / 'publication'
terminal = json.loads((publication / 'RESULT.json').read_bytes())
assert terminal['exit_status'] == 0 and terminal['status'] == 'PUBLISHED_PENDING_DESTINATION_VERIFICATION'
prepared = json.loads((publication / 'PREPARED.json').read_bytes())
rows = []
totals = {key:dict(added=0, removed=0, net=0, files=0) for key in ('source', 'test', 'contract')}
for item in prepared['staged']:
    name = item['path']
    raw = (c.F / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == item['candidate_sha256']
    before = b'' if item['before'] is None else (publication / 'before' / (name + '.source')).read_bytes()
    assert item['before'] is None or hashlib.sha256(before).hexdigest() == item['before']['sha256']
    old, new = before.decode('utf-8').splitlines(), raw.decode('utf-8').splitlines()
    added = removed = 0
    for tag, a, b, x, y in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag in ('insert', 'replace'):
            added += y-x
        if tag in ('delete', 'replace'):
            removed += b-a
    category = 'test' if name.startswith('tests/') else 'contract' if name.startswith('contracts/') else 'source'
    rows.append(dict(path=name, category=category, added=added, removed=removed, net=added-removed,
        before_sha256=None if item['before'] is None else item['before']['sha256'],
        destination_sha256=item['candidate_sha256']))
    for key, amount in (('added', added), ('removed', removed), ('net', added-removed), ('files', 1)):
        totals[category][key] += amount
assert sorted(row['path'] for row in rows) == sorted(p['application_paths'])
report = dict(packet_sha256=hashlib.sha256((c.D/'PACKET.json').read_bytes()).hexdigest(),
    publication_sha256=hashlib.sha256((publication/'RESULT.json').read_bytes()).hexdigest(),
    measurement='Physical line insertions/removals including comments and blank lines; not executable-statement count',
    interval='Reviewed Source31 destination before-images to actual published destination',
    newly_authored_this_turn_not_inferred=True, copied_dependency_LOC_credit=0,
    totals=totals, paths=rows, Source_accepted=False, product_acceptance=False)
c.save(c.R/'PUBLICATION-LINE-DELTA.json', report)
print(json.dumps(dict(totals=totals, copied_dependency_LOC_credit=0, Source_accepted=False)))
