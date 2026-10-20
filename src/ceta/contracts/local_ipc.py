"""Versioned local ingress; decoded messages never establish permission."""
from dataclasses import dataclass
import hashlib

from .kernel_transactions import require
from .store_transactions import identifier
from .wire import ContractError, MAX_WIRE_BYTES, RecordCodec, ParsedRecord, canonical_bytes, strict_loads

from .task_drafts import TaskCommand, TASK_OPERATIONS, decode_command

IPC_PROFILE = "ceta-local-ingress-v1"
MAX_MESSAGE_TTL_MS = 30_000
MAX_REPLAY_ENTRIES = 4096
OPERATIONS = {"kernel.prepare": "ActionProposal", "kernel.consume": "OperationPermit",
              "kernel.revoke": "StandingGrant", "kernel.resolve_consumption": "OperationPermit",
              "kernel.recover_permit": "OperationPermit", "kernel.recover_preparation": "ActionProposal", **{op: "TaskCommand" for op in TASK_OPERATIONS}}
FIELDS = {"profile", "version", "message_id", "correlation_ref", "causation_ref",
          "sender_session", "receiver_generation", "operation", "scope_id", "issued_at_ms",
          "expires_at_ms", "record_commitment", "original_record_sha256", "record_wire", "arguments"}


class SubmissionUncertain(ContractError):
    """The trusted controller retained this attempt before dispatch failed.

    This correlation carries no proof of delivery, COMMIT, rollback or effect.
    """
    def __init__(self, attempt):
        require(type(attempt) is str and len(attempt) == 32
                and all(character in "0123456789abcdef" for character in attempt),
                "IPC_SUBMISSION_ATTEMPT_REQUIRED")
        super().__init__("IPC_SUBMISSION_UNCERTAIN")
        self.attempt = attempt


@dataclass(frozen=True)
class LocalMessage:
    message_id: str
    sender_session: str
    receiver_generation: str
    operation: str
    scope_id: str
    issued_at_ms: int
    expires_at_ms: int
    record: ParsedRecord | TaskCommand
    reason_ref: str | None
    original_message: bytes


def encode_message(record_wire, codec, *, message_id, sender_session, receiver_generation,
                   operation, issued_at_ms, expires_at_ms, correlation_ref=None,
                   causation_ref=None, reason_ref=None):
    require(type(record_wire) is bytes and type(codec) is RecordCodec, "IPC_RECORD_REQUIRED")
    record = decode_command(record_wire) if operation in TASK_OPERATIONS else codec.decode(record_wire)
    value = {"profile": IPC_PROFILE, "version": 1, "message_id": message_id,
             "correlation_ref": correlation_ref, "causation_ref": causation_ref,
             "sender_session": sender_session, "receiver_generation": receiver_generation,
             "operation": operation, "scope_id": record.as_dict()["scope_id"],
             "issued_at_ms": issued_at_ms, "expires_at_ms": expires_at_ms,
             "record_commitment": record.commitment,
             "original_record_sha256": hashlib.sha256(record_wire).hexdigest(),
             "record_wire": record_wire.decode("utf8"),
             "arguments": {"reason_ref": reason_ref} if operation == "kernel.revoke" else {}}
    require(operation == "kernel.revoke" or reason_ref is None, "IPC_UNEXPECTED_ARGUMENT")
    wire = canonical_bytes(value)
    decode_message(wire, codec)
    return wire


def decode_message(wire, codec):
    require(type(wire) is bytes and 1 <= len(wire) <= MAX_WIRE_BYTES
            and type(codec) is RecordCodec, "IPC_MESSAGE_SIZE_OR_CODEC")
    value = strict_loads(wire)
    require(type(value) is dict and set(value) == FIELDS, "IPC_MESSAGE_FIELDS")
    require(value["profile"] == IPC_PROFILE and type(value["version"]) is int
            and value["version"] == 1, "IPC_MESSAGE_VERSION")
    for name in ("message_id", "sender_session", "receiver_generation", "scope_id"):
        identifier(value[name])
    for name in ("correlation_ref", "causation_ref"):
        if value[name] is not None:
            identifier(value[name])
    operation = value["operation"]
    require(type(operation) is str and operation in OPERATIONS, "IPC_OPERATION_UNAVAILABLE")
    start, end = value["issued_at_ms"], value["expires_at_ms"]
    require(type(start) is int and type(end) is int and 0 <= start < end
            and end - start <= MAX_MESSAGE_TTL_MS, "IPC_VALIDITY_SHAPE")
    require(type(value["record_wire"]) is str, "IPC_RECORD_REQUIRED")
    original = value["record_wire"].encode("utf8")
    record = decode_command(original) if operation in TASK_OPERATIONS else codec.decode(original)
    require(record.record_type == OPERATIONS[operation]
            and record.as_dict()["scope_id"] == value["scope_id"], "IPC_OPERATION_SCOPE_BINDING")
    if operation in TASK_OPERATIONS:
        require(record.as_dict()["kind"] == TASK_OPERATIONS[operation], "TASK_ROUTE_BINDING")
    require(record.commitment == value["record_commitment"]
            and hashlib.sha256(original).hexdigest() == value["original_record_sha256"], "IPC_RECORD_BINDING")
    args = value["arguments"]
    expected = {"reason_ref"} if operation == "kernel.revoke" else set()
    require(type(args) is dict and set(args) == expected, "IPC_ARGUMENTS")
    reason = args.get("reason_ref")
    if operation == "kernel.revoke":
        identifier(reason)
    return LocalMessage(value["message_id"], value["sender_session"], value["receiver_generation"],
                        operation, value["scope_id"], start, end, record, reason, wire)


class IngressState:
    """One serial receiver owns replay state; exhaustion denies rather than evicts."""
    def __init__(self, generation):
        identifier(generation)
        self.generation = generation
        self._seen = set()

    def accept(self, message, *, authenticated_session, allowed_operations, allowed_scopes, now_ms):
        require(type(message) is LocalMessage and type(now_ms) is int, "IPC_MESSAGE_REQUIRED")
        require(message.receiver_generation == self.generation, "IPC_STALE_RECEIVER")
        require(message.sender_session == authenticated_session, "IPC_SESSION_BINDING")
        require(message.operation in allowed_operations and message.scope_id in allowed_scopes, "IPC_CALLER_SCOPE_DENIED")
        require(message.issued_at_ms <= now_ms < message.expires_at_ms, "IPC_MESSAGE_EXPIRED_OR_FUTURE")
        key = (authenticated_session, message.message_id)
        require(key not in self._seen, "IPC_MESSAGE_REPLAY")
        require(len(self._seen) < MAX_REPLAY_ENTRIES, "IPC_REPLAY_CAPACITY_EXHAUSTED")
        # Consume before dispatch, including commands later denied by kernel.
        self._seen.add(key)
