"""Bounded ingress contracts; parsing is never OS identity or positive authority.

These are narrower deterministic fixtures, not original B063/B068 completion.
"""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.contracts.local_ipc import (IPC_PROFILE, MAX_MESSAGE_TTL_MS,
    MAX_REPLAY_ENTRIES, IngressState, decode_message, encode_message)
from ceta.contracts.wire import (ContractError, MAX_WIRE_BYTES, RecordCodec,
    canonical_bytes, strict_loads)
from test_all_records import example


class LocalIpcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())
        cls.codec = RecordCodec(cls.schema)

    def setUp(self):
        self.record = example(self.schema["$defs"]["ActionProposal"])
        self.record.update(record_id="proposal:ipc-fixture", scope_id="project:ipc-fixture")
        self.record_wire = canonical_bytes(self.record)
        self.wire = self.message()
        self.value = strict_loads(self.wire)

    def message(self, *, record_wire=None, **changes):
        values = dict(message_id="message:fixture", sender_session="session:fixture",
            receiver_generation="service:fixture", operation="kernel.prepare",
            issued_at_ms=1000, expires_at_ms=2000, correlation_ref="request:fixture",
            causation_ref="cause:fixture")
        values.update(changes)
        return encode_message(self.record_wire if record_wire is None else record_wire,
                              self.codec, **values)

    def reject(self, call, code=None):
        with self.assertRaises(ContractError) as caught:
            call()
        if code is not None:
            self.assertEqual(caught.exception.code, code)

    def reject_value(self, value, code=None):
        self.reject(lambda: decode_message(canonical_bytes(value), self.codec), code)

    def accept(self, state, message=None, **changes):
        inputs = dict(authenticated_session="session:fixture",
            allowed_operations=("kernel.prepare",), allowed_scopes=("project:ipc-fixture",),
            now_ms=1500)
        inputs.update(changes)
        return state.accept(decode_message(self.wire, self.codec) if message is None else message,
                            **inputs)

    def test_exact_inner_bytes_and_both_commitments_survive_round_trip(self):
        original = json.dumps(self.record, indent=2).encode("utf8")
        wire = self.message(record_wire=original)
        message = decode_message(wire, self.codec)
        self.assertEqual(message.record.original_wire, original)
        self.assertNotEqual(original, message.record.canonical_wire)
        self.assertEqual(message.original_message, wire)
        value = strict_loads(wire)
        self.assertEqual(value["original_record_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(value["record_commitment"], self.codec.decode(original).commitment)

    def test_each_route_requires_its_original_record_and_revoke_reason(self):
        for operation, kind in (("kernel.prepare", "ActionProposal"),
                ("kernel.consume", "OperationPermit"), ("kernel.revoke", "StandingGrant"),
                ("kernel.resolve_consumption", "OperationPermit")):
            with self.subTest(operation=operation):
                record = example(self.schema["$defs"][kind])
                record["scope_id"] = "project:ipc-fixture"
                wire = self.message(record_wire=canonical_bytes(record), operation=operation,
                                    reason_ref="reason:fixture" if operation == "kernel.revoke" else None)
                message = decode_message(wire, self.codec)
                self.assertEqual((message.operation, message.record.record_type), (operation, kind))
                self.assertEqual(message.reason_ref, "reason:fixture" if operation == "kernel.revoke" else None)

    def test_unknown_or_missing_envelope_fields_do_not_supply_authority(self):
        for field in ("authenticated", "pid", "role", "owner_says_allow", "critical_future_field"):
            with self.subTest(extra=field):
                self.reject_value(dict(self.value, **{field: True}), "IPC_MESSAGE_FIELDS")
        for field in self.value:
            with self.subTest(missing=field):
                changed = dict(self.value)
                del changed[field]
                self.reject_value(changed, "IPC_MESSAGE_FIELDS")

    def test_duplicate_keys_and_nonobject_envelopes_are_rejected(self):
        duplicate = self.wire[:-1] + b',"version":1}'
        self.reject(lambda: decode_message(duplicate, self.codec), "DUPLICATE_KEY")
        for value in ([], None, True, "text"):
            with self.subTest(value=value):
                self.reject_value(value, "IPC_MESSAGE_FIELDS")

    def test_profile_and_exact_version_type_are_bound(self):
        self.reject_value(dict(self.value, profile="unrelated-profile"), "IPC_MESSAGE_VERSION")
        for version in (True, False, 0, 2, "1", None):
            with self.subTest(version=version):
                self.reject_value(dict(self.value, version=version), "IPC_MESSAGE_VERSION")

    def test_unsupported_routes_and_wrong_record_type_are_denied(self):
        for operation in ("shell.execute", "kernel.allow", "", None, ["kernel.prepare"]):
            with self.subTest(operation=operation):
                self.reject_value(dict(self.value, operation=operation), "IPC_OPERATION_UNAVAILABLE")
        self.reject_value(dict(self.value, operation="kernel.consume"), "IPC_OPERATION_SCOPE_BINDING")

    def test_scope_canonical_commitment_and_original_byte_commitment_are_independent(self):
        mutations = ({"scope_id": "project:other"},
            {"record_commitment": "sha256:" + "0" * 64},
            {"original_record_sha256": "0" * 64},
            {"record_wire": json.dumps(self.record, indent=2)})
        for mutation in mutations:
            with self.subTest(mutation=tuple(mutation)):
                self.reject_value(dict(self.value, **mutation))

    def test_nested_record_unknown_authority_fields_are_rejected(self):
        record = dict(self.record, owner_says_allow=True)
        changed = dict(self.value, record_wire=json.dumps(record))
        self.reject_value(changed)

    def test_arguments_are_exact_and_revoke_requires_identifier(self):
        for arguments in (None, [], {"reason_ref": "reason:fixture"}, {"authenticated": True}):
            with self.subTest(arguments=arguments):
                self.reject_value(dict(self.value, arguments=arguments), "IPC_ARGUMENTS")
        self.reject(lambda: self.message(reason_ref="reason:unexpected"), "IPC_UNEXPECTED_ARGUMENT")
        grant = canonical_bytes(example(self.schema["$defs"]["StandingGrant"]))
        for reason in (None, "", {}, True):
            with self.subTest(reason=reason):
                self.reject(lambda: self.message(record_wire=grant, operation="kernel.revoke", reason_ref=reason))

    def test_validity_requires_exact_integer_bounded_positive_interval(self):
        for start, end in ((True, 2000), (1000, True), (-1, 1000), (1000, 1000),
                (1001, 1000), (0, MAX_MESSAGE_TTL_MS + 1), ("1000", 2000)):
            with self.subTest(start=start, end=end):
                self.reject_value(dict(self.value, issued_at_ms=start, expires_at_ms=end), "IPC_VALIDITY_SHAPE")
        message = decode_message(self.message(issued_at_ms=0, expires_at_ms=MAX_MESSAGE_TTL_MS), self.codec)
        self.assertEqual(message.expires_at_ms - message.issued_at_ms, MAX_MESSAGE_TTL_MS)

    def test_message_size_type_and_codec_are_bounded_before_decode(self):
        for value in (b"", b"x" * (MAX_WIRE_BYTES + 1), bytearray(self.wire), self.wire.decode("utf8"), None):
            with self.subTest(kind=type(value).__name__):
                self.reject(lambda: decode_message(value, self.codec), "IPC_MESSAGE_SIZE_OR_CODEC")
        self.reject(lambda: decode_message(self.wire, object()), "IPC_MESSAGE_SIZE_OR_CODEC")

    def test_server_checks_session_generation_origin_operation_and_scope(self):
        for change, code in (({"authenticated_session": "session:other"}, "IPC_SESSION_BINDING"),
                ({"allowed_operations": ("kernel.consume",)}, "IPC_CALLER_SCOPE_DENIED"),
                ({"allowed_scopes": ("project:other",)}, "IPC_CALLER_SCOPE_DENIED")):
            with self.subTest(change=change):
                state = IngressState("service:fixture")
                self.reject(lambda: self.accept(state, **change), code)
                self.accept(state)  # A denied origin did not consume the legitimate message.
        state = IngressState("service:current")
        self.reject(lambda: self.accept(state), "IPC_STALE_RECEIVER")

    def test_receipt_validity_is_inclusive_start_exclusive_expiry(self):
        for now in (999, 2000, 2001):
            with self.subTest(now=now):
                state = IngressState("service:fixture")
                self.reject(lambda: self.accept(state, now_ms=now), "IPC_MESSAGE_EXPIRED_OR_FUTURE")
                self.accept(state, now_ms=1000)
        self.reject(lambda: self.accept(IngressState("service:fixture"), now_ms=True), "IPC_MESSAGE_REQUIRED")

    def test_replay_consumes_before_any_dispatch_result(self):
        state = IngressState("service:fixture")
        self.accept(state)
        self.reject(lambda: self.accept(state), "IPC_MESSAGE_REPLAY")
        another = decode_message(self.message(message_id="message:next"), self.codec)
        self.accept(state, another)

    def test_replay_capacity_denies_without_evicting_existing_messages(self):
        state = IngressState("service:fixture")
        for number in range(MAX_REPLAY_ENTRIES):
            message = decode_message(self.message(message_id=f"message:capacity:{number}"), self.codec)
            self.accept(state, message)
        fresh = decode_message(self.message(message_id="message:over-capacity"), self.codec)
        self.reject(lambda: self.accept(state, fresh), "IPC_REPLAY_CAPACITY_EXHAUSTED")
        self.reject(lambda: self.accept(state, decode_message(self.message(message_id="message:capacity:0"), self.codec)), "IPC_MESSAGE_REPLAY")
        self.reject(lambda: self.accept(state, fresh), "IPC_REPLAY_CAPACITY_EXHAUSTED")

    def test_old_generation_message_cannot_be_replayed_at_new_receiver(self):
        self.accept(IngressState("service:fixture"))
        self.reject(lambda: self.accept(IngressState("service:restarted")), "IPC_STALE_RECEIVER")


if __name__ == "__main__":
    unittest.main()
