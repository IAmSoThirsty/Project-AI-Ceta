"""Disposable reference views derived from the exact admitted journal prefix.

These views retain raw evidence and do not authenticate an actor, authorize an
effect, resolve a missing payload, or turn an observation into settlement. Task
events bind draft/meaning/editor references; the actual text remains in the
canonical store change records and is never fabricated from its commitment.
"""
from dataclasses import dataclass, fields
import hashlib
from types import MappingProxyType

from ceta.contracts.events import EventContract, StreamPosition
from ceta.contracts.history import JournalEntry
from ceta.contracts.memory_lifecycle import MEMORY_STATES
from ceta.contracts.store_transactions import identifier, commitment
from ceta.contracts.wire import ContractError, RecordCodec, canonical_bytes, strict_loads


PROJECTION_PROFILE = "ceta-journal-reference-projection-v1"
MAX_PROJECTION_EVENTS = 65536
MAX_PROJECTION_BYTES = 64 * 1024 * 1024
_DOMAIN = b"CETA:journal-reference-projection:v1\0"
_TASK_EVENTS = {
    "task.created": ("task_drafts", "OBSERVED"),
    "task.draft.saved": ("task_drafts", "OBSERVED"),
    "task.meaning.proposed": ("task_meanings", "ATTRIBUTED"),
    "task.editor.retained": ("task_editors", "OBSERVED"),
    "task.editor.discarded": ("task_editors", "OBSERVED"),
}
_BUILTINS = {
    **{name: "ObservationEnvelope" for name in _TASK_EVENTS},
    "observation.accepted": "ObservationEnvelope",
    "kernel.intent.committed": "OperationPermit",
    "kernel.permit.consumed": "OperationPermit",
    "kernel.grant.revoked": "StandingGrant",
    "kernel.development.allocation": "PolicyDecision",
}
_REFERENCE_COLLECTIONS = {
    "MemoryRecord": "memory_records", "MemoryLifecycleEvent": "memory_lifecycles",
    "ExecutionReceipt": "execution_receipts", "EffectObservation": "effect_observations",
    "ObservationEnvelope": "observations", "StandingGrant": "grant_references",
    "OperationPermit": "permit_references", "PolicyDecision": "policy_references",
}
_COLLECTIONS = frozenset(_REFERENCE_COLLECTIONS.values()) | {
    "task_drafts", "task_meanings", "task_editors", "grants", "permits", "policy_decisions"}


def _require(condition, code):
    if not condition:
        raise ContractError(code)


def _copy(value, cls):
    _require(type(value) is cls, "PROJECTION_VALUE_TYPE")
    try:
        copied = [object.__getattribute__(value, field.name) for field in fields(cls) if field.init]
    except AttributeError as error:
        raise ContractError("PROJECTION_VALUE_FIELDS") from error
    return cls(*copied)


def _entries(value):
    _require(type(value) is tuple and len(value) <= MAX_PROJECTION_EVENTS,
        "PROJECTION_EVENT_BOUND_EXCEEDED")
    copied = tuple(_copy(entry, JournalEntry) for entry in value)
    _require(sum(len(entry.event_wire) + len(entry.payload_wire) for entry in copied)
        <= MAX_PROJECTION_BYTES, "PROJECTION_BYTE_BOUND_EXCEEDED")
    return copied


def _sha(value):
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True, slots=True)
class ProjectionRegistration:
    """An explicit event spelling for one supported typed reference reducer.

    Composition must select the spelling from its actual accepted event owner.
    This is local derivation configuration, never wire or authority registration.
    No custom callback can inject projection values or skip prefix validation.
    """
    event_type: str
    payload_type: str

    def __post_init__(self):
        _require(type(self.event_type) is str and 1 <= len(self.event_type) <= 4096,
            "PROJECTION_EVENT_NAME")
        _require(type(self.payload_type) is str and self.payload_type in _REFERENCE_COLLECTIONS,
            "PROJECTION_PAYLOAD_SEMANTICS_UNSUPPORTED")


@dataclass(frozen=True, slots=True)
class ProjectedRecord:
    """Latest exact accepted record for an index key; all labels remain claims."""
    collection: str
    subject_id: str
    event_id: str
    sequence: int
    event_wire: bytes
    payload_wire: bytes

    def __post_init__(self):
        _require(type(self.collection) is str and self.collection in _COLLECTIONS,
            "PROJECTION_COLLECTION")
        identifier(self.subject_id); identifier(self.event_id)
        _require(type(self.sequence) is int and 0 <= self.sequence < 2**53,
            "PROJECTION_SEQUENCE")
        JournalEntry(self.event_wire, self.payload_wire)

    def payload(self):
        """Return a detached record copy, retaining original bytes separately."""
        return strict_loads(self.payload_wire)

    @property
    def key(self):
        return self.collection, self.subject_id


@dataclass(frozen=True, slots=True)
class MemoryReference:
    memory_id: str
    claimed_lifecycle: str
    claimed_deletion_state: str
    lifecycle_event_id: str | None

    def __post_init__(self):
        identifier(self.memory_id)
        _require(type(self.claimed_lifecycle) is str and self.claimed_lifecycle in MEMORY_STATES,
            "PROJECTION_MEMORY_LIFECYCLE_UNSUPPORTED")
        _require(type(self.claimed_deletion_state) is str and self.claimed_deletion_state in {
            "NOT_REQUESTED", "REQUESTED", "LOCAL_DELETION_OBSERVED", "BACKUP_RETENTION_PENDING", "PARTIAL"},
            "PROJECTION_MEMORY_DELETION_STATE")
        if self.lifecycle_event_id is not None:
            identifier(self.lifecycle_event_id)


@dataclass(frozen=True, slots=True)
class ProjectionSnapshot:
    profile: str
    registry_commitment: str
    position: StreamPosition
    entries: tuple[JournalEntry, ...]
    records: tuple[ProjectedRecord, ...]
    memory_references: tuple[MemoryReference, ...]

    def __post_init__(self):
        _require(type(self.profile) is str and self.profile == PROJECTION_PROFILE, "PROJECTION_PROFILE_UNSUPPORTED")
        commitment(self.registry_commitment)
        object.__setattr__(self, "position", _copy(self.position, StreamPosition))
        object.__setattr__(self, "entries", _entries(self.entries))
        _require(type(self.records) is tuple and len(self.records) <= MAX_PROJECTION_EVENTS
            and type(self.memory_references) is tuple and len(self.memory_references) <= MAX_PROJECTION_EVENTS,
            "PROJECTION_VIEW_BOUND_EXCEEDED")
        records = tuple(_copy(item, ProjectedRecord) for item in self.records)
        memories = tuple(_copy(item, MemoryReference) for item in self.memory_references)
        _require(tuple(sorted(records, key=lambda item: item.key)) == records
            and len({item.key for item in records}) == len(records), "PROJECTION_RECORD_ORDER_OR_DUPLICATE")
        _require(tuple(sorted(memories, key=lambda item: item.memory_id)) == memories
            and len({item.memory_id for item in memories}) == len(memories), "PROJECTION_MEMORY_ORDER_OR_DUPLICATE")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "memory_references", memories)

    def select(self, collection):
        _require(type(collection) is str and collection in _COLLECTIONS, "PROJECTION_COLLECTION")
        return tuple(item for item in self.records if item.collection == collection)

    @property
    def sha256(self):
        # Length-framed small canonical objects avoid an implicit one-MiB
        # aggregate wire ceiling on a supported growing projection prefix.
        hasher = hashlib.sha256(_DOMAIN)
        def frame(value):
            raw = canonical_bytes(value)
            hasher.update(len(raw).to_bytes(8, "big")); hasher.update(raw)
        frame({"profile": self.profile, "registry_commitment": self.registry_commitment,
            "position": {"scope_id": self.position.scope_id, "next_sequence": self.position.next_sequence,
                "head": self.position.head},
            "entry_count": len(self.entries), "record_count": len(self.records),
            "memory_reference_count": len(self.memory_references)})
        for entry in self.entries:
            frame(["entry", _sha(entry.event_wire), _sha(entry.payload_wire)])
        for item in self.records:
            frame(["record", item.collection, item.subject_id, item.event_id, item.sequence,
                _sha(item.event_wire), _sha(item.payload_wire)])
        for item in self.memory_references:
            frame(["memory_reference", item.memory_id, item.claimed_lifecycle,
                item.claimed_deletion_state, item.lifecycle_event_id])
        return "sha256:" + hasher.hexdigest()


class ProjectionReducer:
    """Rebuild exact bounded per-scope prefixes, rejecting unknown semantics.

    ``reduce`` validates the retained original prefix before accepting a tail.
    Snapshot hashes are identity data, not trust anchors. The journal read seam
    independently validates the real committed prefix in one SQLite snapshot.
    Registry changes require a full rebuild and cannot reinterpret an old view.
    """
    def __init__(self, codec, *, registrations=()):
        _require(type(codec) is RecordCodec, "PROJECTION_CODEC_REQUIRED")
        # Freeze the injected schema against later caller mutation.
        try:
            schema_wire = canonical_bytes(object.__getattribute__(codec, "_schema"))
            self._codec = RecordCodec(strict_loads(schema_wire))
        except (AttributeError, TypeError, ContractError) as error:
            raise ContractError("PROJECTION_CODEC_INVALID") from error
        self._events = EventContract(self._codec)
        _require(type(registrations) is tuple and len(registrations) <= 128,
            "PROJECTION_REGISTRY_BOUND")
        mapping = dict(_BUILTINS)
        for supplied in registrations:
            registration = _copy(supplied, ProjectionRegistration)
            _require(registration.event_type not in mapping, "PROJECTION_EVENT_REGISTRATION_DUPLICATE")
            mapping[registration.event_type] = registration.payload_type
        self._registry = MappingProxyType(mapping)
        self.registry_commitment = "sha256:" + _sha(b"CETA:projection-registry:v1\0" + canonical_bytes({
            "profile": PROJECTION_PROFILE, "schema_sha256": _sha(schema_wire),
            "event_payloads": [[key, mapping[key]] for key in sorted(mapping)]}))

    def _task(self, event, payload, records):
        event_type = event["event_type"]
        collection, epistemic_status = _TASK_EVENTS[event_type]
        task_id = payload["payload_ref"]
        identifier(task_id)
        _require(payload["resource"] == {"resource_id": task_id,
            "revision": payload["payload_commitment"], "access": "READ", "scope_id": event["scope_id"]}
            and payload["payload_commitment"] is not None
            and payload["method"] == "authenticated.local." + event_type
            and payload["observer_session"] == event["actor_session"]
            and payload["causation_ref"] == event["causation_ref"]
            and payload["recorded_at"] == event["recorded_at"]
            and payload["observed_at"] is None and payload["valid_until"] is None and payload["supersedes"] is None
            and payload["completeness"] == "COMPLETE" and payload["epistemic_status"] == epistemic_status
            and payload["sensitivity"] == "PROJECT_PRIVATE", "PROJECTION_TASK_BINDING")
        previous = records.get(("task_drafts", task_id))
        if event_type == "task.created":
            _require(previous is None, "PROJECTION_TASK_ALREADY_CREATED")
        else:
            _require(previous is not None, "PROJECTION_TASK_CREATION_MISSING")
            created_event = strict_loads(previous.event_wire)
            _require(created_event["actor_id"] == event["actor_id"], "PROJECTION_TASK_OWNER_CHANGED")
        return collection, task_id

    def _kernel(self, event, payload, records):
        event_type = event["event_type"]
        _require(event["causation_ref"] == payload["causation_ref"], "PROJECTION_KERNEL_CAUSATION_BINDING")
        if event_type == "kernel.intent.committed":
            _require(payload["status"] == "PREPARED" and payload["consume_event_ref"] is None
                and payload["issuance_evidence_ref"] == event["record_id"], "PROJECTION_PERMIT_ISSUANCE_BINDING")
            _require(("permits", payload["record_id"]) not in records, "PROJECTION_PERMIT_ALREADY_ISSUED")
            return "permits", payload["record_id"]
        if event_type == "kernel.permit.consumed":
            _require(payload["status"] == "CONSUMED" and payload["consume_event_ref"] == event["record_id"]
                and payload["causation_ref"] == event["record_id"], "PROJECTION_PERMIT_CONSUMPTION_BINDING")
            previous = records.get(("permits", payload["record_id"]))
            _require(previous is not None, "PROJECTION_PERMIT_ISSUANCE_MISSING")
            before = previous.payload()
            _require(before["status"] == "PREPARED", "PROJECTION_PERMIT_CONSUMED_TWICE")
            immutable = set(before) - {"status", "consume_event_ref", "causation_ref"}
            _require(all(before[name] == payload[name] for name in immutable), "PROJECTION_PERMIT_CONTENT_CHANGED")
            _require(strict_loads(previous.event_wire)["actor_id"] == event["actor_id"],
                "PROJECTION_PERMIT_ACTOR_CHANGED")
            return "permits", payload["record_id"]
        if event_type == "kernel.grant.revoked":
            _require(payload["status"] == "REVOKED" and payload["revocation_generation"] > 0,
                "PROJECTION_GRANT_REVOCATION_BINDING")
            previous = records.get(("grants", payload["record_id"]))
            if previous is not None:
                before = previous.payload()
                _require(before["revocation_generation"] < payload["revocation_generation"],
                    "PROJECTION_GRANT_REVOCATION_NOT_ADVANCED")
            return "grants", payload["record_id"]
        _require(event_type == "kernel.development.allocation" and payload["outcome"] == "ALLOW"
            and payload["reason_codes"] == ["DEVELOPMENT_ALLOCATION_PROFILE"]
            and payload["authority_owner_id"] == "kernel:cmp02", "PROJECTION_ALLOCATION_BINDING")
        return "policy_decisions", payload["record_id"]

    def _memory(self, payload, records, memories):
        if payload["record_type"] == "MemoryRecord":
            key = payload["record_id"]
            memories[key] = MemoryReference(key, payload["lifecycle"], "NOT_REQUESTED", None)
            return
        memory_id = payload["memory_ref"]
        previous = records.get(("memory_records", memory_id))
        state = memories.get(memory_id)
        _require(previous is not None and state is not None, "PROJECTION_MEMORY_REFERENCE_UNRESOLVED")
        base = previous.payload()
        _require(payload["policy_ref"] == base["retention_policy_ref"]
            and payload["before"] == state.claimed_lifecycle, "PROJECTION_MEMORY_STATE_OR_POLICY_BINDING")
        _require(payload["after"] in MEMORY_STATES, "PROJECTION_MEMORY_LIFECYCLE_UNSUPPORTED")
        deletion = payload["payload_deletion_state"]
        observed = deletion in {"LOCAL_DELETION_OBSERVED", "BACKUP_RETENTION_PENDING", "PARTIAL"}
        _require(payload["after"] != "DELETED_PAYLOAD" or observed, "MEMORY_DELETION_CLAIM_UNSUPPORTED")
        _require(not observed or payload["evidence_refs"], "MEMORY_DELETION_EVIDENCE_MISSING")
        memories[memory_id] = MemoryReference(memory_id, payload["after"], deletion, payload["record_id"])

    def rebuild(self, scope_id, entries, *, expected_position=None):
        """Derive from genesis; fail without returning a partial usable view."""
        point = StreamPosition(scope_id, 0, None)
        originals = _entries(entries)
        expected = None if expected_position is None else _copy(expected_position, StreamPosition)
        if expected is not None:
            _require(expected.scope_id == scope_id, "PROJECTION_SCOPE_MISMATCH")
        records, memories, event_ids, payload_ids = {}, {}, set(), {}
        for entry in originals:
            prepared = self._events.require_successor(entry.event_wire, point)
            parsed = self._events.require_payload(entry.event_wire, entry.payload_wire)
            event, payload = prepared.record.as_dict(), parsed.as_dict()
            _require(prepared.record.record_id not in event_ids, "PROJECTION_EVENT_ID_DUPLICATE")
            event_ids.add(prepared.record.record_id)
            expected_type = self._registry.get(event["event_type"])
            _require(expected_type is not None, "PROJECTION_EVENT_UNREGISTERED")
            _require(parsed.record_type == expected_type, "PROJECTION_EVENT_PAYLOAD_TYPE_MISMATCH")
            previous_type = payload_ids.setdefault(parsed.record_id, parsed.record_type)
            _require(previous_type == parsed.record_type, "PROJECTION_PAYLOAD_ID_TYPE_CHANGED")
            if event["event_type"] in _TASK_EVENTS:
                _require(prepared.record.original_wire == prepared.record.canonical_wire
                    and parsed.original_wire == parsed.canonical_wire, "PROJECTION_TASK_CANONICAL_EVENT_REQUIRED")
                collection, subject = self._task(event, payload, records)
            elif event["event_type"].startswith("kernel.") and event["event_type"] in _BUILTINS:
                collection, subject = self._kernel(event, payload, records)
            else:
                collection, subject = _REFERENCE_COLLECTIONS[parsed.record_type], parsed.record_id
                if parsed.record_type in {"MemoryRecord", "MemoryLifecycleEvent"}:
                    self._memory(payload, records, memories)
                if parsed.record_type == "EffectObservation" and payload["receipt_ref"] is not None:
                    receipt = records.get(("execution_receipts", payload["receipt_ref"]))
                    _require(receipt is not None and receipt.payload()["operation_id"] == payload["operation_id"],
                        "PROJECTION_EFFECT_RECEIPT_REFERENCE_UNRESOLVED")
            records[(collection, subject)] = ProjectedRecord(collection, subject, event["record_id"],
                event["sequence"], entry.event_wire, entry.payload_wire)
            _require(point.next_sequence < 2**53 - 1, "PROJECTION_SEQUENCE_EXHAUSTED")
            point = StreamPosition(scope_id, point.next_sequence + 1, prepared.head)
        _require(expected is None or point == expected, "PROJECTION_ACCEPTED_PREFIX_MISMATCH")
        return ProjectionSnapshot(PROJECTION_PROFILE, self.registry_commitment, point, originals,
            tuple(records[key] for key in sorted(records)), tuple(memories[key] for key in sorted(memories)))

    def reduce(self, snapshot, entries, *, expected_before, expected_after=None):
        """Verify cached view against its retained prefix before adding a tail."""
        previous = _copy(snapshot, ProjectionSnapshot)
        before = _copy(expected_before, StreamPosition)
        _require(previous.registry_commitment == self.registry_commitment, "PROJECTION_REGISTRY_CHANGED")
        _require(previous.position == before, "PROJECTION_SNAPSHOT_PREFIX_MISMATCH")
        rebuilt = self.rebuild(before.scope_id, previous.entries, expected_position=before)
        _require(rebuilt == previous, "PROJECTION_VIEW_DIVERGENCE")
        tail = _entries(entries)
        return self.rebuild(before.scope_id, previous.entries + tail, expected_position=expected_after)


__all__ = ["PROJECTION_PROFILE", "MAX_PROJECTION_EVENTS", "MAX_PROJECTION_BYTES",
    "ProjectionRegistration", "ProjectedRecord", "MemoryReference", "ProjectionSnapshot", "ProjectionReducer"]
