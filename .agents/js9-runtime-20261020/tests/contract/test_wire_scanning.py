"""Semantic regression vectors for bounded structural and lowercase-hex scans."""
from pathlib import Path
import itertools
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from ceta.contracts import wire
from ceta.contracts.editor_recovery import (
    _hex_bytes, decode_editor_payload, editor_payload_chunk_wires, editor_payload_wire)
from ceta.contracts.task_drafts import command_wire, decode_command, text_value
from ceta.contracts.task_meaning import MEANING_FIELDS
from ceta.contracts.wire import ContractError, MAX_DEPTH, MAX_WIRE_BYTES, canonical_bytes, strict_loads


def retained_preflight(text):
    """Copied prior scanner oracle; its source lines receive no authored credit."""
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise ContractError("DEPTH_LIMIT")
        elif char in "]}":
            depth -= 1


def outcome(call, value):
    try:
        return ('returned', call(value))
    except ContractError as error:
        return ('rejected', error.code, error.path)


class WireScanningTests(unittest.TestCase):
    def test_structural_depth_matches_retained_scanner_for_escape_and_delimiter_vectors(self):
        alphabet = ('"', '\\', '[', ']', '{', '}', 'x')
        for length in range(6):
            for values in itertools.product(alphabet, repeat=length):
                text = ''.join(values)
                for candidate in (text, '[' * 31 + text + ']' * 31):
                    self.assertEqual(outcome(wire._preflight, candidate),
                                     outcome(retained_preflight, candidate), repr(candidate))

    def test_public_strict_values_and_rejections_match_prior_scanner(self):
        values = [None, False, True, 0, -(2**63), 2**63 - 1,
                  '"\\[{}]🙂', {'quoted"key': ['\\', '[', ']', {'x': 'Cafe\u0301'}]}]
        vectors = [json.dumps(value, ensure_ascii=True).encode() for value in values]
        vectors += [b'{"a":1,"a":2}', b'{"a":{"b":0,"b":1}}', b'1e2', b'0.5',
                    b'NaN', b'"\\ud800"', b'"e\\u0301"', b'"\\q"', b'"x\n"', b'"\xff"',
                    b'\\"[[[', b'{"a":}', b'[]{}', b'', b'[1,]', str(2**63).encode()]
        for wire_value in vectors:
            with self.subTest(wire=wire_value):
                current = outcome(strict_loads, wire_value)
                with patch.object(wire, '_preflight', retained_preflight):
                    previous = outcome(strict_loads, wire_value)
                self.assertEqual(current, previous)

    def test_depth_limit_is_enforced_before_json_materialization(self):
        for prefix, suffix in (('[', ']'), ('{"a":', '}')):
            data = (prefix * (MAX_DEPTH + 1) + '0' + suffix * (MAX_DEPTH + 1)).encode()
            with self.subTest(prefix=prefix), patch.object(wire.json, 'loads',
                    side_effect=AssertionError('JSON materialization must not start')):
                with self.assertRaises(ContractError) as caught:
                    strict_loads(data)
                self.assertEqual(caught.exception.code, 'DEPTH_LIMIT')

    def test_long_quoted_brackets_and_backslash_parity_preserve_exact_strings(self):
        for backslashes in range(9):
            value = ('x' * 180000 + '\\' * backslashes + '"' + '[' * 64 + '{}' * 64 + ']')
            encoded = json.dumps(value, ensure_ascii=False).encode()
            self.assertEqual(strict_loads(encoded), value)
            self.assertLess(len(encoded), MAX_WIRE_BYTES)
            malformed = encoded[:-1]
            self.assertEqual(outcome(strict_loads, malformed),
                             ('rejected', 'MALFORMED_JSON', '$'))

    def test_editor_lowercase_hex_decodes_every_two_byte_value(self):
        for value in range(65536):
            raw = value.to_bytes(2, 'little')
            self.assertEqual(_hex_bytes(raw.hex(), 'EDITOR_TEST_HEX', 2), raw)
        self.assertEqual(_hex_bytes('', 'EDITOR_TEST_HEX', 0), b'')

    def test_editor_hex_keeps_exact_type_width_size_and_alphabet_rejections(self):
        class HostileText(str):
            def __len__(self):
                raise AssertionError('subclass hook must not run')
        rejected = [None, b'0000', True, HostileText('0000'), '000', '000000', '00000000',
                    '00FF', '00ff\n', '00 f', '００００', '00\u200b0', '00\ud8000']
        for value in rejected:
            with self.subTest(value=repr(value)), self.assertRaises(ContractError) as caught:
                _hex_bytes(value, 'EDITOR_TEST_HEX', 2)
            self.assertEqual(caught.exception.code, 'EDITOR_TEST_HEX')
        # A late invalid glyph must not be hidden by a long accepted prefix.
        with self.assertRaisesRegex(ContractError, 'EDITOR_TEST_HEX'):
            _hex_bytes('00' * 65535 + '0G', 'EDITOR_TEST_HEX', 65536)

    def test_task_utf8_text_keeps_raw_unicode_and_strict_hex_bounds(self):
        for text in ('', 'A', 'NO consent\u00a0🙂\u2028\u2029', 'Cafe\u0301', '\x00\r\n'):
            raw = text.encode('utf-8')
            self.assertEqual(text_value(raw.hex(), maximum=len(raw)), text)
            if raw:
                with self.assertRaisesRegex(ContractError, 'TASK_TEXT_ENCODING'):
                    text_value(raw.hex(), maximum=len(raw) - 1)
        for value in ('a', 'GG', 'FF', '00 ', '００', 'ed a080', 'eda080', 'ff', None, b'00'):
            with self.subTest(value=value), self.assertRaisesRegex(ContractError, 'TASK_TEXT_ENCODING'):
                text_value(value)

    @staticmethod
    def reference_command():
        documents = {name: {'utf16le_hex': '', 'document_id': 'editor-document:scan-' + name,
            'document_revision': 0, 'cursor_position': 0, 'anchor_position': 0}
            for name in MEANING_FIELDS}
        documents['scope']['utf16le_hex'] = ('x' * 65537 + '\ud800').encode(
            'utf-16-le', errors='surrogatepass').hex()
        payload = editor_payload_wire(basis_revision='sha256:' + 'a' * 64,
            widget_revision=1, documents=documents)
        decoded = decode_editor_payload(payload)
        chunks = editor_payload_chunk_wires(decoded, documents)
        assert len(chunks) == decoded['chunk_count'] == 2
        return command_wire('editor_retain', 'project:scan', 'task-command:scan',
            task_id='task:scan', editor_payload=payload, editor_expected_revision=None,
            editor_capture_commitment=decoded['capture_commitment'], editor_chunk_index=0,
            editor_chunk=chunks[0])

    def test_reference_command_keeps_canonical_bytes_and_lowercase_field_rejections(self):
        original = self.reference_command()
        decoded = decode_command(original)
        self.assertEqual(decoded.original_wire, original)
        self.assertEqual(decoded.canonical_wire, original)
        for field, code in (('editor_payload_hex', 'EDITOR_COMMAND_PAYLOAD'),
                            ('editor_chunk_hex', 'EDITOR_REFERENCE_COMMAND')):
            invalid = strict_loads(original)
            invalid[field] = invalid[field].upper()
            self.assertNotEqual(invalid[field], strict_loads(original)[field])
            with self.subTest(field=field), self.assertRaises(ContractError) as caught:
                decode_command(canonical_bytes(invalid))
            self.assertEqual(caught.exception.code, code)

    def test_wire_size_and_input_type_reject_before_structural_scan(self):
        with patch.object(wire, '_preflight', side_effect=AssertionError('scan must not start')):
            for value, code in ((b' ' * (MAX_WIRE_BYTES + 1), 'WIRE_SIZE_LIMIT'),
                                ('{}', 'WIRE_MUST_BE_BYTES'), (bytearray(b'{}'), 'WIRE_MUST_BE_BYTES')):
                with self.subTest(code=code), self.assertRaises(ContractError) as caught:
                    strict_loads(value)
                self.assertEqual(caught.exception.code, code)


if __name__ == '__main__':
    unittest.main()
