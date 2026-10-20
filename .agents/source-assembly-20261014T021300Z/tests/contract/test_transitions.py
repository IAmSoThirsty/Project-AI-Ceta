"""Pure predicate fixtures only; no B-case runtime qualification or state writes."""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.wire import ContractError
from ceta.contracts.transitions import PredicateWitness, TransitionModel


class TransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog_bytes = (ROOT / "contracts/state_catalog.json").read_bytes()
        cls.rules_bytes = (ROOT / "contracts/transition_rules.json").read_bytes()
        cls.schema_bytes = (ROOT / "contracts/schemas/records.schema.json").read_bytes()
        cls.custody_bytes = (SOURCE / "docs/specification/25_defensive_vault_custody.md").read_bytes()
        cls.model = TransitionModel(cls.catalog_bytes, cls.rules_bytes, cls.schema_bytes, cls.custody_bytes)

    def witnesses(self, rule):
        return tuple(PredicateWitness(g.name, g.required_provider, True,
                                      ("fixture:" + rule.rule_id + ":" + g.name,))
                     for g in rule.guards)

    def assess(self, rule, witnesses):
        return self.model.assess(rule.domain, rule.from_state, rule.to_state, witnesses)

    def reject(self, code, fn, *args):
        with self.assertRaises(ContractError) as raised:
            fn(*args)
        self.assertEqual(raised.exception.code, code)

    def test_every_catalog_state_record_enum_principal_predicate_and_case_is_preserved(self):
        catalog = json.loads(self.catalog_bytes)
        self.assertEqual(dict(self.model.catalog),
                         {key: tuple(value) for key, value in catalog.items() if isinstance(value, list)})
        schema = json.loads(self.schema_bytes)
        enums = tuple((name, field, tuple(value["enum"]))
                      for name, definition in schema["$defs"].items()
                      for field, value in definition.get("properties", {}).items() if "enum" in value)
        self.assertEqual(self.model.record_enumerations, enums)
        rules = json.loads(self.rules_bytes)["rules"]
        self.assertEqual(len(self.model.rules), 20)
        for actual, source in zip(self.model.rules, rules):
            with self.subTest(rule=actual.rule_id):
                self.assertEqual((actual.rule_id, actual.domain, actual.from_state, actual.to_state,
                                  actual.required_predicate, actual.on_failure, actual.acceptance_ids),
                                 (source["id"], source["domain"], source["from"], source["to"],
                                  source["required_predicate"], source["on_failure"],
                                  tuple(source["acceptance_ids"])))

    def test_legitimate_complete_predicates_are_positive_only_for_supported_principal_entries(self):
        for rule in self.model.rules:
            with self.subTest(rule=rule.rule_id):
                result = self.assess(rule, self.witnesses(rule))
                self.assertTrue(result.predicates_satisfied)
                self.assertFalse(result.runtime_authorized)
                self.assertEqual(result.implementation_status, "IMPLEMENTED_NOT_QUALIFIED")
                self.assertEqual(result.direct_edge_supported, not bool(rule.unresolved_intermediates or rule.required_intermediates))
                self.assertEqual(result.acceptance_ids, rule.acceptance_ids)

    def test_all_six_ambiguous_entries_deny_even_all_positive_witnesses(self):
        expected = {"TR-04": ("CLAIMED",), "TR-06": ("VALIDATED",),
                    "TR-09": ("DISPATCHED",), "TR-11": ("OBSERVED",),
                    "TR-13": ("OBSERVING", "RESOLVED_CURRENT_STATE"),
                    "TR-20": ("AWAITING_CUTOVER",)}
        self.assertEqual({r.rule_id: r.unresolved_intermediates for r in self.model.rules
                          if r.unresolved_intermediates}, expected)
        for rule_id, intermediate in expected.items():
            rule = self.model.rule(rule_id)
            result = self.assess(rule, self.witnesses(rule))
            self.assertEqual(result.reason, "VERIFIED_UNRESOLVED")
            self.assertFalse(result.direct_edge_supported)
            self.assertFalse(result.runtime_authorized)
            self.assertEqual(result.unresolved_intermediates, intermediate)
            # Intermediates remain named, but this implementation invents no subedge.
            for state in intermediate:
                held = self.model.assess(rule.domain, rule.from_state, state, ())
                self.assertEqual(held.reason, "VERIFIED_UNRESOLVED")
                self.assertFalse(held.direct_edge_supported)

    def test_missing_false_empty_or_wrong_owner_denies_every_guard(self):
        for rule in self.model.rules + self.model.direct_edges:
            original = self.witnesses(rule)
            for index, guard in enumerate(rule.guards):
                missing = original[:index] + original[index + 1:]
                bad = [missing]
                for change in ({"satisfied": False}, {"evidence_refs": ()},
                               {"provider_component": "CMP-09"}):
                    bad.append(original[:index] + (replace(original[index], **change),)
                               + original[index + 1:])
                for witnesses in bad:
                    with self.subTest(rule=rule.rule_id, guard=guard.name):
                        result = self.assess(rule, witnesses)
                        self.assertFalse(result.predicates_satisfied)
                        self.assertFalse(result.direct_edge_supported)
                        self.assertIn(guard.name, result.unmet_predicates)

    def test_admission_replay_revocation_race_storage_failure_and_false_exit_claims_deny(self):
        for rule_id, guard in (
                ("TR-07", "reservation_and_intent_committed_atomically"),
                ("TR-08", "fence_permit_revocation_current"),
                ("TR-08", "permit_consumed_once_at_admission"),
                ("TR-08", "actual_resource_handle_preconditions_valid"),
                ("TR-10", "actual_owned_process_termination_observed"),
                ("TR-15", "owned_workers_observed_stopped"),
                ("TR-18", "declared_tests_thresholds_real_configuration_match")):
            rule = self.model.rule(rule_id)
            witnesses = tuple(replace(w, satisfied=False) if w.predicate == guard else w
                              for w in self.witnesses(rule))
            result = self.assess(rule, witnesses)
            self.assertFalse(result.direct_edge_supported)
            self.assertIn(guard, result.unmet_predicates)
        # These are negative predicate fixtures, not actual races or process tests.

    def test_no_implicit_effect_replay_qualification_or_stop_shortcuts(self):
        for domain, before, after in (
                ("EFFECT", "INDETERMINATE", "RUNNING"),
                ("EFFECT", "PROCESS_EXITED", "VERIFIED"),
                ("SUPERVISOR", "ACTIVE", "STOPPED"),
                ("QUALIFICATION", "NOT_QUALIFIED", "QUALIFIED_WITHIN_SCOPE"),
                ("MEMORY", "ACTIVE", "DELETED_PAYLOAD"),
                ("QUEUE", "PENDING", "COMPLETED")):
            result = self.model.assess(domain, before, after, ())
            self.assertFalse(result.direct_edge_supported)
            self.assertFalse(result.runtime_authorized)

    def test_source_defined_four_vault_edges_are_positive_and_principal_shortcuts_deny(self):
        edges = tuple(r for r in self.model.direct_edges if r.domain == "VAULT")
        self.assertEqual(tuple((r.from_state, r.to_state) for r in edges),
                         (("SEALED", "VERIFYING"), ("VERIFYING", "AUTHORIZED_RELEASE"),
                          ("AUTHORIZED_RELEASE", "ZEROIZING"), ("ZEROIZING", "SEALED")))
        for edge in edges:
            result = self.assess(edge, self.witnesses(edge))
            self.assertTrue(result.direct_edge_supported)
            self.assertFalse(result.runtime_authorized)
            self.assertFalse(self.assess(edge, ()).direct_edge_supported)
        for rule_id, state in (("TR-16", "VERIFYING"), ("TR-17", "ZEROIZING")):
            principal = self.model.rule(rule_id)
            self.assertEqual(principal.required_intermediates, (state,))
            result = self.assess(principal, self.witnesses(principal))
            self.assertEqual(result.reason, "SOURCE_DEFINED_SEQUENCE_SHORTCUT_DENIED")
            self.assertFalse(result.direct_edge_supported)
        # No undocumented tamper/recovery/ordinary-decryption fallback is added.
        self.assertFalse(self.model.assess("VAULT", "SEALED", "RECOVERY", ()).direct_edge_supported)

    def test_source_byte_drift_is_rejected_even_semantically_equivalent_json(self):
        for index, raw in enumerate((self.catalog_bytes, self.rules_bytes, self.schema_bytes, self.custody_bytes)):
            inputs = [self.catalog_bytes, self.rules_bytes, self.schema_bytes, self.custody_bytes]
            inputs[index] = raw + b"\n"
            self.reject("TRANSITION_SOURCE_IDENTITY_MISMATCH", TransitionModel, *inputs)

    def test_unknown_states_predicates_duplicates_invalid_types_and_bounds_reject(self):
        self.reject("UNKNOWN_TRANSITION_RULE", self.model.rule, "TR-21")
        self.reject("UNKNOWN_TRANSITION_STATE", self.model.assess, "EFFECT", "UNKNOWN", "RUNNING", ())
        rule = self.model.rule("TR-08")
        witnesses = self.witnesses(rule)
        self.reject("DUPLICATE_TRANSITION_WITNESS", self.assess, rule, witnesses + witnesses[:1])
        self.reject("UNKNOWN_TRANSITION_PREDICATE", self.assess, rule,
                    (replace(witnesses[0], predicate="model_said_allow"),))
        self.reject("INVALID_TRANSITION_WITNESSES", self.assess, rule, list(witnesses))
        self.reject("INVALID_TRANSITION_WITNESSES", self.assess, rule, (None,))
        for satisfied in (1, None, "true"):
            self.reject("INVALID_TRANSITION_WITNESS", PredicateWitness, "x", "CMP-02", satisfied, ())
        for refs in (["x"], ("x", "x"), ("x" * 1025,), ("x",) * 65):
            self.reject("INVALID_TRANSITION_WITNESS", PredicateWitness, "x", "CMP-02", True, refs)

    def test_snapshots_and_results_are_immutable_and_do_not_mutate_input_sources(self):
        with self.assertRaises(FrozenInstanceError):
            self.model.rules = ()
        result = self.assess(self.model.rule("TR-01"), ())
        with self.assertRaises(FrozenInstanceError):
            result.runtime_authorized = True
        self.assertEqual((ROOT / "contracts/state_catalog.json").read_bytes(), self.catalog_bytes)
        self.assertEqual((ROOT / "contracts/transition_rules.json").read_bytes(), self.rules_bytes)
        self.assertEqual((ROOT / "contracts/schemas/records.schema.json").read_bytes(), self.schema_bytes)


if __name__ == "__main__":
    unittest.main()

