"""Coverage and source mutation rejection with synthetic local fixtures."""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts import ContractError
spec = importlib.util.spec_from_file_location("source_coverage", ROOT / "tools/verify_source_coverage.py")
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)


class SourceCoverageTests(unittest.TestCase):
    def test_current_summary_and_original_pending_description_are_consistent(self):
        rows = [{"applicability": state} for state in ("DIRECT", "NOT_APPLICABLE", "UNRESOLVED")]
        result = coverage.require_summary_consistency({
            "sections": rows, "coverage_state": "3_SOURCE_SECTIONS_PRESENT_2_APPLICABILITY_ASSESSED_1_PENDING"})
        self.assertEqual(result, {"total": 3, "assessed": 2, "unresolved": 1})
        coverage.require_summary_consistency({
            "sections": [{"applicability": "UNRESOLVED"}],
            "coverage_state": "1_SOURCE_SECTIONS_PRESENT_APPLICABILITY_PENDING"})

    def test_stale_total_assessed_or_pending_summary_is_rejected(self):
        rows = [{"applicability": state} for state in ("DIRECT", "SUPPORTING", "UNRESOLVED")]
        for stale in ("3_SOURCE_SECTIONS_PRESENT_1_APPLICABILITY_ASSESSED_2_PENDING",
                      "4_SOURCE_SECTIONS_PRESENT_2_APPLICABILITY_ASSESSED_2_PENDING",
                      "3_SOURCE_SECTIONS_PRESENT_3_APPLICABILITY_ASSESSED_0_PENDING"):
            with self.subTest(stale=stale), self.assertRaisesRegex(
                    ContractError, "SOURCE_COVERAGE_SUMMARY_MISMATCH"):
                coverage.require_summary_consistency({"sections": rows, "coverage_state": stale})

    def test_original_pending_description_cannot_hide_assessed_source(self):
        with self.assertRaisesRegex(ContractError, "SOURCE_COVERAGE_SUMMARY_MISMATCH"):
            coverage.require_summary_consistency({
                "sections": [{"applicability": "DIRECT"}],
                "coverage_state": "1_SOURCE_SECTIONS_PRESENT_APPLICABILITY_PENDING"})

    def test_unknown_state_or_unsubstantiated_completion_summary_is_rejected(self):
        with self.assertRaisesRegex(ContractError, "UNKNOWN_APPLICABILITY"):
            coverage.require_summary_consistency({
                "sections": [{"applicability": "COMPLETE"}],
                "coverage_state": "1_SOURCE_SECTIONS_PRESENT_1_APPLICABILITY_ASSESSED_0_PENDING"})
        for state in (None, True, "COMPLETE", " 1_SOURCE_SECTIONS_PRESENT_1_APPLICABILITY_ASSESSED_0_PENDING"):
            with self.subTest(summary=state), self.assertRaisesRegex(
                    ContractError, "SOURCE_COVERAGE_SUMMARY_MISMATCH"):
                coverage.require_summary_consistency({
                    "sections": [{"applicability": "DIRECT"}], "coverage_state": state})

    def test_mutation_after_metadata_read_before_first_snapshot_is_rejected(self):
        fixture_dir = ROOT / ".local-test-output"
        fixture_dir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="coverage-read-", dir=fixture_dir) as temp:
            root = Path(temp)
            self.assertTrue(root.resolve().is_relative_to(fixture_dir.resolve()))
            source = root / "metadata.json"
            source.write_bytes(b'{"coverage":"before"}')
            wires = {"metadata.json": source.read_bytes()}
            source.write_bytes(b'{"coverage":"after"}')
            before = coverage.snapshot(root, ["metadata.json"])
            with self.assertRaisesRegex(ContractError, "SOURCE_CHANGED_DURING_VERIFICATION"):
                coverage.require_read_inputs_unchanged(wires, before)
            self.assertEqual(source.read_bytes(), b'{"coverage":"after"}')

    def test_exact_read_bytes_match_first_snapshot_without_status_promotion(self):
        wires = {"metadata.json": b'{"applicability":"UNRESOLVED"}'}
        coverage.require_read_inputs_unchanged(
            wires, {"metadata.json": hashlib.sha256(wires["metadata.json"]).hexdigest()})

    def test_real_identifier_cannot_be_rebound_to_another_original(self):
        baseline = [{"section": "033", "path": "sources/033.txt", "sha256": "a" * 64,
                     "bytes": 10, "volume": 3, "original_title": "Software Architecture"}]
        for field, replacement in (("path", "sources/046.txt"), ("volume", 4),
                                   ("original_title", "Identity Architecture"), ("sha256", "b" * 64)):
            current = copy.deepcopy(baseline)
            current[0][field] = replacement
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, "ORIGINAL_IDENTIFIER_REBOUND"):
                coverage.require_original_bindings(current, baseline, "section")

    def test_applicability_change_does_not_rewrite_original_identity(self):
        baseline = [{"section": "033", "path": "sources/033.txt", "sha256": "a" * 64,
                     "bytes": 10, "original_status": "CONTENT-COMPLETE", "applicability": "UNRESOLVED"}]
        current = copy.deepcopy(baseline)
        current[0]["applicability"] = "DIRECT"
        current[0]["decision_reason"] = "Material software rebuild"
        coverage.require_original_bindings(current, baseline, "section")
    def test_omitted_volume_is_rejected(self):
        with self.assertRaisesRegex(ContractError, "VOLUME_SET_INCOMPLETE"):
            coverage.check_ids([{"volume": n} for n in range(1, 20)], "volume", set(range(1, 21)), "VOLUME_SET_INCOMPLETE")

    def test_omitted_lifecycle_section_is_rejected(self):
        with self.assertRaisesRegex(ContractError, "SECTION_SET_INCOMPLETE"):
            coverage.check_ids([{"section": f"{n:03}"} for n in range(1, 406)], "section",
                               {f"{n:03}" for n in range(1, 407)}, "SECTION_SET_INCOMPLETE")

    def test_duplicate_section_cannot_replace_missing_section(self):
        with self.assertRaises(ContractError):
            coverage.check_ids([{"section": "001"}, {"section": "001"}], "section", {"001", "002"}, "SECTION_SET_INCOMPLETE")

    def test_invented_original_identifier_is_rejected(self):
        with self.assertRaises(ContractError):
            coverage.check_ids([{"section": f"{n:03}"} for n in range(1, 407)] + [{"section": "CETA-407"}],
                               "section", {f"{n:03}" for n in range(1, 407)}, "SECTION_SET_INCOMPLETE")

    def test_path_escape_rejected_before_file_read(self):
        for relative in ("../decoy.txt", "C:/decoy.txt", "/decoy.txt", "sources\\decoy.txt"):
            with self.subTest(relative=relative), self.assertRaises(ContractError):
                coverage.safe_path(ROOT, relative)

    def test_real_file_mutation_invalidates_earlier_evidence(self):
        fixture_dir = ROOT / ".local-test-output"
        fixture_dir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_dir) as temp:
            root = Path(temp)
            path = root / "source.txt"
            path.write_bytes(b"baseline\r\n")
            before = coverage.snapshot(root, ["source.txt"])
            path.write_bytes(b"newer work\n")
            with self.assertRaisesRegex(ContractError, "SOURCE_CHANGED_DURING_VERIFICATION"):
                coverage.require_unchanged(before, coverage.snapshot(root, ["source.txt"]))
            self.assertEqual(path.read_bytes(), b"newer work\n")

    def test_original_unchanged_snapshot_accepted(self):
        before = {"source.txt": "a" * 64}
        coverage.require_unchanged(before, dict(before))

    def assert_contract_leaf_imports(self, source, path):
        allowed = {"__future__", "dataclasses", "datetime", "hashlib", "json", "re", "unicodedata", "typing"}
        contract_modules = {item.stem for item in (ROOT / "src/ceta/contracts").glob("*.py")}
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name, allowed, str(path))
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    self.assertEqual(node.level, 1, str(path))
                    self.assertIn(node.module, contract_modules, str(path))
                elif node.module == "enum":
                    # Qualify this observed pure type, without permitting a
                    # general enum import or a different contract/domain owner.
                    self.assertEqual(path.name, "resource_management.py")
                    self.assertEqual([(alias.name, alias.asname) for alias in node.names], [("Enum", None)])
                else:
                    self.assertIn(node.module, allowed, str(path))

    def test_contract_core_has_no_infrastructure_or_other_domain_imports(self):
        for path in (ROOT / "src/ceta/contracts").glob("*.py"):
            self.assert_contract_leaf_imports(path.read_text(encoding="utf-8"), path)

    def test_only_the_observed_enum_type_import_is_qualified(self):
        path = ROOT / "src/ceta/contracts/resource_management.py"
        self.assert_contract_leaf_imports("from enum import Enum", path)
        for source in ("import enum", "from enum import auto", "from enum import Enum, auto",
                       "from enum import Enum as Other", "from enum import *"):
            with self.subTest(source=source), self.assertRaises(AssertionError):
                self.assert_contract_leaf_imports(source, path)
        with self.assertRaises(AssertionError):
            self.assert_contract_leaf_imports("from enum import Enum", ROOT / "src/ceta/contracts/wire.py")

    def test_contract_leaf_rejects_infrastructure_and_relative_domain_escape(self):
        path = ROOT / "src/ceta/contracts/resource_management.py"
        for source in ("import os", "import ctypes", "import json.tool", "from json.tool import main", "from ceta.supervisor import windows_jobs",
                       "from ..supervisor import windows_jobs", "from ..resource import hardware",
                       "from .missing_owner import require"):
            with self.subTest(source=source), self.assertRaises(AssertionError):
                self.assert_contract_leaf_imports(source, path)
        self.assert_contract_leaf_imports("from .wire import ContractError", path)


if __name__ == "__main__":
    unittest.main()
