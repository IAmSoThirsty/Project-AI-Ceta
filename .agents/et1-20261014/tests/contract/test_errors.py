"""Synthetic error admission predicates; no actual failure, effect or retry."""
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts import ContractError, RecordCodec, canonical_bytes, strict_loads
from ceta.contracts.errors import (ERROR_PROFILE, MAX_ERROR_DEFINITIONS, ErrorCatalog,
                                   ErrorContract, ErrorDefinition)


class ErrorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codec = RecordCodec(strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes()))
        cls.catalog_raw = (ROOT / "contracts/error_catalog.json").read_bytes()
        cls.catalog = ErrorCatalog.from_wire(cls.catalog_raw)
        cls.contract = ErrorContract(cls.codec, cls.catalog)

    def setUp(self):
        self.error = {"record_type": "ErrorEnvelope", "schema_version": "1", "record_id": "error:1",
            "scope_id": "scope:fixture", "causation_ref": "request:1", "operation_id": "operation:1",
            "task_id": "task:1", "code": "AUTHORITY_MISSING", "phase": "PREPARATION",
            "recoverability": "RETRY_WITH_NEW_AUTHORITY", "effect_status": "NOT_STARTED",
            "retry_policy_ref": None, "affected_resources": [{"resource_id": "file:fixture",
                "revision": None, "access": "WRITE", "scope_id": "scope:fixture"}],
            "diagnostic_ref": None, "user_explanation": "Current authority is unavailable."}

    def decode(self, instance=None, **context):
        expected = {"scope_id": "scope:fixture", "task_id": "task:1", "operation_id": "operation:1"}
        expected.update(context)
        return self.contract.decode(canonical_bytes(self.error if instance is None else instance), **expected)

    def reject(self, code, fn, *args, **kwargs):
        with self.assertRaises(ContractError) as raised:
            fn(*args, **kwargs)
        self.assertEqual(raised.exception.code, code)

    def test_all_twenty_original_error_definitions_are_registered(self):
        original = strict_loads(self.catalog_raw)["errors"]
        self.assertEqual(len(original), 20)
        self.assertEqual(len(self.catalog.definitions), 20)
        for row in original:
            definition = self.catalog.lookup(row["code"])
            self.assertEqual(definition.category, row["category"])
            self.assertEqual(definition.next_action, row["next_action"])
            self.assertIs(definition.must_not_imply_completed_effect, True)
            instance = dict(self.error, code=row["code"], recoverability="RECONCILE",
                            effect_status="UNKNOWN")
            result = self.decode(instance)
            self.assertEqual(result.definition, definition)
            self.assertTrue(result.requires_reconciliation)

    def test_definition_and_catalog_reject_malformed_and_weakening_inputs(self):
        row = strict_loads(self.catalog_raw)["errors"][0]
        for field, bad in (("code", "bad code"), ("code", True), ("category", "SUCCESS"),
                           ("category", []), ("next_action", ""), ("next_action", "x" * 4097),
                           ("must_not_imply_completed_effect", False),
                           ("must_not_imply_completed_effect", 1)):
            with self.subTest(field=field, bad=bad):
                with self.assertRaises(ContractError):
                    ErrorCatalog.from_wire(canonical_bytes({"errors": [dict(row, **{field: bad})]}))
        for doc in ({}, {"errors": None}, {"errors": []}, {"errors": [row], "critical": True},
                    {"errors": [dict(row, extra=True)]}, {"errors": [dict(row, code=None)]}):
            with self.assertRaises(ContractError):
                ErrorCatalog.from_wire(canonical_bytes(doc))
        self.reject("DUPLICATE_ERROR_CODE", ErrorCatalog.from_wire,
                    canonical_bytes({"errors": [row, row]}))
        self.reject("INVALID_ERROR_CATALOG", ErrorCatalog.from_wire,
                    canonical_bytes({"errors": [row] * (MAX_ERROR_DEFINITIONS + 1)}))
        self.reject("INVALID_ERROR_CATALOG", ErrorCatalog, list(self.catalog.definitions))
        self.reject("INVALID_ERROR_CATALOG", ErrorCatalog, (row,))
        for guidance in ("e\u0301", "\ud800"):
            with self.assertRaises(ContractError):
                ErrorDefinition("AUTHORITY_MISSING", "DENIED", guidance)

    def test_catalog_rejects_duplicate_keys_and_unsupported_json_before_semantics(self):
        self.reject("DUPLICATE_KEY", ErrorCatalog.from_wire, b'{"errors":[],"errors":[]}')
        self.reject("NON_INTEGER_NUMBER", ErrorCatalog.from_wire, b'{"errors":1.0}')
        self.reject("UNREGISTERED_ERROR_CODE", self.catalog.lookup, "MISSING")
        self.reject("UNREGISTERED_ERROR_CODE", self.catalog.lookup, True)

    def test_catalog_identity_is_order_independent_and_binds_every_definition(self):
        other = ErrorCatalog(tuple(reversed(self.catalog.definitions)))
        self.assertEqual(other.commitment(), self.catalog.commitment())
        self.assertEqual(self.catalog.commitment(), "sha256:" + hashlib.sha256(
            b"CETA:error-catalog:" + ERROR_PROFILE.encode() + b"\0" + self.catalog.canonical_wire()).hexdigest())
        first = self.catalog.definitions[0]
        amended = ErrorDefinition(first.code, first.category, first.next_action + " Revised.")
        self.assertNotEqual(ErrorCatalog((amended,) + self.catalog.definitions[1:]).commitment(),
                            self.catalog.commitment())
        self.reject("UNKNOWN_RECORD_TYPE", self.codec.decode, self.catalog.canonical_wire())

    def test_valid_error_preserves_original_bytes_and_declared_effect_state(self):
        raw = json.dumps(self.error, indent=2).encode()
        result = self.contract.decode(raw, scope_id="scope:fixture", task_id="task:1", operation_id="operation:1")
        self.assertEqual(result.record.original_wire, raw)
        self.assertEqual(result.record.as_dict(), self.error)
        self.assertEqual(result.record.commitment, self.codec.decode(raw).commitment)
        self.assertEqual(result.catalog_commitment, self.catalog.commitment())
        self.assertFalse(result.requires_reconciliation)
        explicitly_reconcile = self.decode(dict(self.error, recoverability="RECONCILE"))
        self.assertTrue(explicitly_reconcile.requires_reconciliation)
        # A reference is only a reference; no dispatcher or retry admission exists.
        self.error["retry_policy_ref"] = "policy:untrusted-reference"
        self.assertEqual(self.decode().record.as_dict()["retry_policy_ref"], "policy:untrusted-reference")

    def test_uncertain_effects_require_reconciliation_under_every_other_error_category(self):
        for status in ("UNKNOWN", "MAY_HAVE_EXECUTED"):
            for recovery in ("RETRY_WITH_NEW_AUTHORITY", "REQUIRES_DECISION", "REQUIRES_RESOURCE", "PERMANENT_FOR_REQUEST"):
                instance = dict(self.error, effect_status=status, recoverability=recovery)
                self.reject("ERROR_EFFECT_RECONCILIATION_REQUIRED", self.decode, instance)
            accepted = self.decode(dict(self.error, effect_status=status, recoverability="RECONCILE"))
            self.assertEqual(accepted.record.as_dict()["effect_status"], status)
            self.assertTrue(accepted.requires_reconciliation)

    def test_observed_effect_is_not_success_or_permission_to_repeat(self):
        self.reject("ERROR_EFFECT_RECONCILIATION_REQUIRED", self.decode,
                    dict(self.error, effect_status="OBSERVED_EFFECT"))
        for recovery in ("RECONCILE", "REQUIRES_DECISION", "REQUIRES_RESOURCE", "PERMANENT_FOR_REQUEST"):
            result = self.decode(dict(self.error, effect_status="OBSERVED_EFFECT", recoverability=recovery))
            self.assertTrue(result.requires_reconciliation)
            self.assertEqual(result.record.as_dict()["effect_status"], "OBSERVED_EFFECT")

    def test_consumed_permit_and_pending_stop_do_not_become_fresh_retries(self):
        for code in ("PERMIT_CONSUMED", "STOP_PENDING"):
            self.reject("ERROR_EFFECT_RECONCILIATION_REQUIRED", self.decode, dict(self.error, code=code))
            result = self.decode(dict(self.error, code=code, recoverability="RECONCILE"))
            self.assertTrue(result.requires_reconciliation)
        self.reject("ERROR_EFFECT_STATUS_CONTRADICTION", self.decode,
                    dict(self.error, code="EFFECT_INDETERMINATE", recoverability="RECONCILE"))

    def test_record_scope_task_and_operation_are_exact_expected_context(self):
        for field in ("scope_id", "task_id", "operation_id"):
            self.reject("ERROR_CONTEXT_MISMATCH", self.decode, dict(self.error, **{field: "foreign:1"}))
        for field in ("task_id", "operation_id"):
            self.reject("ERROR_CONTEXT_MISMATCH", self.decode, dict(self.error, **{field: None}))
        instance = dict(self.error, operation_id=None, task_id=None)
        self.assertEqual(self.decode(instance, operation_id=None, task_id=None).record.as_dict(), instance)
        for field, invalid in (("scope_id", None), ("scope_id", True), ("scope_id", "x" * 161),
                                ("task_id", "bad id"), ("operation_id", 1)):
            self.reject("INVALID_ERROR_CONTEXT", self.decode, **{field: invalid})

    def test_resource_scope_rejects_foreign_context_without_inventing_missing_revision(self):
        self.assertIsNone(self.decode().record.as_dict()["affected_resources"][0]["revision"])
        self.error["affected_resources"][0]["scope_id"] = "scope:foreign"
        self.reject("ERROR_RESOURCE_SCOPE_MISMATCH", self.decode)

    def test_unknown_code_wrong_record_and_strict_wire_reject_without_echoing_private_text(self):
        secret = "private-fixture-value"
        self.error["code"] = secret
        with self.assertRaises(ContractError) as raised:
            self.decode()
        self.assertEqual(raised.exception.code, "UNREGISTERED_ERROR_CODE")
        self.assertNotIn(secret, str(raised.exception))
        fixture = strict_loads((ROOT / "contracts/examples/observation_shape_valid.json").read_bytes())["instance"]
        self.reject("ERROR_ENVELOPE_REQUIRED", self.decode, fixture)
        self.error["code"] = "AUTHORITY_MISSING"
        self.error["unknown_field"] = secret
        with self.assertRaises(ContractError):
            self.decode()

    def test_immutable_copies_do_not_reclassify_a_prior_error(self):
        result = self.decode()
        with self.assertRaises(FrozenInstanceError):
            result.definition.category = "SUCCESS"
        with self.assertRaises(FrozenInstanceError):
            self.catalog.definitions = ()
        with self.assertRaises(FrozenInstanceError):
            result.catalog_commitment = "changed"
        copy = result.record.as_dict()
        copy["effect_status"] = "OBSERVED_EFFECT"
        copy["affected_resources"][0]["scope_id"] = "scope:foreign"
        self.assertEqual(result.record.as_dict(), self.error)
        self.reject("ERROR_CONTRACT_INPUT_REQUIRED", ErrorContract, self.codec, {})


if __name__ == "__main__":
    unittest.main()
