from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts import ContractError
from ceta.contracts.provenance import ProvenanceCatalog, SourceReference


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.sources = {"codex:edition-fixture": {"033": "sha256:" + "a" * 64}}
        self.scales = {"codex:source-status:fixture": ("CONTENT-COMPLETE", "SOURCE-RECONCILED"),
                       "ceta:runtime-status:fixture": ("ACTIVE", "VERIFIED"),
                       "source-a:fixture": ("C0", "C1"), "source-b:fixture": ("C0", "C1")}
        self.catalog = ProvenanceCatalog(self.sources, self.scales)

    def test_actual_identifier_and_exact_commitment_resolve(self):
        reference = SourceReference("codex:edition-fixture", "033", "sha256:" + "a" * 64)
        self.assertEqual(self.catalog.validate_source(reference), reference)

    def test_invented_identifier_cannot_resolve(self):
        with self.assertRaisesRegex(ContractError, "UNSUPPORTED_ORIGINAL_IDENTIFIER"):
            self.catalog.validate_source(SourceReference("codex:edition-fixture", "CETA-407", "sha256:" + "a" * 64))

    def test_matching_name_from_different_source_cannot_resolve(self):
        with self.assertRaisesRegex(ContractError, "UNSUPPORTED_SOURCE_NAMESPACE"):
            self.catalog.validate_source(SourceReference("unrelated:edition", "033", "sha256:" + "a" * 64))

    def test_changed_source_bytes_invalidate_reference(self):
        with self.assertRaisesRegex(ContractError, "SOURCE_COMMITMENT_MISMATCH"):
            self.catalog.validate_source(SourceReference("codex:edition-fixture", "033", "sha256:" + "b" * 64))

    def test_source_status_cannot_be_used_as_runtime_status(self):
        with self.assertRaisesRegex(ContractError, "UNSUPPORTED_MATURITY_LABEL"):
            self.catalog.validate_maturity("ceta:runtime-status:fixture", "CONTENT-COMPLETE")

    def test_wrong_maturity_namespace_is_rejected(self):
        with self.assertRaisesRegex(ContractError, "UNSUPPORTED_MATURITY_NAMESPACE"):
            self.catalog.validate_maturity("invented:scale", "VERIFIED")

    def test_matching_c0_labels_from_distinct_scales_are_not_comparable(self):
        with self.assertRaisesRegex(ContractError, "MATURITY_SCALES_NOT_COMPARABLE"):
            self.catalog.require_same_scale(("source-a:fixture", "C0"), ("source-b:fixture", "C0"))

    def test_caller_cannot_change_frozen_catalog(self):
        self.sources["codex:edition-fixture"]["033"] = "sha256:" + "b" * 64
        self.scales["ceta:runtime-status:fixture"] = ("CONTENT-COMPLETE",)
        self.catalog.validate_source(SourceReference("codex:edition-fixture", "033", "sha256:" + "a" * 64))
        with self.assertRaises(ContractError):
            self.catalog.validate_maturity("ceta:runtime-status:fixture", "CONTENT-COMPLETE")

    def test_malformed_references_produce_contract_rejection(self):
        for reference in (None, {}, SourceReference([], "033", "hash"),
                          SourceReference("codex:edition-fixture", {}, "hash")):
            with self.subTest(reference=reference), self.assertRaises(ContractError):
                self.catalog.validate_source(reference)
        for arguments in (([], "C0"), ("source-a:fixture", {})):
            with self.assertRaises(ContractError):
                self.catalog.validate_maturity(*arguments)
        with self.assertRaises(ContractError):
            self.catalog.require_same_scale(("source-a:fixture",), ("source-b:fixture", "C0"))


if __name__ == "__main__":
    unittest.main()
