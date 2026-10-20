"""Contract rejection and identity tests; no runtime authority is substituted."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts import ContractError, RecordCodec, canonical_bytes, strict_loads
from ceta.contracts.wire import MAX_DEPTH, MAX_WIRE_BYTES, PROFILE


class WireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())
        cls.codec = RecordCodec(cls.schema)
        cls.observation = strict_loads((ROOT / "contracts/examples/observation_shape_valid.json").read_bytes())["instance"]

    def reject(self, wire, code):
        with self.assertRaises(ContractError) as caught:
            self.codec.decode(wire)
        self.assertEqual(caught.exception.code, code)

    def test_supplied_positive_and_negative_examples(self):
        for path in (ROOT / "contracts/examples").glob("*.json"):
            example = strict_loads(path.read_bytes())
            with self.subTest(path=path.name):
                if example["expected_shape"] == "ACCEPT":
                    self.codec.decode(canonical_bytes(example["instance"]))
                else:
                    with self.assertRaises(ContractError):
                        self.codec.decode(canonical_bytes(example["instance"]))

    def test_original_newlines_preserved_separately_from_canonical_bytes(self):
        compact = canonical_bytes(self.observation)
        multiline = json.dumps(self.observation, indent=2).replace("\n", "\r\n").encode() + b"\r\n"
        first, second = self.codec.decode(compact), self.codec.decode(multiline)
        self.assertEqual(first.canonical_wire, second.canonical_wire)
        self.assertEqual(first.commitment, second.commitment)
        self.assertNotEqual(first.original_sha256, second.original_sha256)
        self.assertEqual(second.original_wire, multiline)

    def test_domain_separated_commitment_known_vector(self):
        parsed = self.codec.decode(canonical_bytes(self.observation))
        prefix = ("CETA:record:" + PROFILE + ":ObservationEnvelope\0").encode()
        self.assertEqual(parsed.commitment, "sha256:" + hashlib.sha256(prefix + parsed.canonical_wire).hexdigest())
        self.assertNotEqual(parsed.commitment, parsed.original_sha256)

    def test_dictionary_order_has_no_effect_on_canonical_bytes(self):
        reversed_items = dict(reversed(list(self.observation.items())))
        self.assertEqual(canonical_bytes(self.observation), canonical_bytes(reversed_items))

    def test_decoded_copy_cannot_change_validated_record(self):
        parsed = self.codec.decode(canonical_bytes(self.observation))
        changed = parsed.as_dict()
        changed["scope_id"] = "different"
        self.assertEqual(parsed.as_dict(), self.observation)

    def test_duplicate_top_level_key(self):
        self.reject(b'{"record_type":"ObservationEnvelope","record_type":"OperationPermit"}', "DUPLICATE_KEY")

    def test_duplicate_nested_key(self):
        self.reject(b'{"nested":{"allow":false,"allow":true}}', "DUPLICATE_KEY")

    def test_nonfinite_and_fractional_numbers(self):
        for value in (b"NaN", b"Infinity", b"-Infinity", b"0.5", b"1e3"):
            with self.subTest(value=value):
                self.reject(value, "NON_INTEGER_NUMBER")

    def test_excessive_depth_rejected_before_json_materialization(self):
        self.reject(b"[" * (MAX_DEPTH + 1) + b"0" + b"]" * (MAX_DEPTH + 1), "DEPTH_LIMIT")

    def test_quoted_brackets_do_not_consume_depth(self):
        self.assertEqual(strict_loads(json.dumps("[" * 100).encode()), "[" * 100)

    def test_wire_size_bound(self):
        self.reject(b" " * (MAX_WIRE_BYTES + 1), "WIRE_SIZE_LIMIT")

    def test_non_nfc_and_lone_surrogate_rejected_without_normalization(self):
        for wire, code in ((b'"e\\u0301"', "NON_CANONICAL_UNICODE"), (b'"\\ud800"', "INVALID_UNICODE")):
            with self.subTest(code=code):
                self.reject(wire, code)

    def test_invalid_utf8(self):
        self.reject(b'"\xff"', "MALFORMED_JSON")

    def test_integer_range(self):
        self.reject(str(2**63).encode(), "INTEGER_RANGE")

    def test_unknown_record_type(self):
        self.reject(b'{"record_type":"InventedRecord"}', "UNKNOWN_RECORD_TYPE")

    def test_non_string_record_discriminator_rejected(self):
        for discriminator in ([], {}, True, None, 1):
            with self.subTest(discriminator=discriminator):
                self.reject(canonical_bytes({"record_type": discriminator}), "UNKNOWN_RECORD_TYPE")

    def test_missing_field_is_not_invented(self):
        value = copy.deepcopy(self.observation)
        del value["causation_ref"]
        self.reject(canonical_bytes(value), "MISSING_FIELD")

    def test_unknown_authority_field(self):
        value = copy.deepcopy(self.observation)
        value["allow_execution"] = True
        self.reject(canonical_bytes(value), "UNKNOWN_FIELD")

    def test_unknown_schema_version(self):
        value = copy.deepcopy(self.observation)
        value["schema_version"] = "2"
        self.reject(canonical_bytes(value), "SCHEMA_VALUE")

    def test_invalid_calendar_and_missing_timezone(self):
        for stamp in ("2026-02-30T00:00:00Z", "2026-10-06T00:00:00", "2026-10-06T25:00:00Z"):
            value = copy.deepcopy(self.observation)
            value["recorded_at"] = stamp
            with self.subTest(stamp=stamp):
                self.reject(canonical_bytes(value), "INVALID_DATE_TIME")

    def test_invalid_optional_observation_time_is_rejected(self):
        value = copy.deepcopy(self.observation)
        value["observed_at"] = "2026-02-30T00:00:00Z"
        self.reject(canonical_bytes(value), "SCHEMA_ALTERNATIVE")

    def test_boolean_cannot_impersonate_integer_counter(self):
        schema = copy.deepcopy(self.schema)
        schema["$defs"]["ObservationEnvelope"]["properties"]["uncertainty"] = {"type": "integer"}
        codec = RecordCodec(schema)
        value = copy.deepcopy(self.observation)
        value["uncertainty"] = True
        with self.assertRaises(ContractError) as caught:
            codec.decode(canonical_bytes(value))
        self.assertEqual(caught.exception.code, "SCHEMA_TYPE")

    def test_unsupported_schema_keyword_cannot_silently_weaken_validation(self):
        schema = copy.deepcopy(self.schema)
        schema["$defs"]["OperationPermit"]["unevaluatedProperties"] = False
        with self.assertRaises(ContractError) as caught:
            RecordCodec(schema)
        self.assertEqual(caught.exception.code, "UNSUPPORTED_SCHEMA_KEYWORD")

    def test_external_schema_reference_rejected(self):
        schema = copy.deepcopy(self.schema)
        schema["oneOf"][0]["$ref"] = "https://example.invalid/schema"
        with self.assertRaises(ContractError) as caught:
            RecordCodec(schema)
        self.assertEqual(caught.exception.code, "UNSUPPORTED_SCHEMA_REFERENCE")

    def test_security_identifier_trailing_newline(self):
        value = copy.deepcopy(self.observation)
        value["record_id"] += "\n"
        self.reject(canonical_bytes(value), "STRING_PATTERN")


if __name__ == "__main__":
    unittest.main()
