"""Event preimages and bindings; neither a signature verifier nor a store.

The trusted writer supplies the accepted stream position and payload bytes.
Callers cannot turn a matching hash or these value objects into authority.
"""
from dataclasses import dataclass
import hashlib
import re

from .wire import ContractError, ParsedRecord, PROFILE, RecordCodec, canonical_bytes

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}")
_HASH = re.compile(r"sha256:[0-9a-f]{64}")
_HEAD_DOMAIN = ("CETA:event-head:" + PROFILE + "\0").encode("ascii")
_SIGNATURE_DOMAIN = ("CETA:event-signature:" + PROFILE + "\0").encode("ascii")


@dataclass(frozen=True)
class StreamPosition:
    """Accepted position injected by the sole writer, not a trust assertion."""

    scope_id: str
    next_sequence: int
    head: str | None

    def __post_init__(self) -> None:
        if type(self.scope_id) is not str or not _IDENTIFIER.fullmatch(self.scope_id):
            raise ContractError("INVALID_SCOPE")
        if type(self.next_sequence) is not int or not 0 <= self.next_sequence <= 2**53 - 1:
            raise ContractError("INVALID_SEQUENCE")
        if self.head is not None and (type(self.head) is not str or not _HASH.fullmatch(self.head)):
            raise ContractError("INVALID_HEAD")
        if (self.next_sequence == 0) != (self.head is None):
            raise ContractError("INVALID_GENESIS_POSITION")


@dataclass(frozen=True)
class EventPreimages:
    record: ParsedRecord
    body: bytes
    head_preimage: bytes
    head: str
    signature_preimage: bytes | None


class EventContract:
    """Pure checks against the versioned injected record schema."""

    def __init__(self, codec: RecordCodec) -> None:
        self._codec = codec

    def preimages(self, wire: bytes) -> EventPreimages:
        record = self._codec.decode(wire)
        if record.record_type != "EventRecord":
            raise ContractError("EVENT_RECORD_REQUIRED")
        event = record.as_dict()
        if event["canonicalization_profile"] != PROFILE:
            raise ContractError("UNSUPPORTED_EVENT_PROFILE")
        if event["signature_ref"] is not None and event["signer_key_ref"] is None:
            raise ContractError("SIGNATURE_KEY_REQUIRED")
        # The signature reference is the sole excluded version-1 field.
        # Its key identifier stays in the body; no final hash field is admitted.
        del event["signature_ref"]
        body = canonical_bytes(event)
        head_preimage = _HEAD_DOMAIN + body
        signature_preimage = (_SIGNATURE_DOMAIN + body
                              if event["signer_key_ref"] is not None else None)
        return EventPreimages(record, body, head_preimage,
                              "sha256:" + hashlib.sha256(head_preimage).hexdigest(),
                              signature_preimage)

    def require_successor(self, wire: bytes, accepted: StreamPosition) -> EventPreimages:
        if type(accepted) is not StreamPosition:
            raise ContractError("STREAM_POSITION_REQUIRED")
        prepared = self.preimages(wire)
        event = prepared.record.as_dict()
        if event["scope_id"] != accepted.scope_id:
            raise ContractError("EVENT_SCOPE_MISMATCH")
        if event["sequence"] != accepted.next_sequence:
            raise ContractError("EVENT_SEQUENCE_MISMATCH")
        if event["previous_head"] != accepted.head:
            raise ContractError("EVENT_PRIOR_HEAD_MISMATCH")
        return prepared

    def require_payload(self, event_wire: bytes, payload_wire: bytes) -> ParsedRecord:
        event = self.preimages(event_wire).record.as_dict()
        payload = self._codec.decode(payload_wire)
        if event["payload_ref"] != payload.record_id:
            raise ContractError("EVENT_PAYLOAD_REFERENCE_MISMATCH")
        if event["scope_id"] != payload.as_dict()["scope_id"]:
            raise ContractError("EVENT_PAYLOAD_SCOPE_MISMATCH")
        if event["payload_commitment"] != payload.commitment:
            raise ContractError("EVENT_PAYLOAD_COMMITMENT_MISMATCH")
        return payload
