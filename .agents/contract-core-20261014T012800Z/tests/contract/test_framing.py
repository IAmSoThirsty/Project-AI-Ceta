"""Hostile framing inputs and exact record preservation; no real IPC claims."""
import copy
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts import (ContractError, RecordCodec, canonical_bytes,
                            decode_frame_length, decode_record_frame, frame_record, strict_loads)
from ceta.contracts.wire import MAX_WIRE_BYTES
from test_all_records import example


class FramingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())
        cls.codec = RecordCodec(cls.schema)
        cls.observation = strict_loads((ROOT / "contracts/examples/observation_shape_valid.json").read_bytes())["instance"]

    def reject(self, call, code):
        with self.assertRaises(ContractError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def test_header_unsigned_network_order_known_vectors_and_maximum(self):
        for header, size in ((b"\x00\x00\x00\x01", 1), (b"\x00\x00\x01\x00", 256),
                             (b"\x00\x01\x00\x00", 65536), (b"\x00\x10\x00\x00", MAX_WIRE_BYTES)):
            with self.subTest(size=size):
                self.assertEqual(decode_frame_length(header), size)

    def test_header_has_exactly_four_bytes(self):
        for length in (0,1,2,3,5,8):
            with self.subTest(length=length):
                self.reject(lambda: decode_frame_length(b"\x01"*length), "IPC_HEADER_SIZE")

    def test_header_rejects_mutable_or_coercible_inputs(self):
        for value in (bytearray(b"\x00\x00\x00\x01"), memoryview(b"1234"), "1234", 4, None):
            with self.subTest(value=type(value).__name__):
                self.reject(lambda: decode_frame_length(value), "IPC_HEADER_MUST_BE_BYTES")

    def test_zero_and_oversized_declarations_reject_without_body_or_parser(self):
        for size in (0, MAX_WIRE_BYTES+1, 2**31, 2**32-1):
            with self.subTest(size=size), patch.object(self.codec, "decode") as parser:
                self.reject(lambda: decode_record_frame(struct.pack(">I",size),self.codec), "IPC_BODY_SIZE_LIMIT")
                parser.assert_not_called()

    def test_missing_header_rejects_before_record_parser(self):
        with patch.object(self.codec,"decode") as parser:
            self.reject(lambda: decode_record_frame(b"\x00\x00\x00",self.codec), "IPC_HEADER_SIZE")
            parser.assert_not_called()

    def test_body_length_mismatch_truncation_trailing_and_concatenation(self):
        body = canonical_bytes(self.observation)
        complete = struct.pack(">I",len(body))+body
        for frame in (complete[:-1], complete+b" ", complete+complete,
                      struct.pack(">I",len(body)+1)+body):
            with self.subTest(length=len(frame)), patch.object(self.codec,"decode") as parser:
                self.reject(lambda: decode_record_frame(frame,self.codec), "IPC_FRAME_LENGTH")
                parser.assert_not_called()

    def test_complete_buffer_size_rejected_before_slicing_or_parsing(self):
        with patch.object(self.codec,"decode") as parser:
            self.reject(lambda: decode_record_frame(b"x"*(MAX_WIRE_BYTES+5),self.codec), "IPC_FRAME_SIZE_LIMIT")
            parser.assert_not_called()

    def test_encoder_empty_and_oversized_body_rejected_before_parsing(self):
        for body in (b"",b"x"*(MAX_WIRE_BYTES+1)):
            with patch.object(self.codec,"decode") as parser:
                self.reject(lambda: frame_record(body,self.codec), "IPC_BODY_SIZE_LIMIT")
                parser.assert_not_called()

    def test_frame_and_encoder_require_immutable_bytes(self):
        for value in (bytearray(b"abcd"),memoryview(b"abcd"),"abcd",4,None):
            with self.subTest(value=type(value).__name__):
                self.reject(lambda: decode_record_frame(value,self.codec), "IPC_FRAME_MUST_BE_BYTES")
                self.reject(lambda: frame_record(value,self.codec), "WIRE_MUST_BE_BYTES")

    def test_original_bytes_and_record_commitment_survive_round_trip(self):
        body = json.dumps(self.observation,indent=2).replace("\n","\r\n").encode("utf-8")+b"\r\n"
        original = self.codec.decode(body)
        frame = frame_record(body,self.codec)
        self.assertEqual(frame[:4],struct.pack(">I",len(body)))
        self.assertEqual(frame[4:],body)
        decoded = decode_record_frame(frame,self.codec)
        self.assertEqual(decoded,original)
        self.assertNotEqual(decoded.original_wire,decoded.canonical_wire)

    def test_twenty_existing_record_types_cross_framing_without_new_schema(self):
        for name, shape in self.schema["$defs"].items():
            with self.subTest(record=name):
                body = canonical_bytes(example(shape))
                frame = struct.pack(">I",len(body))+body
                result = decode_record_frame(frame,self.codec)
                self.assertEqual(result.record_type,name)
                self.assertEqual(frame_record(body,self.codec),frame)

    def test_duplicate_keys_invalid_utf8_and_fractional_values_stay_rejected(self):
        for body, code in ((b'{"record_type":"ObservationEnvelope","record_type":"OperationPermit"}',"DUPLICATE_KEY"),
                           (b'"\xff"',"MALFORMED_JSON"),(b"0.5","NON_INTEGER_NUMBER")):
            with self.subTest(code=code):
                frame = struct.pack(">I",len(body))+body
                self.reject(lambda: decode_record_frame(frame,self.codec),code)
                self.reject(lambda: frame_record(body,self.codec),code)

    def test_framing_cannot_hide_unknown_record_or_authority_field(self):
        changed = copy.deepcopy(self.observation)
        changed["owner_says_allow"] = True
        for body, code in ((b'{"record_type":"InventedPermit"}',"UNKNOWN_RECORD_TYPE"),
                           (canonical_bytes(changed),"UNKNOWN_FIELD")):
            with self.subTest(code=code):
                self.reject(lambda: decode_record_frame(struct.pack(">I",len(body))+body,self.codec),code)
                self.reject(lambda: frame_record(body,self.codec),code)


if __name__ == "__main__":
    unittest.main()
