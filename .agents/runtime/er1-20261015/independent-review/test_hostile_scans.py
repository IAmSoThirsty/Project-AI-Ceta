"""Finite independent pure-leaf oracles; retained originals are uncredited."""
import ast
import hashlib
import json
import random
import sys
import unittest
from unittest.mock import patch

from review_support import F, Q, P, R, V, s, read, function
sys.path.insert(0, str(Q / 'src'))
from ceta.contracts import wire, editor_recovery, task_drafts
from ceta.contracts.local_ipc import decode_message
from ceta.contracts.wire import ContractError, RecordCodec, strict_loads, canonical_bytes

COUNTS = {}
REQUEST_PROOF = {}


def retained(path, name, globals_):
    node = function(path, name)
    namespace = dict(globals_)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


old_preflight = retained(P / 'src/ceta/contracts/wire.py', '_preflight', wire.__dict__)
old_editor_hex = retained(P / 'src/ceta/contracts/editor_recovery.py', '_hex_bytes', editor_recovery.__dict__)
old_task_text = retained(P / 'src/ceta/contracts/task_drafts.py', 'text_value', task_drafts.__dict__)


def outcome(call, *args, **kwargs):
    try:
        value = call(*args, **kwargs)
        if type(value) is bytes:
            return ('returned_bytes', len(value), hashlib.sha256(value).hexdigest())
        return ('returned_json', json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')))
    except ContractError as error:
        return ('rejected', error.code, error.path)


def previous_loads(data):
    with patch.object(wire, '_preflight', old_preflight):
        return strict_loads(data)


class HostileScanTests(unittest.TestCase):
    def test_seeded_sparse_positional_escapes_match_exact_retained_scanner(self):
        random_source = random.Random(2026101501)
        alphabet = ('"', '\\', '[', ']', '{', '}', 'x', '🙂', '\x00', '\u0301', '\n')
        count = 0
        for index in range(4096):
            text = ''.join(random_source.choice(alphabet) for _ in range(random_source.randrange(1, 129)))
            prefix = '[' * (index % 34)
            candidate = prefix + text + ']' * (index % 34)
            self.assertEqual(outcome(wire._preflight, candidate), outcome(old_preflight, candidate), repr(candidate))
            count += 1
        COUNTS[self.id()] = count

    def test_seeded_public_values_and_corruptions_preserve_typed_value_or_exact_error(self):
        random_source = random.Random(2026101502)
        atoms = (None, True, False, 0, -(2**63), 2**63 - 1, '🙂', '\\"[{]}', '\x00', 'e\u0301')
        count = 0
        for index in range(512):
            value = {'key"\\🙂': [random_source.choice(atoms) for _ in range(index % 9)],
                'nested': {'x': random_source.choice(atoms)}}
            original = json.dumps(value, ensure_ascii=True, separators=(',', ':')).encode()
            for candidate in (original, original[:-1], original + b'[]', original.replace(b':', b'::', 1)):
                self.assertEqual(outcome(strict_loads, candidate), outcome(previous_loads, candidate))
                count += 1
        COUNTS[self.id()] = count

    def test_escaped_strings_do_not_hide_depth_before_json_materialization(self):
        count = 0
        for slash_count in range(17):
            quoted = json.dumps('🙂' + '\\' * slash_count + '"' + '[' * 80 + '{}' * 80, ensure_ascii=True)
            candidate = ('{"quoted":' + quoted + ',"deep":' + '[' * 32 + '0' + ']' * 32 + '}').encode()
            self.assertEqual(outcome(wire._preflight, candidate.decode()), ('rejected', 'DEPTH_LIMIT', '$'))
            self.assertEqual(outcome(wire._preflight, candidate.decode()), outcome(old_preflight, candidate.decode()))
            with patch.object(wire.json, 'loads', side_effect=AssertionError('materialization must remain unstarted')):
                with self.assertRaises(ContractError) as caught:
                    strict_loads(candidate)
                self.assertEqual(caught.exception.code, 'DEPTH_LIMIT')
            count += 1
        COUNTS[self.id()] = count

    def test_each_bmp_character_preserves_exact_old_hex_membership_and_decode(self):
        count = 0
        for codepoint in range(65536):
            candidate = '000' + chr(codepoint)
            self.assertEqual(outcome(editor_recovery._hex_bytes, candidate, 'REVIEW_HEX', 2),
                outcome(old_editor_hex, candidate, 'REVIEW_HEX', 2), codepoint)
            self.assertEqual(outcome(task_drafts.text_value, candidate, maximum=2),
                outcome(old_task_text, candidate, maximum=2), codepoint)
            count += 2
        COUNTS[self.id()] = count

    def test_exact_one_mib_plain_and_escape_dense_wires_keep_values_and_size_guard(self):
        limit = wire.MAX_WIRE_BYTES
        values = (b'"' + b'x' * (limit - 2) + b'"', b'"' + b'\\\\' * ((limit - 2) // 2) + b'"')
        count = 0
        for candidate in values:
            self.assertEqual(len(candidate), limit)
            self.assertEqual(outcome(strict_loads, candidate), outcome(previous_loads, candidate))
            self.assertEqual(outcome(strict_loads, candidate + b' '), ('rejected', 'WIRE_SIZE_LIMIT', '$'))
            count += 2
        COUNTS[self.id()] = count

    def test_profile_unicode_integer_and_duplicate_policies_remain_exact(self):
        vectors = (b'{"a":0,"a":1}', b'{"a":{"x":true,"x":false}}', b'1.0', b'1e0', b'NaN',
            b'-Infinity', b'"\\ud800"', b'"\\udfff"', b'"e\\u0301"', b'"\xc0\xaf"', b'\xef\xbb\xbf{}',
            str(2**63).encode(), str(-(2**63)-1).encode(), b'false', b'0', b'"\\u00e9"')
        for candidate in vectors:
            self.assertEqual(outcome(strict_loads, candidate), outcome(previous_loads, candidate))
        with patch.object(wire.unicodedata, 'unidata_version', '16.0.0'):
            self.assertEqual(outcome(strict_loads, b'{}'), ('rejected', 'UNSUPPORTED_UNICODE_VERSION', '$'))
            self.assertEqual(outcome(strict_loads, b'{}'), outcome(previous_loads, b'{}'))
        COUNTS[self.id()] = len(vectors) + 2

    def test_retained_staging_request_keeps_original_wire_and_committed_identity(self):
        prior = F / '.agents/runtime/js2-20261015/direct-integration/independent-full'
        failure = read(prior / 'EDITOR-FAILURE-READBACK-R1.json')
        matches = failure['matched_failed_stimulus_requests']
        self.assertEqual(len(matches), 1)
        from pathlib import Path
        path = Path(matches[0]['request']['path'])
        before = s.ordinary(path)
        data = path.read_bytes()
        self.assertEqual(len(data), 532455)
        self.assertEqual(hashlib.sha256(data).hexdigest(), '8b2f8145bc08ca6680bc1c04ea93061f9dd28cc5abd41ea6340fc941fcdb84fd')
        codec = RecordCodec(strict_loads((Q / 'contracts/schemas/records.schema.json').read_bytes()))
        request = decode_message(data, codec)
        cells = read(prior / 'EDITOR-DB-READBACK-R1.json')['cells']
        staged = [row['value'] for row in cells if row.get('value', {}).get('state') == 'STAGING']
        self.assertEqual(len(staged), 1)
        self.assertEqual(request.original_message, data)
        self.assertEqual(request.operation, 'task.editor_retain')
        self.assertEqual(request.record.record_id, staged[0]['request_id'])
        self.assertEqual(request.record.commitment, staged[0]['request_commitment'])
        self.assertEqual(s.ordinary(path), before)
        REQUEST_PROOF.update(request=s.reference(path), native_before=before, native_after=s.ordinary(path),
            record_id=request.record.record_id, record_commitment=request.record.commitment,
            pure_shape_decode_only=True, authority_or_journal_execution=False)
        COUNTS[self.id()] = 1


if __name__ == '__main__':
    unittest.main()
