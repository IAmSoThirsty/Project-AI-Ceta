"""Relevant state fixtures; no real admission, race, grant or resource handle."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts import ContractError, RecordCodec, strict_loads
from ceta.contracts.read_sets import ReadSet, ResourceRevision, require_current_preparation

H1, H2, H3 = ("sha256:" + c * 64 for c in "abc")


class ReadSetTests(unittest.TestCase):
    def setUp(self):
        self.file = ResourceRevision("file:target", H1)
        self.input = ResourceRevision("artifact:input", H2)
        self.prepared = ReadSet("project:1", 4, 7, H1, H2, (self.file, self.input))
        self.required = ("file:target", "artifact:input")

    def reject(self, code, fn, *args):
        with self.assertRaises(ContractError) as raised:
            fn(*args)
        self.assertEqual(raised.exception.code, code)

    def test_exact_current_state_satisfies_only_the_comparison_predicate(self):
        self.assertIsNone(require_current_preparation(self.prepared, self.prepared, self.required))

    def test_unrelated_resource_activity_does_not_invalidate_preparation(self):
        before = replace(self.prepared, resources=self.prepared.resources + (ResourceRevision("file:unrelated", H1),))
        after = replace(before, resources=self.prepared.resources + (ResourceRevision("file:unrelated", H3),))
        self.assertNotEqual(before.commitment(), after.commitment())
        require_current_preparation(self.prepared, before, self.required)
        require_current_preparation(self.prepared, after, self.required)

    def test_relevant_resource_changes_and_missing_evidence_reject(self):
        for resource in self.prepared.resources:
            changed = tuple(replace(r, revision=H3) if r == resource else r for r in self.prepared.resources)
            with self.subTest(resource=resource.resource_id):
                self.reject("RESOURCE_REVISION_CHANGED", require_current_preparation,
                            self.prepared, replace(self.prepared, resources=changed), self.required)
        missing = replace(self.prepared, resources=(self.file,))
        self.reject("CURRENT_RESOURCE_REVISION_MISSING", require_current_preparation,
                    self.prepared, missing, self.required)

    def test_authority_fence_policy_environment_and_scope_changes_reject(self):
        for field, value, code in (
            ("authority_generation", 5, "AUTHORITY_GENERATION_CHANGED"),
            ("fence_generation", 8, "FENCE_GENERATION_CHANGED"),
            ("policy_commitment", H3, "POLICY_REVISION_CHANGED"),
            ("environment_commitment", H3, "ENVIRONMENT_REVISION_CHANGED"),
            ("scope_id", "project:other", "READ_SET_SCOPE_MISMATCH"),
        ):
            with self.subTest(field=field):
                self.reject(code, require_current_preparation,
                            self.prepared, replace(self.prepared, **{field: value}), self.required)

    def test_rollback_generations_reject_as_well_as_advancement(self):
        for field, code in (("authority_generation", "AUTHORITY_GENERATION_CHANGED"),
                            ("fence_generation", "FENCE_GENERATION_CHANGED")):
            self.reject(code, require_current_preparation,
                        self.prepared, replace(self.prepared, **{field: 0}), self.required)

    def test_omitted_and_extra_prepared_dependencies_reject(self):
        omitted = replace(self.prepared, resources=(self.file,))
        extra = replace(self.prepared, resources=self.prepared.resources + (ResourceRevision("file:extra", H3),))
        for expected in (omitted, extra):
            self.reject("READ_SET_DEPENDENCY_MISMATCH", require_current_preparation,
                        expected, self.prepared, self.required)

    def test_current_values_are_not_invented_from_null_revisions(self):
        self.reject("INVALID_REVISION_COMMITMENT", ResourceRevision, "file:target", None)
        for value in ("sha256:" + "0" * 63, "SHA256:" + "a" * 64, "mtime:1", True, []):
            self.reject("INVALID_REVISION_COMMITMENT", ResourceRevision, "file:target", value)

    def test_exact_counter_types_identifiers_duplicate_and_bound_rejections(self):
        for field in ("authority_generation", "fence_generation"):
            for value in (True, -1, 1.5, 2**53, None):
                with self.subTest(field=field, value=value), self.assertRaises(ContractError):
                    replace(self.prepared, **{field: value})
        for value in ([], "", "file:target\n", "x" * 161):
            self.reject("INVALID_READ_SET_IDENTIFIER", ResourceRevision, value, H1)
        for resources in ([], (), (None,), (self.file, self.file), (self.file,) * 4097):
            with self.subTest(length=len(resources)), self.assertRaises(ContractError):
                replace(self.prepared, resources=resources)

    def test_required_dependencies_reject_malformed_duplicate_and_unbounded_lists(self):
        for required in ([], (), (None,), ("file:target", "file:target"), ("x",) * 4097):
            with self.subTest(required_type=type(required).__name__), self.assertRaises(ContractError):
                require_current_preparation(self.prepared, self.prepared, required)
        self.reject("READ_SET_REQUIRED", require_current_preparation, {}, self.prepared, self.required)
        self.reject("READ_SET_REQUIRED", require_current_preparation, self.prepared, {}, self.required)

    def test_order_independent_canonical_identity_with_explicit_domain_and_profile(self):
        reordered = replace(self.prepared, resources=tuple(reversed(self.prepared.resources)))
        self.assertEqual(reordered.canonical_wire(), self.prepared.canonical_wire())
        self.assertEqual(reordered.commitment(), self.prepared.commitment())
        value = json.loads(self.prepared.canonical_wire())
        self.assertEqual(value["contract_type"], "RelevantReadSet")
        self.assertEqual(value["contract_version"], "1")
        self.assertEqual(value["read_set_profile"], "ceta-relevant-state-v1")
        self.assertEqual(value["resources"], [
            {"resource_id": "artifact:input", "revision": H2}, {"resource_id": "file:target", "revision": H1}])
        self.assertEqual(self.prepared.commitment(), "sha256:" + hashlib.sha256(
            b"CETA:read-set:ceta-relevant-state-v1\0" + self.prepared.canonical_wire()).hexdigest())

    def test_every_relevant_field_changes_preparation_identity(self):
        for field, value in (("scope_id", "project:2"), ("authority_generation", 5),
                             ("fence_generation", 8), ("policy_commitment", H3),
                             ("environment_commitment", H3),
                             ("resources", (replace(self.file, revision=H3), self.input))):
            with self.subTest(field=field):
                self.assertNotEqual(self.prepared.commitment(), replace(self.prepared, **{field: value}).commitment())

    def test_immutable_values_and_no_silent_record_dispatch_amendment(self):
        with self.assertRaises(FrozenInstanceError):
            self.file.revision = H3
        with self.assertRaises(FrozenInstanceError):
            self.prepared.resources = ()
        codec = RecordCodec(strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes()))
        self.reject("UNKNOWN_RECORD_TYPE", codec.decode, self.prepared.canonical_wire())


if __name__ == "__main__":
    unittest.main()
