import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
# Exact owner-supplied source fixtures belong to this repository.
SPEC_ROOT = ROOT
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts import ContractError
from ceta.contracts.source_references import WorkingReferenceMap, SCHEMA_SHA256


class SourceReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping_wire = (ROOT / "contracts/source_reference_map_v1.json").read_bytes()
        cls.document = json.loads(cls.mapping_wire)
        cls.mapping = WorkingReferenceMap(cls.mapping_wire)
        cls.schema = (ROOT / cls.document["schema"]["working_material_path"]).read_bytes()

    def test_all_twenty_one_actual_guides_resolve_without_rewriting_originals(self):
        self.assertEqual(len(self.document["guides"]), 21)
        self.assertEqual(hashlib.sha256(self.schema).hexdigest(), SCHEMA_SHA256)
        for row in self.document["guides"]:
            with self.subTest(guide=row["path"]):
                path = SPEC_ROOT / row["path"]
                before = path.read_bytes()
                result = self.mapping.resolve(row["path"], before, self.schema)
                self.assertEqual(result.schema_bytes, self.schema)
                self.assertEqual(result.original_reference, "../schemas/handoff_record.md")
                self.assertEqual(path.read_bytes(), before)
                self.assertIn("AUTHOR_INTENT_NOT_ESTABLISHED", result.status)

    def test_changed_guide_is_rejected(self):
        row = self.document["guides"][0]
        wire = (SPEC_ROOT / row["path"]).read_bytes()
        with self.assertRaisesRegex(ContractError, "GUIDE_SOURCE_COMMITMENT_MISMATCH"):
            self.mapping.resolve(row["path"], wire + b"\n", self.schema)

    def test_changed_or_invented_schema_is_rejected(self):
        row = self.document["guides"][0]
        wire = (SPEC_ROOT / row["path"]).read_bytes()
        for candidate in (b"invented", self.schema[:-1] + bytes([self.schema[-1] ^ 1])):
            with self.subTest(candidate_hash=hashlib.sha256(candidate).hexdigest()):
                with self.assertRaisesRegex(ContractError, "SCHEMA_SOURCE_COMMITMENT_MISMATCH"):
                    self.mapping.resolve(row["path"], wire, candidate)

    def test_unmapped_or_traversal_reference_is_rejected(self):
        for candidate in ("../other-project/guide.md", "invented", None):
            with self.assertRaisesRegex(ContractError, "UNMAPPED_SOURCE_REFERENCE"):
                self.mapping.resolve(candidate, b"", self.schema)

    def test_duplicate_missing_and_wrong_witness_maps_are_rejected(self):
        changes = []
        missing = copy.deepcopy(self.document)
        missing["guides"].pop()
        changes.append(missing)
        duplicate = copy.deepcopy(self.document)
        duplicate["guides"][-1] = copy.deepcopy(duplicate["guides"][0])
        changes.append(duplicate)
        wrong = copy.deepcopy(self.document)
        wrong["guides"][0]["witness"] = 999
        changes.append(wrong)
        for changed in changes:
            with self.assertRaises(ContractError):
                WorkingReferenceMap(json.dumps(changed).encode())

    def test_valid_witness_numbers_cannot_be_permuted_between_guide_identities(self):
        changed = copy.deepcopy(self.document)
        first, second = changed["guides"][:2]
        first["witness"], second["witness"] = second["witness"], first["witness"]
        with self.assertRaisesRegex(ContractError, "REFERENCE_MAP_COMMITMENT_MISMATCH"):
            WorkingReferenceMap(json.dumps(changed).encode())


if __name__ == "__main__":
    unittest.main()
