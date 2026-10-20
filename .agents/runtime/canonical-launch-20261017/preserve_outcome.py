"""Verify the actual launch's durable task records on an exact retained copy."""
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import asdict
import hashlib
import json
import sys

ROOT = Path('T:/00-Active/Project-AI-CETA')
OUT = Path(__file__).resolve().parent / 'attempt1'
PROFILE = ROOT / '.agents/fixtures/operator-24/9811f4262bad42428905b3178f0755e7'
sys.path.insert(0, str(ROOT / 'src'))
from ceta.contracts.wire import RecordCodec, strict_loads
from ceta.contracts.store_transactions import STORE_PROFILE
from ceta.store.journal import SqliteJournal

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def write(name, value):
    with (OUT / name).open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')

def facts(path):
    raw = path.read_bytes()
    info = path.stat()
    return dict(path=str(path), bytes=len(raw), sha256=digest(raw), inode=info.st_ino,
                device=info.st_dev, mtime_ns=info.st_mtime_ns)

exit_record = strict_loads((OUT / 'EXIT.json').read_bytes())
assert exit_record['exit_status'] == 0 and exit_record['source_unchanged'] is True
assert exit_record['profiles_created'] == [PROFILE.name]
custody_path = PROFILE / '.ceta-launcher-shutdown-custody-v1.json'
custody = strict_loads(custody_path.read_bytes())
assert custody['state'] == custody['publication_state'] == 'SETTLEMENT_OBSERVED'
copy = OUT / 'retained-profile'
copy.mkdir(exist_ok=False)
files = [p for p in PROFILE.rglob('*') if p.is_file()]
before = {str(p.relative_to(PROFILE)): facts(p) for p in files}
for name, expected in before.items():
    origin = PROFILE / name
    target = copy / name
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = origin.read_bytes()
    assert digest(raw) == expected['sha256']
    with target.open('xb') as stream:
        assert stream.write(raw) == len(raw)
write('PROFILE-COPY.json', dict(original_root=str(PROFILE), copy_root=str(copy), originals=before))

codec = RecordCodec(strict_loads((ROOT / 'contracts/schemas/records.schema.json').read_bytes()))
journal = SqliteJournal(copy, codec, ('installation:operator-development', 'project:operator-development'),
                        profile=STORE_PROFILE, read_only=True)
connection = journal._connection
try:
    positions = [asdict(p) for p in journal.validate()]
    records = []
    for point in positions:
        for entry in journal.replay(point['scope_id']):
            event = codec.decode(entry.event_wire)
            payload = codec.decode(entry.payload_wire)
            records.append(dict(scope_id=point['scope_id'], event=event.as_dict(),
                event_sha256=digest(entry.event_wire), payload=payload.as_dict(),
                payload_sha256=digest(entry.payload_wire)))
    cells = [dict(collection=row[0], scope_id=row[1], record_id=row[2], generation=row[3],
                  value=None if row[4] is None else strict_loads(row[4]), revision=row[5])
             for row in connection.execute('SELECT collection,scope_id,record_id,generation,value_wire,revision FROM store_cells ORDER BY collection,scope_id,record_id')]
finally:
    journal.close()
closed = False
try:
    connection.execute('SELECT 1')
except journal._sqlite.ProgrammingError as error:
    closed = str(error) == 'Cannot operate on a closed database.'
assert closed
assert before == {str(p.relative_to(PROFILE)): facts(p) for p in files}
responses = []
for path in sorted((copy / 'controller-4e37b7a7ae004db99bd6a21826427631/requests').glob('*.response.json')):
    response = strict_loads(path.read_bytes())
    request_path = path.with_name(path.name.replace('.response.json', '.request.json'))
    request_raw = request_path.read_bytes()
    assert digest(request_raw) == response['request_sha256']
    responses.append(dict(request_sha256=digest(request_raw), response_sha256=digest(path.read_bytes()),
        request=str(request_path.relative_to(OUT)), response=str(path.relative_to(OUT)),
        operation=response['operation'], kind=response['kind'], error_code=response['error_code']))
write('DURABLE-RECORDS.json', dict(at=datetime.now(timezone.utc).isoformat(),
    original_profile_unchanged=True, read_only_copy_validated=True, verifier_connection_closed=closed,
    positions=positions, events=records, cells=cells, transport_receipts=responses, shutdown_custody=custody))
print(json.dumps(dict(read_only_copy_validated=True, event_count=len(records),
    cell_count=len(cells), responses=responses, source_unchanged=True)), flush=True)
