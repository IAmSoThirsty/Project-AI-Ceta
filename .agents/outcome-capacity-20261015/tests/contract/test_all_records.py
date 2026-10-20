"""All supplied record types cross-checked against a separate schema validator.

Generated values are synthetic shape fixtures, not observations, grants,
permits, accepted policy decisions or claims of a running governed system.
"""
import copy
import importlib.metadata
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts import ContractError, RecordCodec, canonical_bytes, strict_loads


def example(shape):
    if "const" in shape:
        return shape["const"]
    if "enum" in shape:
        return shape["enum"][0]
    if "anyOf" in shape:
        return example(shape["anyOf"][0])
    kind = shape["type"]
    if kind == "object":
        return {name: example(shape["properties"][name]) for name in shape["required"]}
    if kind == "array":
        return [example(shape["items"]) for _ in range(shape.get("minItems", 0))]
    if kind == "string":
        if shape.get("format") == "date-time":
            return "2026-10-06T21:00:00Z"
        if shape.get("pattern") == "^sha256:[0-9a-f]{64}$":
            return "sha256:" + "a" * 64
        return "fixture" + "x" * max(0, shape.get("minLength", 0) - 7)
    return {"integer": shape.get("minimum", 0), "boolean": False, "null": None}[kind]


class AllRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())
        cls.codec = RecordCodec(cls.schema)
        cls.records = {name: example(shape) for name, shape in cls.schema["$defs"].items()}

    def test_all_twenty_record_types_have_actual_decode_and_round_trip(self):
        self.assertEqual(len(self.records), 20)
        for name, instance in self.records.items():
            with self.subTest(record=name):
                original = json.dumps(instance, indent=2).encode()
                result = self.codec.decode(original)
                self.assertEqual(result.record_type, name)
                self.assertEqual(result.original_wire, original)
                self.assertEqual(result.as_dict(), instance)
                self.assertEqual(self.codec.decode(result.canonical_wire).commitment, result.commitment)

    def test_every_required_field_is_required_in_actual_codec(self):
        for name, instance in self.records.items():
            for field in instance:
                changed = copy.deepcopy(instance)
                del changed[field]
                with self.subTest(record=name, field=field), self.assertRaises(ContractError):
                    self.codec.decode(canonical_bytes(changed))

    def test_every_record_rejects_unknown_authority_field(self):
        for name, instance in self.records.items():
            changed = copy.deepcopy(instance)
            changed["owner_says_allow"] = True
            with self.subTest(record=name), self.assertRaises(ContractError):
                self.codec.decode(canonical_bytes(changed))

    def test_separate_draft202012_validator_agrees_on_shape_cases(self):
        try:
            from jsonschema import Draft202012Validator, FormatChecker
        except ImportError:
            self.skipTest("Declared jsonschema development oracle is unavailable; install requirements-contract-tests.txt")
        self.assertEqual(importlib.metadata.version("jsonschema"), "4.26.0")
        Draft202012Validator.check_schema(self.schema)
        checker = FormatChecker()
        self.assertIn("date-time", checker.checkers, "Date-time oracle dependency missing")
        self.assertFalse(checker.conforms("not-a-date", "date-time"))
        validator = Draft202012Validator(self.schema, format_checker=checker)
        for name, instance in self.records.items():
            with self.subTest(record=name):
                validator.validate(instance)
                self.codec.decode(canonical_bytes(instance))
                for field in instance:
                    missing = copy.deepcopy(instance)
                    del missing[field]
                    self.assertFalse(validator.is_valid(missing))
                unknown = copy.deepcopy(instance)
                unknown["owner_says_allow"] = True
                self.assertFalse(validator.is_valid(unknown))

if __name__ == "__main__":
    unittest.main()
