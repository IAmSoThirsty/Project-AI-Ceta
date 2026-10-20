"""Deterministic CREATED task custody on the captured atomic journal.

Capturing a task does not accept its meaning, scope, consent or grant. Kernel
objective revisions change atomically with drafts, invalidating prepared inputs.
The original submitted instruction is immutable; edits retain a separate draft.
"""
from datetime import datetime, timezone
import hashlib
import uuid

from ceta.contracts.events import EventContract, StreamPosition
from ceta.contracts.history import JournalEntry
from ceta.contracts.kernel_transactions import PeerIdentity, require, task_key, task_wire
from ceta.contracts.local_ipc import LocalMessage, decode_message
from ceta.contracts.store_transactions import StoreCell, StoreExpectation, StoreChange, commitment
from ceta.contracts.task_drafts import (TASK_PROFILE, CATALOG_PROFILE, MAX_TASKS, TASK_OPERATIONS,
    TaskCommand, TaskResult, decode_command, decode_snapshot, decode_catalog,
    draft_key, catalog_key, task_content_revision)
from ceta.contracts.wire import RecordCodec, PROFILE, canonical_bytes
from ceta.contracts.task_meaning import (MEANING_PROFILE, MEANING_OPERATIONS,
    meaning_key, meaning_commitment, decode_proposal)
from ceta.contracts.editor_recovery import EDITOR_OPERATIONS, recovery_key
from .editor_recovery import EditorRecovery


def snapshot_commitment(wire):
    return "sha256:" + hashlib.sha256(b"CETA:task-snapshot:v1\0" + wire).hexdigest()


class TaskDrafts:
    def __init__(self, store, codec, identity_owner):
        require(type(codec) is RecordCodec, "TASK_CODEC_REQUIRED")
        self._store, self._codec, self._identity = store, codec, identity_owner
        self._events = EventContract(codec)
        self._editor_recovery = EditorRecovery(self)

    def _subject(self, message, context, expected=None):
        self._identity.require_message(context, message)
        peer = self._identity.authenticate(context)
        require(type(peer) is PeerIdentity, "TASK_AUTHENTICATED_PEER_REQUIRED")
        owner = self._identity.task_owner_binding(context)
        commitment(owner)
        result = (peer, owner)
        require(expected is None or result == expected, "TASK_CONTEXT_CHANGED")
        return result

    def _snapshot(self, keys):
        cells = self._store.snapshot(tuple(sorted(keys)))
        require(type(cells) is tuple and len(cells) == len(keys)
                and all(type(cell) is StoreCell for cell in cells)
                and {cell.key for cell in cells} == set(keys), "TASK_SNAPSHOT_KEYS")
        return {cell.key: cell for cell in cells}

    def _finish_read(self, message, context, subject, cells):
        self._subject(message, context, subject)
        require(self._snapshot(tuple(cells)) == cells, "TASK_READ_CHANGED")
        # Invalidation during the last native/store read must deny disclosure.
        self._subject(message, context, subject)

    def _owned_task(self, draft, task, owner, principal):
        require(draft.value_wire is not None and draft.generation > 0, "TASK_NOT_FOUND")
        value = decode_snapshot(draft.value_wire)
        require(value["objective_generation"] == draft.generation, "TASK_GENERATION_MISMATCH")
        require(value["owner_binding"] == owner and value["principal_id"] == principal, "TASK_OWNER_DENIED")
        require(draft.key == draft_key(value["scope_id"], value["task_id"])
                and task.key == task_key(value["scope_id"], value["task_id"])
                and task.value_wire == task_wire(value["scope_id"], value["task_id"], value["objective_revision"]), "TASK_KERNEL_REVISION_MISMATCH")
        point = StreamPosition(value["scope_id"], value["event_sequence"], value["previous_head"])
        rows = self._store.replay(point.scope_id, point.next_sequence, 1)
        require(len(rows) == 1, "TASK_EVENT_MISSING")
        parsed_event = self._events.require_successor(rows[0].event_wire, point).record
        event = parsed_event.as_dict()
        observation = self._events.require_payload(rows[0].event_wire, rows[0].payload_wire)
        payload = observation.as_dict()
        expected_type = "task.created" if draft.generation == 1 else "task.draft.saved"
        require(event["record_id"] == value["event_id"] and event["event_type"] == expected_type
                and event["actor_id"] == principal and event["actor_session"] == value["updated_session"]
                and event["causation_ref"] == value["request_id"]
                and observation.record_type == "ObservationEnvelope" and observation.record_id == value["observation_id"]
                and payload["causation_ref"] == value["request_id"]
                and payload["observer_session"] == value["updated_session"]
                and payload["resource"] == {"resource_id": value["task_id"], "revision": snapshot_commitment(draft.value_wire),
                    "access": "READ", "scope_id": value["scope_id"]}
                and payload["payload_ref"] == value["task_id"]
                and payload["payload_commitment"] == snapshot_commitment(draft.value_wire)
                and payload["observed_at"] is None and payload["valid_until"] is None and payload["supersedes"] is None
                and payload["recorded_at"] == event["recorded_at"] and payload["completeness"] == "COMPLETE"
                and payload["epistemic_status"] == "OBSERVED" and payload["sensitivity"] == "PROJECT_PRIVATE"
                and parsed_event.original_wire == parsed_event.canonical_wire
                and observation.original_wire == observation.canonical_wire
                and payload["method"] == "authenticated.local." + expected_type,
                "TASK_EVENT_BINDING")
        return value

    def _owned_meaning(self, cell, task_value, owner, principal):
        require(cell.value_wire is not None and cell.generation > 0, "MEANING_NOT_FOUND")
        value = decode_proposal(cell.value_wire)
        require(value["generation"] == cell.generation and cell.key == meaning_key(value["scope_id"], value["task_id"]), "MEANING_CELL_BINDING")
        require(value["owner_binding"] == owner and value["principal_id"] == principal
            and (value["scope_id"], value["task_id"], value["instruction_hex"])
            == (task_value["scope_id"], task_value["task_id"], task_value["instruction_hex"]), "MEANING_OWNER_TASK_BINDING")
        point = StreamPosition(value["scope_id"], value["event_sequence"], value["previous_head"])
        rows = self._store.replay(point.scope_id, point.next_sequence, 1)
        require(len(rows) == 1, "MEANING_EVENT_MISSING")
        parsed = self._events.require_successor(rows[0].event_wire, point).record
        event = parsed.as_dict()
        observation = self._events.require_payload(rows[0].event_wire, rows[0].payload_wire)
        payload = observation.as_dict(); pin = meaning_commitment(cell.value_wire)
        require(event["record_id"] == value["event_id"] and event["event_type"] == "task.meaning.proposed"
            and event["actor_id"] == principal and event["actor_session"] == value["updated_session"]
            and event["causation_ref"] == value["request_id"] and observation.record_type == "ObservationEnvelope"
            and observation.record_id == value["observation_id"] and payload["causation_ref"] == value["request_id"]
            and payload["observer_session"] == value["updated_session"]
            and payload["resource"] == {"resource_id": value["task_id"], "revision": pin, "access": "READ", "scope_id": value["scope_id"]}
            and payload["payload_ref"] == value["task_id"] and payload["payload_commitment"] == pin
            and payload["method"] == "authenticated.local.task.meaning.proposed"
            and payload["observed_at"] is None and payload["valid_until"] is None and payload["supersedes"] is None
            and payload["recorded_at"] == event["recorded_at"] and payload["completeness"] == "COMPLETE"
            and payload["epistemic_status"] == "ATTRIBUTED" and payload["sensitivity"] == "PROJECT_PRIVATE"
            and parsed.original_wire == parsed.canonical_wire and observation.original_wire == observation.canonical_wire,
            "MEANING_EVENT_BINDING")
        return value

    def _meaning(self, message, context, subject, command, cells, task_value, draft):
        peer, owner = subject; key = meaning_key(message.scope_id, command["task_id"])
        cell = cells[key]; basis = cells[draft].revision
        previous = None
        if cell.generation == 0 and cell.value_wire is None:
            pass
        else:
            previous = self._owned_meaning(cell, task_value, owner, peer.principal_id)
        if command["kind"] == "meaning_load":
            self._finish_read(message, context, subject, cells)
            if previous is None: return TaskResult("TASK_MEANING_ABSENT", current_task_revision=basis)
            kind = "TASK_MEANING_PROPOSAL" if previous["basis_revision"] == basis else "TASK_MEANING_STALE"
            return TaskResult(kind, cell.value_wire, cell.generation, current_task_revision=basis)
        require(command["expected_revision"] == basis, "MEANING_TASK_REVISION_CONFLICT")
        require(command["meaning_expected_revision"] == (None if previous is None else cell.revision), "MEANING_REVISION_CONFLICT")
        self._subject(message, context, subject); point = self._store.position(message.scope_id)
        event_id, observation_id = "event:" + uuid.uuid4().hex, "observation:" + uuid.uuid4().hex
        from ceta.contracts.wire import strict_loads
        value = {"profile": MEANING_PROFILE, "state": "UNACCEPTED", "scope_id": message.scope_id,
            "task_id": command["task_id"], "owner_binding": owner, "principal_id": peer.principal_id,
            "updated_session": peer.session_id, "basis_revision": basis,
            "task_objective_revision": task_value["objective_revision"],
            **{name: task_value[name] for name in ("title_hex", "instruction_hex", "draft_hex")},
            "meaning": strict_loads(bytes.fromhex(command["meaning_hex"])), "generation": cell.generation + 1,
            "request_id": command["record_id"], "request_commitment": message.record.commitment,
            "event_id": event_id, "event_sequence": point.next_sequence, "previous_head": point.head,
            "observation_id": observation_id}
        wire = canonical_bytes(value); decode_proposal(wire)
        observed = datetime.now(timezone.utc).isoformat(); pin = meaning_commitment(wire)
        payload = self._codec.decode(canonical_bytes({"record_type": "ObservationEnvelope", "schema_version": "1",
            "record_id": observation_id, "scope_id": message.scope_id, "causation_ref": command["record_id"],
            "observer_session": peer.session_id, "resource": {"resource_id": value["task_id"], "revision": pin,
                "access": "READ", "scope_id": message.scope_id}, "observed_at": None, "recorded_at": observed,
            "valid_until": None, "method": "authenticated.local.task.meaning.proposed", "completeness": "COMPLETE",
            "payload_ref": value["task_id"], "payload_commitment": pin, "epistemic_status": "ATTRIBUTED",
            "sensitivity": "PROJECT_PRIVATE", "uncertainty": ["Interpretation is an unaccepted attributed proposal, not consent or a grant.",
                "Recorded wall time is not a qualified trusted clock."], "supersedes": None}))
        event_wire = canonical_bytes({"record_type": "EventRecord", "schema_version": "1", "record_id": event_id,
            "scope_id": message.scope_id, "causation_ref": command["record_id"], "sequence": point.next_sequence,
            "event_type": "task.meaning.proposed", "actor_id": peer.principal_id, "actor_session": peer.session_id,
            "recorded_at": observed, "previous_head": point.head, "payload_ref": observation_id,
            "payload_commitment": payload.commitment, "canonicalization_profile": PROFILE,
            "signer_key_ref": None, "signature_ref": None})
        change = StoreChange(StoreExpectation(key, cell.revision), wire, event_id)
        checks = tuple(StoreExpectation(k, c.revision) for k, c in sorted(cells.items()) if k != key)
        self._store.commit((point,), (JournalEntry(event_wire, payload.canonical_wire),), checks=checks, changes=(change,),
            guard=lambda: self._subject(message, context, subject))
        self._subject(message, context, subject); after = self._snapshot(tuple(cells))
        require(after[key].value_wire == wire and after[key].generation == cell.generation + 1
            and all(after[k] == c for k, c in cells.items() if k != key), "MEANING_COMMIT_RECONCILE")
        self._subject(message, context, subject)
        return TaskResult("TASK_MEANING_PROPOSAL", wire, after[key].generation, current_task_revision=basis)

    def __call__(self, message, context):
        require(type(message) is LocalMessage and type(message.record) is TaskCommand
                and decode_message(message.original_message, self._codec) == message
                and decode_command(message.record.original_wire) == message.record
                and message.operation in TASK_OPERATIONS
                and TASK_OPERATIONS[message.operation] == message.record.as_dict()["kind"], "TASK_MESSAGE_REQUIRED")
        subject = self._subject(message, context)
        peer, owner = subject
        command = message.record.as_dict()
        scope, kind = message.scope_id, command["kind"]
        require(scope == command["scope_id"], "TASK_SCOPE_BINDING")
        catalog = catalog_key(scope, owner)
        if kind == "list":
            cells = self._snapshot((catalog,)); cell = cells[catalog]
            ids = () if cell.generation == 0 and cell.value_wire is None else decode_catalog(cell.value_wire, scope, owner)
            self._finish_read(message, context, subject, cells)
            return TaskResult("TASK_LIST", task_ids=ids)
        draft, task = draft_key(scope, command["task_id"]), task_key(scope, command["task_id"])
        selected = (draft, task, catalog)
        if message.operation in MEANING_OPERATIONS: selected += (meaning_key(scope, command["task_id"]),)
        if message.operation in EDITOR_OPERATIONS:
            # Editor custody binds its raw capture to the actual original task,
            # current proposal (when present), and corrected task revision. The
            # proposal cell remains read-only here; raw text never enters it.
            selected += (meaning_key(scope, command["task_id"]), recovery_key(scope, command["task_id"]))
        if message.operation in EDITOR_OPERATIONS: self._subject(message, context, subject)
        cells = self._snapshot(selected)
        if message.operation in EDITOR_OPERATIONS: self._subject(message, context, subject)
        index = cells[catalog]
        ids = () if index.generation == 0 and index.value_wire is None else decode_catalog(index.value_wire, scope, owner)
        if kind == "create":
            require(cells[draft].generation == cells[task].generation == 0
                    and cells[draft].value_wire is None and cells[task].value_wire is None,
                    "TASK_EXISTS_OR_CONFLICT")
            require(len(ids) < MAX_TASKS and command["task_id"] not in ids, "TASK_CAPACITY_OR_CATALOG_CONFLICT")
            value = {"profile": TASK_PROFILE, "scope_id": scope, "task_id": command["task_id"],
                "owner_binding": owner, "principal_id": peer.principal_id, "created_session": peer.session_id,
                "state": "CREATED", "instruction_hex": command["instruction_hex"],
                "meaning": {name: None for name in ("clarified_meaning", "scope", "exclusions", "completion_predicates",
                    "assumptions", "unresolved_questions", "standing_instructions", "authority", "budgets", "evidence")}}
        else:
            if (kind == "load" and cells[draft].generation == cells[task].generation == 0
                    and cells[draft].value_wire is None and cells[task].value_wire is None
                    and command["task_id"] not in ids):
                self._finish_read(message, context, subject, cells)
                return TaskResult("TASK_ABSENT")
            if message.operation in EDITOR_OPERATIONS: self._subject(message, context, subject)
            value = self._owned_task(cells[draft], cells[task], owner, peer.principal_id)
            if message.operation in EDITOR_OPERATIONS: self._subject(message, context, subject)
            require(command["task_id"] in ids, "TASK_CATALOG_MISMATCH")
            if message.operation in MEANING_OPERATIONS:
                return self._meaning(message, context, subject, command, cells, value, draft)
            if message.operation in EDITOR_OPERATIONS:
                return self._editor_recovery.apply(message, context, subject, command, cells, value, draft)
            if kind == "load":
                self._finish_read(message, context, subject, cells)
                return TaskResult("TASK_SNAPSHOT", cells[draft].value_wire, cells[draft].generation)
            require(command["expected_revision"] == cells[draft].revision, "TASK_REVISION_CONFLICT")
            if all(command[n] == value[n] for n in ("title_hex", "draft_hex")):
                self._finish_read(message, context, subject, cells)
                return TaskResult("TASK_UNCHANGED", cells[draft].value_wire, cells[draft].generation)
        self._subject(message, context, subject)
        point = self._store.position(scope)
        event_id, observation_id = "event:" + uuid.uuid4().hex, "observation:" + uuid.uuid4().hex
        value.update(updated_session=peer.session_id, title_hex=command["title_hex"], draft_hex=command["draft_hex"],
            request_id=command["record_id"], request_commitment=message.record.commitment,
            event_id=event_id, observation_id=observation_id,
            objective_generation=cells[draft].generation + 1,
            event_sequence=point.next_sequence, previous_head=point.head)
        value["objective_revision"] = task_content_revision(value)
        wire = canonical_bytes(value); decode_snapshot(wire)
        observed = datetime.now(timezone.utc).isoformat()
        event_type = "task.created" if kind == "create" else "task.draft.saved"
        payload = self._codec.decode(canonical_bytes({"record_type": "ObservationEnvelope", "schema_version": "1",
            "record_id": observation_id, "scope_id": scope, "causation_ref": command["record_id"],
            "observer_session": peer.session_id, "resource": {"resource_id": value["task_id"],
                "revision": snapshot_commitment(wire), "access": "READ", "scope_id": scope},
            "observed_at": None, "recorded_at": observed, "valid_until": None,
            "method": "authenticated.local." + event_type, "completeness": "COMPLETE",
            "payload_ref": value["task_id"], "payload_commitment": snapshot_commitment(wire),
            "epistemic_status": "OBSERVED", "sensitivity": "PROJECT_PRIVATE",
            "uncertainty": ["Submitted bytes preserved; interpretation and consent are not inferred.",
                "Recorded wall time is not a qualified trusted clock."], "supersedes": None}))
        event_wire = canonical_bytes({"record_type": "EventRecord", "schema_version": "1", "record_id": event_id,
            "scope_id": scope, "causation_ref": command["record_id"], "sequence": point.next_sequence,
            "event_type": event_type, "actor_id": peer.principal_id, "actor_session": peer.session_id,
            "recorded_at": observed, "previous_head": point.head, "payload_ref": observation_id,
            "payload_commitment": payload.commitment, "canonicalization_profile": PROFILE,
            "signer_key_ref": None, "signature_ref": None})
        values = {draft: wire, task: task_wire(scope, value["task_id"], value["objective_revision"])}
        if kind == "create":
            values[catalog] = canonical_bytes({"profile": CATALOG_PROFILE, "scope_id": scope,
                "owner_binding": owner, "task_ids": [*ids, value["task_id"]]})
        changes = tuple(StoreChange(StoreExpectation(key, cells[key].revision), body, event_id)
                        for key, body in sorted(values.items()))
        checks = tuple(StoreExpectation(key, cell.revision) for key, cell in sorted(cells.items()) if key not in values)
        self._store.commit((point,), (JournalEntry(event_wire, payload.canonical_wire),), checks=checks, changes=changes,
            guard=lambda: self._subject(message, context, subject))
        # This denial is allowed after COMMIT; the caller must load/reconcile.
        self._subject(message, context, subject)
        after = self._snapshot(tuple(cells))
        require(all(after[key].value_wire == body and after[key].generation == cells[key].generation + 1
                    for key, body in values.items()), "TASK_COMMIT_RECONCILE")
        self._subject(message, context, subject)
        return TaskResult("TASK_SNAPSHOT", after[draft].value_wire, after[draft].generation)
