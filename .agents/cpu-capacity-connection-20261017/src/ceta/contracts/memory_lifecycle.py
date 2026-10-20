"""Memory lifecycle metadata binding; no permission or deletion is conferred."""
from dataclasses import dataclass
import re

from .wire import ContractError, ParsedRecord, RecordCodec

MEMORY_BINDING_PROFILE = "ceta-memory-lifecycle-binding-v1"
MEMORY_STATES = frozenset({"CANDIDATE", "ACTIVE", "SUPERSEDED", "ARCHIVED",
                           "RETIRED", "DELETED_PAYLOAD"})
_OBSERVED_DELETION = frozenset({"LOCAL_DELETION_OBSERVED", "BACKUP_RETENTION_PENDING", "PARTIAL"})
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}")
_BASE_VERIFICATIONS = ("CURRENT_AUTHORITY_AND_RETENTION_POLICY", "AUTHENTIC_INITIATOR_AND_APPROVAL",
                       "CURRENT_MEMORY_AND_REFERENCE_RESOLUTION")


@dataclass(frozen=True)
class MemoryLifecycleAssessment:
    """Bounded claims with their outstanding verifications, never an allow result."""

    memory: ParsedRecord
    lifecycle_event: ParsedRecord
    requested_state: str
    claimed_payload_deletion_state: str
    required_verifications: tuple[str, ...]


class MemoryLifecycleContract:
    """Check two supplied records against explicit expected scope/policy context.

    Composition must provide authentic current records and policy; this pure
    check neither resolves references nor proves the claim behind an evidence ID.
    The kernel still determines whether the requested transition is permitted.
    """

    def __init__(self, codec: RecordCodec) -> None:
        if type(codec) is not RecordCodec:
            raise ContractError("INVALID_MEMORY_CODEC")
        self._codec = codec

    def check_binding(self, memory_wire: bytes, event_wire: bytes, *,
                      expected_scope: str, expected_policy_ref: str) -> MemoryLifecycleAssessment:
        if any(type(v) is not str or not _ID.fullmatch(v) for v in (expected_scope, expected_policy_ref)):
            raise ContractError("INVALID_MEMORY_CONTEXT")
        memory = self._codec.decode(memory_wire)
        event = self._codec.decode(event_wire)
        if memory.record_type != "MemoryRecord" or event.record_type != "MemoryLifecycleEvent":
            raise ContractError("MEMORY_RECORD_TYPE_MISMATCH")
        item, change = memory.as_dict(), event.as_dict()
        if item["scope_id"] != expected_scope or change["scope_id"] != expected_scope:
            raise ContractError("MEMORY_SCOPE_MISMATCH")
        if change["memory_ref"] != item["record_id"]:
            raise ContractError("MEMORY_REFERENCE_MISMATCH")
        if item["retention_policy_ref"] != expected_policy_ref or change["policy_ref"] != expected_policy_ref:
            raise ContractError("MEMORY_POLICY_MISMATCH")
        if change["before"] != item["lifecycle"]:
            raise ContractError("MEMORY_STATE_STALE")
        if change["after"] not in MEMORY_STATES:
            raise ContractError("UNKNOWN_MEMORY_LIFECYCLE")
        deletion = change["payload_deletion_state"]
        if change["after"] == "DELETED_PAYLOAD" and deletion not in _OBSERVED_DELETION:
            raise ContractError("MEMORY_DELETION_CLAIM_UNSUPPORTED")
        if deletion in _OBSERVED_DELETION and not change["evidence_refs"]:
            raise ContractError("MEMORY_DELETION_EVIDENCE_MISSING")
        required = _BASE_VERIFICATIONS
        if deletion != "NOT_REQUESTED":
            required += ("DERIVED_COPY_AND_BACKUP_ACCOUNTING",)
        if deletion in _OBSERVED_DELETION:
            required += ("INDEPENDENT_PAYLOAD_DELETION_EVIDENCE",)
        return MemoryLifecycleAssessment(memory, event, change["after"], deletion, required)
