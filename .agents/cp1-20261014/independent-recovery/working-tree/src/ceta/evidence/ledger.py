# Subsystem 17 evidence ledger: append-only hash-chained JSON lines, standard library only.
# Tamper evidence within a stated trust model. A rewrite that recomputes every hash is not detected unless the head is anchored externally (B-09).
import hashlib
import json
import os
GENESIS = '0' * 64
MAX_RECORDS = 100000
MAX_PAYLOAD_BYTES = 65536
NEWLINE = bytes([10])
class LedgerError(Exception):
    def __init__(self, code, detail=''):
        super().__init__(code + ': ' + detail)
        self.code = code
        self.detail = detail
def _reject_constant(name):
    raise ValueError('non-finite number not allowed: ' + name)
def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
def record_hash(index, prev, payload):
    return hashlib.sha256(canonical({'index': index, 'prev': prev, 'payload': payload})).hexdigest()
def _result(ok, first_broken, code, head, count, anchored):
    return {'ok': ok, 'first_broken_index': first_broken, 'code': code, 'head': head, 'count': count, 'anchored': anchored}
def verify_lines(lines, expected_head=None):
    prev = GENESIS
    count = 0
    for position, line in enumerate(lines):
        try:
            rec = json.loads(line, parse_constant=_reject_constant)
            shape_ok = isinstance(rec, dict) and set(rec) == {'index', 'prev', 'payload', 'hash'} and isinstance(rec['payload'], dict) and isinstance(rec['hash'], str)
            if not shape_ok:
                return _result(False, position, 'malformed', prev, count, False)
            if not (type(rec['index']) is int and rec['index'] == position):
                return _result(False, position, 'index_mismatch', prev, count, False)
            if not (rec['prev'] == prev):
                return _result(False, position, 'chain_break', prev, count, False)
            expected = record_hash(rec['index'], rec['prev'], rec['payload'])
        except (ValueError, TypeError):
            return _result(False, position, 'malformed', prev, count, False)
        if not (expected == rec['hash']):
            return _result(False, position, 'digest_mismatch', prev, count, False)
        prev = rec['hash']
        count += 1
    if count > MAX_RECORDS:
        return _result(False, MAX_RECORDS, 'bounds', prev, count, False)
    if expected_head is None:
        return _result(True, None, 'unanchored', prev, count, False)
    if not (prev == expected_head):
        return _result(False, count, 'head_mismatch', prev, count, True)
    return _result(True, None, 'ok', prev, count, True)
class Ledger:
    def __init__(self, path, expected_head=None):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        result = verify_lines(self._read_lines(), expected_head)
        if not result['ok']:
            raise LedgerError(result['code'], 'first broken index ' + str(result['first_broken_index']))
        self.head = result['head']
        self.count = result['count']
        self.anchored = result['anchored']
    def _read_lines(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, 'rb') as fh:
            data = fh.read()
        parts = data.split(NEWLINE)
        if parts and parts[-1] == b'':
            parts.pop()
        return [p.decode('ascii', 'replace') for p in parts]
    def verify(self, expected_head=None):
        return verify_lines(self._read_lines(), expected_head)
    def append(self, payload):
        if not isinstance(payload, dict):
            raise LedgerError('malformed', 'payload must be an object')
        if self.count >= MAX_RECORDS:
            raise LedgerError('bounds', 'ledger is full')
        try:
            encoded = canonical(payload)
        except (ValueError, TypeError) as exc:
            raise LedgerError('malformed', str(exc))
        if len(encoded) > MAX_PAYLOAD_BYTES:
            raise LedgerError('bounds', 'payload exceeds byte limit')
        index = self.count
        digest = record_hash(index, self.head, payload)
        line = canonical({'index': index, 'prev': self.head, 'payload': payload, 'hash': digest}) + NEWLINE
        with open(self.path, 'ab') as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        self.head = digest
        self.count = index + 1
        return digest
