"""Authenticated editor custody on TaskDrafts' existing atomic writer."""
from datetime import datetime, timezone
import hashlib
import uuid

from ceta.contracts.editor_recovery import (
    EDITOR_PROFILE, EDITOR_REFERENCE_PROFILE, decode_editor_chunk,
    decode_editor_payload, decode_editor_snapshot, editor_chunk_key,
    payload_capture_commitment, recovery_commitment, recovery_key,
    validate_editor_chunk)
from ceta.contracts.events import StreamPosition
from ceta.contracts.history import JournalEntry
from ceta.contracts.kernel_transactions import require
from ceta.contracts.store_transactions import StoreCell, StoreChange, StoreExpectation
from ceta.contracts.task_drafts import TaskResult
from ceta.contracts.task_meaning import meaning_commitment, meaning_key
from ceta.contracts.wire import PROFILE, canonical_bytes


def _instruction_commitment(instruction_hex):
    require(type(instruction_hex) is str, "EDITOR_ORIGINAL_REQUIRED")
    try:
        raw = bytes.fromhex(instruction_hex)
    except ValueError:
        require(False, "EDITOR_ORIGINAL_REQUIRED")
    return "sha256:" + hashlib.sha256(
        b"CETA:task-editor-original-instruction:v1\0" + raw).hexdigest()


def _document_raw_commitment(document):
    """Compare inline and reference document facts without trusting shape alone."""
    if "raw_commitment" in document:
        return document["raw_commitment"]
    raw = bytes.fromhex(document["utf16le_hex"])
    return "sha256:" + hashlib.sha256(
        b"CETA:task-editor-document-utf16:v1\0" + raw).hexdigest()


class EditorRecovery:
    """One collaborator of the task owner; no independent store or authority."""
    def __init__(self, task_owner):
        self._tasks = task_owner

    def _owned_editor(self, cell, task_value, owner, principal, message, context, subject):
        tasks = self._tasks
        require(cell.value_wire is not None and cell.generation > 0, "EDITOR_NOT_FOUND")
        value = decode_editor_snapshot(cell.value_wire)
        require(value["generation"] == cell.generation
            and cell.key == recovery_key(value["scope_id"], value["task_id"]), "EDITOR_CELL_BINDING")
        require(value["owner_binding"] == owner and value["principal_id"] == principal
            and (value["scope_id"], value["task_id"]) == (task_value["scope_id"], task_value["task_id"]),
            "EDITOR_OWNER_TASK_BINDING")
        require(value["lineage"]["original_instruction_commitment"]
            == _instruction_commitment(task_value["instruction_hex"]), "EDITOR_ORIGINAL_LINEAGE")
        point = StreamPosition(value["scope_id"], value["event_sequence"], value["previous_head"])
        tasks._subject(message, context, subject)
        rows = tasks._store.replay(point.scope_id, point.next_sequence, 1)
        tasks._subject(message, context, subject)
        require(len(rows) == 1, "EDITOR_EVENT_MISSING")
        parsed = tasks._events.require_successor(rows[0].event_wire, point).record
        event = parsed.as_dict()
        observation = tasks._events.require_payload(rows[0].event_wire, rows[0].payload_wire)
        payload = observation.as_dict()
        pin = recovery_commitment(cell.value_wire)
        event_type = {"STAGING": "task.editor.staging", "RETAINED": "task.editor.retained",
                      "DISCARDED": "task.editor.discarded"}[value["state"]]
        require(event["record_id"] == value["event_id"] and event["event_type"] == event_type
            and event["actor_id"] == principal and event["actor_session"] == value["updated_session"]
            and event["causation_ref"] == value["request_id"] and observation.record_type == "ObservationEnvelope"
            and observation.record_id == value["observation_id"] and payload["causation_ref"] == value["request_id"]
            and payload["observer_session"] == value["updated_session"]
            and payload["resource"] == {"resource_id": value["task_id"], "revision": pin,
                "access": "READ", "scope_id": value["scope_id"]}
            and payload["payload_ref"] == value["task_id"] and payload["payload_commitment"] == pin
            and payload["method"] == "authenticated.local." + event_type
            and payload["observed_at"] is None and payload["valid_until"] is None and payload["supersedes"] is None
            and payload["recorded_at"] == event["recorded_at"] and payload["completeness"] == "COMPLETE"
            and payload["epistemic_status"] == "OBSERVED" and payload["sensitivity"] == "PROJECT_PRIVATE"
            and parsed.original_wire == parsed.canonical_wire and observation.original_wire == observation.canonical_wire,
            "EDITOR_EVENT_BINDING")
        return value

    def _lineage(self, cells, task_value, owner, peer, payload, observed_task_revision,
                 previous_revision):
        """Bind each custody generation to the authenticated projection it observed."""
        # A reference capture can take several commits. A task save between
        # chunks must refresh the surrounding task/meaning facts while keeping
        # the raw capture's original basis immutable. The predecessor link
        # preserves the prior durable observation without reporting it as the
        # current task projection.
        meaning = cells[meaning_key(task_value["scope_id"], task_value["task_id"])]
        proposed = None
        if not (meaning.generation == 0 and meaning.value_wire is None):
            self._tasks._owned_meaning(meaning, task_value, owner, peer.principal_id)
            proposed = meaning_commitment(meaning.value_wire)
        return {"task_basis_revision": payload["basis_revision"],
            "observed_task_revision": observed_task_revision,
            "original_instruction_commitment": _instruction_commitment(task_value["instruction_hex"]),
            "proposed_meaning_commitment": proposed,
            "corrected_task_revision": task_value["objective_revision"],
            "recovery_capture_commitment": payload_capture_commitment(payload),
            "prior_recovery_revision": previous_revision}

    @staticmethod
    def _document_change_allowed(new, old):
        if new["document_id"] != old["document_id"]:
            return True
        if new["document_revision"] < old["document_revision"]:
            return False
        if new["document_revision"] == old["document_revision"]:
            if "utf16le_hex" in new:
                if "utf16le_hex" in old:
                    return new["utf16le_hex"] == old["utf16le_hex"]
            # An inline capture and a chunked reference describe the same
            # native document with different field sets. At an unchanged
            # native revision they may only cross that representation boundary
            # when their exact raw UTF-16 commitment is equal.
            return _document_raw_commitment(new) == _document_raw_commitment(old)
        return True

    def _next_retain(self, command, previous, basis):
        payload = decode_editor_payload(bytes.fromhex(command["editor_payload_hex"]))
        # Raw editor custody may have begun before an independently observed
        # task save.  Do not turn that later save into loss of the only full
        # widget bytes: retain the exact observed basis in the payload/lineage
        # while apply() binds this transaction to the current authenticated
        # task projection.  The payload remains recovery-only and cannot
        # alter validated task or meaning state.
        reference = payload["profile"] == EDITOR_REFERENCE_PROFILE
        chunk_wire, staged = None, 0
        if previous is not None and previous["state"] == "STAGING":
            require(reference, "EDITOR_STAGING_CAPTURE_REQUIRED")
            if canonical_bytes(payload) == canonical_bytes(previous["payload"]):
                staged = previous["staged_chunk_count"]
            else:
                # A later widget mutation owns a newer full local capture. Do
                # not let a partial older upload consume it or manufacture a
                # discard; start a separately committed staging lineage.
                require(payload["widget_revision"] > previous["payload"]["widget_revision"],
                        "EDITOR_WIDGET_REVISION_CONFLICT")
                for name, document in payload["documents"].items():
                    require(self._document_change_allowed(document, previous["payload"]["documents"][name]),
                            "EDITOR_DOCUMENT_REVISION_CONFLICT")
        elif previous is not None:
            prior = previous["payload"]
            require(payload["widget_revision"] > prior["widget_revision"], "EDITOR_WIDGET_REVISION_CONFLICT")
            for name, document in payload["documents"].items():
                require(self._document_change_allowed(document, prior["documents"][name]),
                        "EDITOR_DOCUMENT_REVISION_CONFLICT")
        if reference:
            chunk_wire = bytes.fromhex(command["editor_chunk_hex"])
            chunk = decode_editor_chunk(chunk_wire)
            validate_editor_chunk(payload, chunk)
            require(command["editor_capture_commitment"] == payload["capture_commitment"]
                and command["editor_chunk_index"] == staged
                and chunk["chunk_index"] == staged, "EDITOR_STAGING_INDEX")
            staged += 1
            state = "RETAINED" if staged == payload["chunk_count"] else "STAGING"
        else:
            require(previous is None or previous["state"] != "STAGING", "EDITOR_STAGING_CAPTURE_REQUIRED")
            state = "RETAINED"
        return payload, chunk_wire, staged, state

    def _read_chunk(self, message, context, subject, cells, task_value, previous, basis, command):
        tasks = self._tasks
        require(previous is not None and previous["state"] == "RETAINED"
            and previous["payload"]["profile"] == EDITOR_REFERENCE_PROFILE,
            "EDITOR_CHUNK_RECOVERY_REQUIRED")
        cell = cells[recovery_key(message.scope_id, command["task_id"])]
        require(command["editor_expected_revision"] == cell.revision
            and command["editor_capture_commitment"] == previous["payload"]["capture_commitment"],
            "EDITOR_CHUNK_REVISION_CONFLICT")
        index = command["editor_chunk_index"]
        key = editor_chunk_key(message.scope_id, command["task_id"], command["editor_capture_commitment"], index)
        chunk_cell = tasks._snapshot((key,))[key]
        require(chunk_cell.generation == 1 and chunk_cell.value_wire is not None, "EDITOR_CHUNK_NOT_FOUND")
        chunk = decode_editor_chunk(chunk_cell.value_wire)
        validate_editor_chunk(previous["payload"], chunk)
        combined = dict(cells)
        combined[key] = chunk_cell
        tasks._finish_read(message, context, subject, combined)
        return TaskResult("TASK_EDITOR_CHUNK", chunk_cell.value_wire, cell.generation,
                          current_task_revision=basis)

    def apply(self, message, context, subject, command, cells, task_value, draft):
        tasks = self._tasks
        peer, owner = subject
        key = recovery_key(message.scope_id, command["task_id"])
        cell, basis = cells[key], cells[draft].revision
        previous = None
        if cell.generation == 0 and cell.value_wire is None:
            require(cell.generation == 0, "EDITOR_ABSENCE_GENERATION")
        else:
            previous = self._owned_editor(cell, task_value, owner, peer.principal_id, message, context, subject)
        if command["kind"] == "editor_load":
            if command["editor_chunk_index"] is not None:
                return self._read_chunk(message, context, subject, cells, task_value, previous, basis, command)
            tasks._finish_read(message, context, subject, cells)
            if previous is None:
                return TaskResult("TASK_EDITOR_ABSENT", current_task_revision=basis)
            return TaskResult("TASK_EDITOR_" + previous["state"], cell.value_wire, cell.generation,
                              current_task_revision=basis)
        require(command["editor_expected_revision"] == (None if previous is None else cell.revision),
                "EDITOR_REVISION_CONFLICT")
        chunk_wire = None
        if command["kind"] == "editor_retain":
            payload, chunk_wire, staged, state = self._next_retain(command, previous, basis)
            lineage = self._lineage(cells, task_value, owner, peer, payload, basis,
                                    cell.revision if previous else None)
            disposition = None
            event_type = "task.editor." + ("staging" if state == "STAGING" else "retained")
        else:
            require(command["kind"] == "editor_discard" and previous is not None
                and previous["state"] == "RETAINED", "EDITOR_DISCARD_REQUIRES_RETENTION")
            payload, staged, state = previous["payload"], previous["staged_chunk_count"], "DISCARDED"
            lineage = self._lineage(cells, task_value, owner, peer, payload, basis,
                                    cell.revision)
            disposition = {"kind": "EXPLICIT_DISCARD",
                "discarded_capture_commitment": payload_capture_commitment(payload),
                "consent_request_commitment": message.record.commitment,
                "predecessor_recovery_revision": cell.revision}
            event_type = "task.editor.discarded"
        tasks._subject(message, context, subject)
        point = tasks._store.position(message.scope_id)
        tasks._subject(message, context, subject)
        event_id, observation_id = "event:" + uuid.uuid4().hex, "observation:" + uuid.uuid4().hex
        value = {"profile": EDITOR_PROFILE, "state": state, "scope_id": message.scope_id,
            "task_id": command["task_id"], "owner_binding": owner, "principal_id": peer.principal_id,
            "updated_session": peer.session_id, "payload": payload, "generation": cell.generation + 1,
            "previous_recovery_revision": None if previous is None else cell.revision,
            "request_id": message.record.record_id, "request_commitment": message.record.commitment,
            "event_id": event_id, "event_sequence": point.next_sequence, "previous_head": point.head,
            "observation_id": observation_id, "lineage": lineage, "disposition": disposition,
            "staged_chunk_count": staged}
        wire = canonical_bytes(value)
        decode_editor_snapshot(wire)
        observed, pin = datetime.now(timezone.utc).isoformat(), recovery_commitment(wire)
        observation = tasks._codec.decode(canonical_bytes({"record_type": "ObservationEnvelope", "schema_version": "1",
            "record_id": observation_id, "scope_id": message.scope_id, "causation_ref": message.record.record_id,
            "observer_session": peer.session_id, "resource": {"resource_id": command["task_id"], "revision": pin,
                "access": "READ", "scope_id": message.scope_id}, "observed_at": None, "recorded_at": observed,
            "valid_until": None, "method": "authenticated.local." + event_type, "completeness": "COMPLETE",
            "payload_ref": command["task_id"], "payload_commitment": pin, "epistemic_status": "OBSERVED",
            "sensitivity": "PROJECT_PRIVATE", "uncertainty": [
                "Observed raw editor custody is not accepted task meaning, consent or a grant.",
                "Recorded wall time is not a qualified trusted clock."], "supersedes": None}))
        event_wire = canonical_bytes({"record_type": "EventRecord", "schema_version": "1", "record_id": event_id,
            "scope_id": message.scope_id, "causation_ref": message.record.record_id, "sequence": point.next_sequence,
            "event_type": event_type, "actor_id": peer.principal_id, "actor_session": peer.session_id,
            "recorded_at": observed, "previous_head": point.head, "payload_ref": observation_id,
            "payload_commitment": observation.commitment, "canonicalization_profile": PROFILE,
            "signer_key_ref": None, "signature_ref": None})
        changes = [StoreChange(StoreExpectation(key, cell.revision), wire, event_id)]
        chunk_key = None
        if chunk_wire is not None:
            chunk = decode_editor_chunk(chunk_wire)
            chunk_key = editor_chunk_key(message.scope_id, command["task_id"],
                                        chunk["capture_commitment"], chunk["chunk_index"])
            chunk_cell = tasks._snapshot((chunk_key,))[chunk_key]
            require(chunk_cell.generation == 0 and chunk_cell.value_wire is None, "EDITOR_CHUNK_ALREADY_STAGED")
            changes.append(StoreChange(StoreExpectation(chunk_key, chunk_cell.revision), chunk_wire, event_id))
        checks = tuple(StoreExpectation(other, cells[other].revision) for other in sorted(cells) if other != key)
        tasks._subject(message, context, subject)
        tasks._store.commit((point,), (JournalEntry(event_wire, observation.canonical_wire),),
            checks=checks, changes=tuple(changes), guard=lambda: tasks._subject(message, context, subject))
        tasks._subject(message, context, subject)
        after = tasks._snapshot(tuple(cells))
        require(after[key].value_wire == wire and after[key].generation == cell.generation + 1
            and all(after[other] == cells[other] for other in cells if other != key), "EDITOR_POSTCOMMIT_BINDING")
        self._owned_editor(after[key], task_value, owner, peer.principal_id, message, context, subject)
        tasks._finish_read(message, context, subject, after)
        return TaskResult("TASK_EDITOR_" + state, wire, after[key].generation, current_task_revision=basis)

