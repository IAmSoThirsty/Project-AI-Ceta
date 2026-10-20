"""Full supplied 28/8 graph fixtures; no formal gate or installed qualification."""
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
# Exact owner-supplied fixture bytes are retained inside this repository;
# their source hash commitments are checked by ConstructionPlan.
SOURCE = ROOT
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.wire import ContractError
from ceta.contracts.construction import ConstructionPlan, topological_order


class ConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wp_bytes = (SOURCE / "build/work_packages.json").read_bytes()
        cls.gate_bytes = (SOURCE / "build/gates.json").read_bytes()
        cls.plan = ConstructionPlan(cls.wp_bytes, cls.gate_bytes)
        cls.all_ids = tuple(p.package_id for p in cls.plan.packages)

    def reject(self, code, fn, *args):
        with self.assertRaises(ContractError) as raised:
            fn(*args)
        self.assertEqual(raised.exception.code, code)

    def test_all_28_packages_dependencies_requirements_cases_and_statuses_preserved(self):
        source = json.loads(self.wp_bytes)["packages"]
        self.assertEqual(len(source), 28)
        self.assertEqual(len(self.plan.packages), 28)
        for p, s in zip(self.plan.packages, source):
            self.assertEqual(
                (p.package_id, p.title, p.path, p.dependencies, p.component_owners,
                 p.requirement_ids, p.acceptance_ids, p.target_gate,
                 p.implementation_status, p.review_status, p.evidence_refs),
                (s["id"], s["title"], s["path"], tuple(s["depends_on"]), tuple(s["component_owners"]),
                 tuple(s["requirement_ids"]), tuple(s["acceptance_ids"]), s["target_gate"],
                 s["implementation_status"], s["review_status"], tuple(s["evidence_refs"])))

    def test_all_eight_gate_memberships_acceptance_bodies_and_recorded_states_preserved(self):
        source = json.loads(self.gate_bytes)["gates"]
        self.assertEqual(len(self.plan.gates), 8)
        self.assertEqual(sum(len(g.members) for g in self.plan.gates), 28)
        for g, s in zip(self.plan.gates, source):
            self.assertEqual((g.gate_id, g.name, g.members, g.acceptance,
                              g.recorded_state, g.recorded_evidence_refs),
                             (s["id"], s["name"], tuple(s["required_work_packages"]), s["acceptance"],
                              s["state"], tuple(s["evidence_refs"])))

    def test_deterministic_acyclic_order_covers_every_dependency(self):
        graph = tuple((p.package_id, p.dependencies) for p in self.plan.packages)
        self.assertEqual(self.plan.order, topological_order(tuple(reversed(graph))))
        self.assertEqual(set(self.plan.order), set(self.all_ids))
        positions = {name: index for index, name in enumerate(self.plan.order)}
        for p in self.plan.packages:
            for dep in p.dependencies:
                self.assertLess(positions[dep], positions[p.package_id])
        completed = ()
        for package_id in self.plan.order:
            self.assertIn(package_id, self.plan.construction_ready(completed))
            completed += (package_id,)
        self.assertEqual(self.plan.construction_ready(completed), ())

    def test_cross_gate_dependencies_construct_in_order_without_gate_relabeling(self):
        packages = {p.package_id: p for p in self.plan.packages}
        self.assertEqual((packages["WP-16"].target_gate, packages["WP-15"].target_gate), ("G-C", "G-D"))
        self.assertIn("WP-15", packages["WP-16"].dependencies)
        self.assertEqual((packages["WP-21"].target_gate, packages["WP-18"].target_gate), ("G-D", "G-F"))
        self.assertIn("WP-18", packages["WP-21"].dependencies)
        position = {name: i for i, name in enumerate(self.plan.order)}
        self.assertLess(position["WP-15"], position["WP-16"])
        self.assertLess(position["WP-18"], position["WP-21"])
        self.assertNotIn("WP-16", self.plan.construction_ready(
            tuple(name for name in self.plan.dependency_closure(("WP-16",)) if name not in ("WP-15", "WP-16"))))

    def test_incoherent_completed_claims_cannot_release_successors(self):
        self.reject("INCOHERENT_COMPLETED_PACKAGE_CLAIMS", self.plan.construction_ready, ("WP-16",))
        self.reject("INCOHERENT_COMPLETED_PACKAGE_CLAIMS", self.plan.construction_ready, ("WP-21",))

    def test_every_gate_positive_checklist_still_confers_no_gate_or_runtime_authority(self):
        for gate in self.plan.gates:
            with self.subTest(gate=gate.gate_id):
                result = self.plan.assess_gate(gate.gate_id, self.all_ids, True, ("fixture:gate-evidence",))
                self.assertTrue(result.candidate_satisfied)
                self.assertFalse(result.gate_qualified)
                self.assertFalse(result.runtime_authorized)
                self.assertEqual(result.implementation_status, "IMPLEMENTED_NOT_QUALIFIED")
                self.assertEqual(result.acceptance, gate.acceptance)
                self.assertEqual(gate.recorded_state, "NOT_EVALUATED")

    def test_members_alone_omit_cross_gate_prerequisites_and_non_package_acceptance(self):
        for gate in self.plan.gates:
            no_evidence = self.plan.assess_gate(gate.gate_id, self.all_ids, False, ())
            self.assertFalse(no_evidence.candidate_satisfied)
            empty_evidence = self.plan.assess_gate(gate.gate_id, self.all_ids, True, ())
            self.assertFalse(empty_evidence.candidate_satisfied)
        c = self.plan.assess_gate("G-C", self.plan.gate("G-C").members, True, ("fixture:evidence",))
        self.assertIn("WP-15", c.missing_dependencies)
        self.assertFalse(c.candidate_satisfied)
        d = self.plan.assess_gate("G-D", self.plan.gate("G-D").members, True, ("fixture:evidence",))
        self.assertIn("WP-18", d.missing_dependencies)
        self.assertFalse(d.candidate_satisfied)

    def test_missing_member_and_missing_dependency_each_deny(self):
        for gate in self.plan.gates:
            closure = self.plan.dependency_closure(gate.members)
            for removed in closure:
                result = self.plan.assess_gate(gate.gate_id, tuple(x for x in closure if x != removed),
                                               True, ("fixture:evidence",))
                self.assertFalse(result.candidate_satisfied)
                self.assertIn(removed, result.missing_members + result.missing_dependencies)

    def test_unknown_duplicate_or_malformed_claims_and_source_drift_reject(self):
        self.reject("CONSTRUCTION_SOURCE_IDENTITY_MISMATCH", ConstructionPlan, self.wp_bytes + b"\n", self.gate_bytes)
        self.reject("CONSTRUCTION_SOURCE_IDENTITY_MISMATCH", ConstructionPlan, self.wp_bytes, self.gate_bytes + b"\n")
        self.reject("UNKNOWN_CONSTRUCTION_GATE", self.plan.gate, "G-I")
        for claims in (("WP-28",), ("WP-00", "WP-00"), ["WP-00"], (True,), self.all_ids * 2):
            self.reject("INVALID_COMPLETED_PACKAGE_CLAIMS", self.plan.construction_ready, claims)
        for value in (1, None, "true"):
            self.reject("INVALID_GATE_EVIDENCE_CLAIMS", self.plan.assess_gate, "G-A", self.all_ids, value, ())
        for refs in (["x"], ("x", "x"), ("x" * 1025,)):
            self.reject("INVALID_GATE_EVIDENCE_CLAIMS", self.plan.assess_gate, "G-A", self.all_ids, True, refs)

    def test_generic_graph_rejects_cycles_unknown_duplicates_and_malformed_edges(self):
        for graph, code in (
                ((("a", ("b",)), ("b", ("a",))), "CONSTRUCTION_DEPENDENCY_CYCLE"),
                ((("a", ("a",)),), "CONSTRUCTION_DEPENDENCY_CYCLE"),
                ((("a", ("missing",)),), "UNKNOWN_CONSTRUCTION_DEPENDENCY"),
                ((("a", ()), ("a", ())), "DUPLICATE_CONSTRUCTION_NODE"),
                ((("a", ("b", "b")), ("b", ())), "DUPLICATE_CONSTRUCTION_DEPENDENCY"),
                ((("a", ["b"]),), "INVALID_CONSTRUCTION_GRAPH"),
                ((), "INVALID_CONSTRUCTION_GRAPH")):
            self.reject(code, topological_order, graph)

    def test_model_is_immutable_and_source_ledgers_are_untouched(self):
        with self.assertRaises(FrozenInstanceError):
            self.plan.order = ()
        self.assertEqual((SOURCE / "build/work_packages.json").read_bytes(), self.wp_bytes)
        self.assertEqual((SOURCE / "build/gates.json").read_bytes(), self.gate_bytes)


if __name__ == "__main__":
    unittest.main()

