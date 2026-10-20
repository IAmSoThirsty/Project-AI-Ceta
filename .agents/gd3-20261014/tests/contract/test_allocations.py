"""Fault-inject allocation links; these are specification-tool tests only."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import verify_allocations as allocation


def fixture():
    model = {
        "requirements": [{"id": "R1", "section": "S1", "component_owner": "C1", "acceptance_ids": ["B1"]},
                         {"id": "R2", "section": "S1", "component_owner": "LEAD_INTEGRATOR", "acceptance_ids": ["B1"]}],
        "components": [{"id": "C1", "slug": "contracts", "section_ids": ["S1"], "allowed_static_dependencies": []},
                       {"id": "C2", "slug": "worker", "section_ids": ["S1"], "allowed_static_dependencies": ["contracts"]}],
        "packages": [{"id": "W1", "requirement_ids": ["R1", "R2"], "acceptance_ids": ["B1"],
                      "component_owners": ["C1", "C2", "LEAD_INTEGRATOR"], "depends_on": [], "target_gate": "G1"},
                     {"id": "W2", "requirement_ids": ["R1"], "acceptance_ids": ["B1"],
                      "component_owners": ["C2"], "depends_on": ["W1"], "target_gate": "G1"}],
        "cases": [{"id": "B1", "requirement_ids": ["R1", "R2"]}],
        "gates": [{"id": "G1", "required_work_packages": ["W1", "W2"]}],
    }
    expected = {name: {r["id"] for r in rows} for name, rows in model.items()}
    return model, expected


class AllocationTests(unittest.TestCase):
    def check(self, model, expected):
        before = copy.deepcopy(model)
        result = allocation.check_models(model, expected)
        self.assertEqual(before, model, "checker changed authoritative input")
        return result

    def test_valid_allocation_and_shared_support_component_are_not_promoted(self):
        model, expected = fixture()
        model["cases"][0]["result"] = "NOT_RUN"
        self.assertEqual([], self.check(model, expected))
        self.assertEqual("NOT_RUN", model["cases"][0]["result"])

    def test_duplicate_or_deleted_identifier_cannot_replace_baseline(self):
        for mode in ("duplicate", "delete", "substitute"):
            model, expected = fixture()
            if mode == "duplicate":
                model["requirements"].append(copy.deepcopy(model["requirements"][0]))
            elif mode == "delete":
                model["requirements"].pop()
            else:
                model["requirements"][0]["id"] = "R3"
            with self.subTest(mode=mode):
                found = self.check(model, expected)
                self.assertTrue(any("DUPLICATE_ID" in e or "ORIGINAL_ID_SET_CHANGED" in e for e in found))

    def test_unallocated_requirement_is_visible(self):
        model, expected = fixture()
        model["packages"][0]["requirement_ids"].remove("R2")
        self.assertIn("UNALLOCATED_REQUIREMENT:R2", self.check(model, expected))

    def test_unallocated_case_is_visible(self):
        model, expected = fixture()
        for row in model["packages"]:
            row["acceptance_ids"] = []
        self.assertIn("UNALLOCATED_CASE:B1", self.check(model, expected))

    def test_unallocated_component_is_visible(self):
        model, expected = fixture()
        model["packages"][0]["component_owners"].remove("C1")
        self.assertIn("UNALLOCATED_COMPONENT:C1", self.check(model, expected))

    def test_unknown_owner_and_owner_section_mismatch_reject(self):
        for value, code in (("ABSENT", "UNKNOWN_REQUIREMENT_OWNER:R1"), ("C2", "OWNER_SECTION_MISMATCH:R1")):
            model, expected = fixture()
            model["components"][1]["section_ids"] = ["S2"]
            model["requirements"][0]["component_owner"] = value
            with self.subTest(value=value):
                self.assertIn(code, self.check(model, expected))

    def test_unknown_or_missing_case_requirement_link_rejects(self):
        model, expected = fixture()
        model["cases"][0]["requirement_ids"] = ["R1", "ABSENT"]
        found = self.check(model, expected)
        self.assertIn("UNKNOWN_REFERENCE:B1:requirement_ids:ABSENT", found)
        self.assertIn("CASE_MISSING_REQUIREMENT_LINK:R2:B1", found)

    def test_unknown_component_dependency_and_duplicate_slug_reject(self):
        model, expected = fixture()
        model["components"][1]["allowed_static_dependencies"] = ["missing"]
        self.assertIn("UNKNOWN_REFERENCE:C2:allowed_static_dependencies:missing", self.check(model, expected))
        model["components"][1]["slug"] = "contracts"
        self.assertIn("COMPONENT_SLUG_MISSING_OR_DUPLICATE", self.check(model, expected))

    def test_component_and_package_cycles_reject(self):
        model, expected = fixture()
        model["components"][0]["allowed_static_dependencies"] = ["worker"]
        model["packages"][0]["depends_on"] = ["W2"]
        found = self.check(model, expected)
        self.assertIn("COMPONENT_DEPENDENCY_CYCLE", found)
        self.assertIn("WORK_PACKAGE_DEPENDENCY_CYCLE", found)

    def test_unknown_gate_and_gate_package_reject(self):
        model, expected = fixture()
        model["packages"][0]["target_gate"] = "G2"
        model["gates"][0]["required_work_packages"] = ["ABSENT"]
        found = self.check(model, expected)
        self.assertIn("UNKNOWN_TARGET_GATE:W1", found)
        self.assertIn("UNKNOWN_REFERENCE:G1:required_work_packages:ABSENT", found)

    def test_malformed_registry_and_references_return_failure(self):
        for bad in (None, {}, "R1", [None], [["R1"]], ["R1", "R1"]):
            model, expected = fixture()
            model["packages"][0]["requirement_ids"] = bad
            with self.subTest(bad=bad):
                self.assertTrue(any(e.startswith("MALFORMED_REFERENCES") for e in self.check(model, expected)))
        model, expected = fixture()
        model["cases"] = {"B1": {}}
        self.assertIn("MALFORMED_REGISTRY:cases", self.check(model, expected))

    def test_self_cycle_cannot_hide_in_dependencies(self):
        model, expected = fixture()
        model["packages"][0]["depends_on"] = ["W1"]
        self.assertIn("WORK_PACKAGE_DEPENDENCY_CYCLE", self.check(model, expected))

    def test_malformed_section_and_row_identifier_fail_without_exception(self):
        model, expected = fixture()
        model["requirements"][0]["section"] = []
        model["components"].append({"id": []})
        found = self.check(model, expected)
        self.assertIn("MALFORMED_REQUIREMENT_SECTION:R1", found)
        self.assertIn("MALFORMED_ROW:components", found)

    def test_current_real_input_mutation_is_not_certified(self):
        original_snapshot = allocation.snapshot
        calls = []
        def changed(root, paths):
            result = original_snapshot(root, paths)
            calls.append(set(paths))
            if len(calls) == 2:
                result["requirements/requirements.json"] = "0" * 64
            return result
        with patch.object(allocation, "snapshot", side_effect=changed):
            result = allocation.verify(ROOT)
        self.assertEqual("FAIL", result["result"])
        self.assertIn("SOURCE_CHANGED_DURING_VERIFICATION", result["errors"])
        self.assertEqual(calls[0], calls[1])
        self.assertEqual("NOT_CLOSED", result["gate_a"])

    def test_manifest_substitution_rejects_before_registry_load(self):
        original_snapshot = allocation.snapshot
        def changed(root, paths):
            result = original_snapshot(root, paths)
            result["PACKAGE_MANIFEST.json"] = "0" * 64
            return result
        with patch.object(allocation, "snapshot", side_effect=changed):
            result = allocation.verify(ROOT)
        self.assertEqual("FAIL", result["result"])
        self.assertEqual(["ORIGINAL_MANIFEST_CHANGED"], result["errors"])
        self.assertEqual({}, result["registry_counts"])


if __name__ == "__main__":
    unittest.main()
