"""Public codec acceptance for the reviewed schema and timestamp amendments."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts import ContractError, RecordCodec, canonical_bytes, strict_loads


class SchemaAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())
        cls.observation = strict_loads(
            (ROOT / "contracts/examples/observation_shape_valid.json").read_bytes()
        )["instance"]

    def changed_shape(self):
        schema = copy.deepcopy(self.schema)
        return schema, schema["$defs"]["ObservationEnvelope"]

    def reject_schema(self, schema, code):
        with self.assertRaises(ContractError) as caught:
            RecordCodec(schema)
        self.assertEqual(caught.exception.code, code)

    def test_duplicate_required_names_are_rejected(self):
        schema, shape = self.changed_shape()
        shape["required"].append(shape["required"][0])
        self.reject_schema(schema, "INVALID_SCHEMA_STRUCTURE")

    def test_empty_and_nonlist_alternatives_and_enum_are_rejected(self):
        for keyword in ("anyOf", "oneOf", "enum"):
            for value in ([], {}, "value", None):
                with self.subTest(keyword=keyword, value=value):
                    schema, shape = self.changed_shape()
                    shape[keyword] = value
                    self.reject_schema(schema, "INVALID_SCHEMA_STRUCTURE")

    def test_nonmapping_properties_and_definitions_are_rejected(self):
        for keyword in ("properties", "$defs"):
            for value in ([], "value", None, True):
                with self.subTest(keyword=keyword, value=value):
                    schema, shape = self.changed_shape()
                    shape[keyword] = value
                    self.reject_schema(schema, "INVALID_SCHEMA_STRUCTURE")

    def test_nonboolean_additional_properties_are_rejected(self):
        for value in (0, 1, "false", [], {}, None):
            with self.subTest(value=value):
                schema, shape = self.changed_shape()
                shape["additionalProperties"] = value
                self.reject_schema(schema, "INVALID_SCHEMA_STRUCTURE")

    def test_boolean_fractional_and_string_bounds_have_typed_rejection(self):
        for kind, lower, upper in (
            ("integer", "minimum", "maximum"),
            ("array", "minItems", "maxItems"),
            ("string", "minLength", "maxLength"),
        ):
            for keyword in (lower, upper):
                for value in (True, False, 1.5, "1"):
                    with self.subTest(kind=kind, keyword=keyword, value=value):
                        schema, shape = self.changed_shape()
                        shape["properties"]["record_id"] = {"type": kind, keyword: value}
                        self.reject_schema(schema, "INVALID_SCHEMA_BOUND")

    def test_bounds_cannot_be_attached_to_the_wrong_schema_type(self):
        for keyword in ("minimum", "maximum", "minItems", "maxItems"):
            with self.subTest(keyword=keyword):
                schema, shape = self.changed_shape()
                shape["properties"]["record_id"] = {"type": "string", keyword: 1}
                self.reject_schema(schema, "INVALID_SCHEMA_BOUND")

    def test_negative_array_and_string_length_bounds_are_rejected(self):
        for kind, keywords in (("array", ("minItems", "maxItems")),
                               ("string", ("minLength", "maxLength"))):
            for keyword in keywords:
                with self.subTest(kind=kind, keyword=keyword):
                    schema, shape = self.changed_shape()
                    shape["properties"]["record_id"] = {"type": kind, keyword: -1}
                    self.reject_schema(schema, "INVALID_SCHEMA_BOUND")

    def test_inverted_bounds_are_rejected(self):
        for kind, lower, upper in (("integer", "minimum", "maximum"),
                                   ("array", "minItems", "maxItems"),
                                   ("string", "minLength", "maxLength")):
            with self.subTest(kind=kind):
                schema, shape = self.changed_shape()
                shape["properties"]["record_id"] = {"type": kind, lower: 2, upper: 1}
                self.reject_schema(schema, "INVALID_SCHEMA_BOUND")

    def test_two_definition_reference_cycle_is_rejected(self):
        schema, first = self.changed_shape()
        first["$ref"] = "#/$defs/OperationPermit"
        schema["$defs"]["OperationPermit"]["$ref"] = "#/$defs/ObservationEnvelope"
        self.reject_schema(schema, "CYCLIC_SCHEMA_REFERENCE")

    def test_cycles_through_properties_items_alternatives_and_definitions_are_rejected(self):
        ref = {"$ref": "#/$defs/ObservationEnvelope"}
        for route in ("properties", "items", "anyOf", "oneOf", "$defs"):
            with self.subTest(route=route):
                schema, shape = self.changed_shape()
                if route == "$defs":
                    shape[route] = {"nested": copy.deepcopy(ref)}
                else:
                    child = copy.deepcopy(ref)
                    if route == "items":
                        child = {"type": "array", "items": child}
                    elif route in ("anyOf", "oneOf"):
                        child = {route: [child]}
                    shape["properties"]["record_id"] = child
                self.reject_schema(schema, "CYCLIC_SCHEMA_REFERENCE")

    def test_repeated_acyclic_reference_remains_usable_for_actual_decode(self):
        schema = copy.deepcopy(self.schema)
        schema["anyOf"] = [
            {"$ref": "#/$defs/ObservationEnvelope"},
            {"$ref": "#/$defs/ObservationEnvelope"},
        ]
        parsed = RecordCodec(schema).decode(canonical_bytes(self.observation))
        self.assertEqual(parsed.as_dict(), self.observation)

    def test_cyclic_python_schema_container_has_bounded_rejection(self):
        schema, shape = self.changed_shape()
        child = {"type": "object", "properties": {}}
        child["properties"]["self"] = child
        shape["properties"]["record_id"] = child
        self.reject_schema(schema, "DEPTH_LIMIT")

    def test_overdeep_schema_container_has_bounded_rejection(self):
        schema, shape = self.changed_shape()
        child = {"type": "string"}
        for _ in range(40):
            child = {"type": "object", "properties": {"nested": child}}
        shape["properties"]["record_id"] = child
        self.reject_schema(schema, "DEPTH_LIMIT")

    def test_literal_enum_and_const_objects_are_not_schema_positions(self):
        for keyword in ("enum", "const"):
            with self.subTest(keyword=keyword):
                schema, shape = self.changed_shape()
                literal = {"minimum": "literal-data", "maxItems": False}
                shape["properties"]["record_id"] = {
                    keyword: [literal] if keyword == "enum" else literal
                }
                self.assertIsInstance(RecordCodec(schema), RecordCodec)

    def test_valid_time_and_offset_boundaries_preserve_original_value(self):
        codec = RecordCodec(self.schema)
        for timestamp in ("2026-10-06T00:00:00Z", "2026-10-06T23:59:59Z",
                          "2026-10-06T23:59:59.999999999+23:59",
                          "2026-10-06T00:00:00-23:59"):
            with self.subTest(timestamp=timestamp):
                record = dict(self.observation, recorded_at=timestamp)
                self.assertEqual(codec.decode(canonical_bytes(record)).as_dict()["recorded_at"], timestamp)

    def test_invalid_time_and_offset_ranges_are_rejected(self):
        codec = RecordCodec(self.schema)
        for timestamp in ("2026-10-06T24:00:00Z", "2026-10-06T23:60:00Z",
                          "2026-10-06T23:59:60Z", "2026-10-06T00:00:00+24:00",
                          "2026-10-06T00:00:00+00:60"):
            with self.subTest(timestamp=timestamp), self.assertRaises(ContractError) as caught:
                codec.decode(canonical_bytes(dict(self.observation, recorded_at=timestamp)))
            self.assertEqual(caught.exception.code, "INVALID_DATE_TIME")

    def test_nonascii_numeric_date_and_time_digits_are_rejected(self):
        codec = RecordCodec(self.schema)
        for timestamp in ("２０２６-10-06T00:00:00Z", "2026-10-06T００:00:00Z",
                          "2026-10-06T00:00:00+００:00"):
            with self.subTest(timestamp=timestamp), self.assertRaises(ContractError) as caught:
                codec.decode(canonical_bytes(dict(self.observation, recorded_at=timestamp)))
            self.assertEqual(caught.exception.code, "INVALID_DATE_TIME")


if __name__ == "__main__":
    unittest.main()
