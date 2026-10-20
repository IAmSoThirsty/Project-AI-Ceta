"""Native task use cases; editing is immediate, persistence is asynchronous."""
import uuid
import threading
import time

from ceta.contracts.kernel_transactions import require
from ceta.contracts.local_ipc import SubmissionUncertain
from ceta.contracts.task_drafts import (command_wire, decode_command, decode_snapshot,
    text_hex, text_value, validate_result)
from ceta.contracts.task_meaning import (MEANING_FIELDS, MEANING_OPERATIONS,
    decode_proposal, meaning_from_text, meaning_as_text)
from ceta.contracts.editor_recovery import (
    EDITOR_REFERENCE_PROFILE, decode_editor_chunk, decode_editor_payload,
    decode_editor_snapshot, editor_payload_chunk_wires,
    editor_payload_matches_documents, materialize_editor_payload)


class TaskOperatorSession:
    def __init__(self, service, scope_id, compiler=None):
        self._service, self._scope = service, scope_id
        self._compiler = compiler
        self._context_job = None
        self._context_stopping = False
        self._shutdown_codes = []
        self._entries, self._selected, self._view_generation = {}, None, 0
        self._editor_discovery_queue = []
        self._blank_placeholders = set()
        self._pending, self._handled = None, None
        self.task_ids = ()
        self.status, self.detail, self.result_text = "STARTING", "Inspecting task service.", ""
        self.new_task()

    def _entry(self): return self._entries[self._selected]
    @property
    def task_id(self): return self._selected
    @property
    def local_task_ids(self):
        return tuple(task_id for task_id, entry in self._entries.items()
                     if not entry["editor_discovery_only"])
    @property
    def title(self): return self._entry()["title"]
    @property
    def draft(self): return self._entry()["draft"]
    @property
    def original_instruction(self): return self._entry()["instruction"]
    @property
    def revision(self): return self._entry()["revision"]
    @property
    def created(self): return self._entry()["snapshot"] is not None
    @property
    def saved_draft(self):
        snapshot = self._entry()["snapshot"]
        return "" if snapshot is None else text_value(snapshot["draft_hex"])
    @property
    def has_remote(self): return self._entry()["remote"] is not None
    @property
    def dirty(self):
        return self._entry_dirty(self._entry())

    @staticmethod
    def _entry_dirty(entry):
        if entry["snapshot"] is None: return bool(entry["title"] or entry["draft"])
        return any(text_hex(entry[name], maximum=256 if name == "title" else 65536)
                   != entry["snapshot"][name + "_hex"] for name in ("title", "draft"))

    @property
    def has_unconfirmed(self):
        return any(self._entry_dirty(entry) or entry["persistence"] in {"SAVING", "UNCERTAIN", "CONFLICT"}
                   or self._meaning_dirty(entry) or entry["meaning_persistence"] in {"SAVING", "UNCERTAIN", "CONFLICT"}
                    or entry["editor_state"] in {"QUEUED", "SAVING", "LOADING", "FETCHING", "DISCARDING",
                                                  "UNCERTAIN", "CONFLICT", "STAGING"}
                   for entry in self._entries.values())

    @staticmethod
    def _meaning_dirty(entry):
        proposal = entry["meaning_proposal"]
        return any(entry["meaning_text"].values()) if proposal is None else entry["meaning_text"] != meaning_as_text(proposal["meaning"])

    @property
    def meaning_text(self): return dict(self._entry()["meaning_text"])
    @property
    def meaning_revision(self): return self._entry()["meaning_revision"]
    @property
    def meaning_proposal(self): return self._entry()["meaning_proposal"]
    @property
    def meaning_observation(self): return self._entry()["meaning_remote"]
    @property
    def has_meaning_remote(self): return self._entry()["meaning_remote"] is not None
    @property
    def meaning_dirty(self): return self._meaning_dirty(self._entry())
    @property
    def meaning_basis_current(self):
        observed = self._entry()["meaning_observed_task_revision"]
        return self.revision is not None and (observed is None or observed == self.revision)
    @property
    def meaning_status(self):
        entry = self._entry(); state = entry["meaning_persistence"]
        if state in {"SAVING", "UNCERTAIN", "CONFLICT"}: return state
        if self.meaning_dirty: return "UNSAVED"
        if entry["meaning_proposal"] is None: return "NONE"
        current = entry["meaning_observed_task_revision"] or entry["revision"]
        if entry["meaning_proposal"]["basis_revision"] != current: return "STALE"
        if not self.meaning_basis_current: return "TASK_REFRESH_REQUIRED"
        if self.dirty: return "LOCAL_DRAFT_CHANGED"
        return "PROPOSED_UNACCEPTED"

    def set_meaning_field(self, name, text):
        require(type(name) is str and name in MEANING_FIELDS, "MEANING_FIELD_UNKNOWN")
        values = self.meaning_text; values[name] = text; self.set_meaning_fields(values)

    def set_meaning_fields(self, values):
        require(type(values) is dict and set(values) == set(MEANING_FIELDS), "MEANING_FIELDS")
        for text in values.values(): text_hex(text, maximum=16384)
        require(sum(len(text.encode("utf8")) for text in values.values()) <= 65536, "MEANING_TOTAL_SIZE")
        entry = self._entry()
        if entry["meaning_text"] != values:
            entry["meaning_text"] = dict(values); entry["meaning_edit_generation"] += 1

    def _editor_entry(self, task_id=None):
        selected = self._selected if task_id is None else task_id
        require(type(selected) is str and selected in self._entries, "EDITOR_LOCAL_TASK_REQUIRED")
        return self._entries[selected]

    def editor_recovery_status(self, task_id=None):
        return self._editor_entry(task_id)["editor_state"]

    def editor_recovery_revision(self, task_id=None):
        return self._editor_entry(task_id)["editor_revision"]

    def editor_recovery_error(self, task_id=None):
        return self._editor_entry(task_id)["editor_error"]

    def note_editor_capture_failure(self, task_id, code):
        """An uncaptured widget edit invalidates pending disposal consent."""
        entry = self._editor_entry(task_id)
        require(type(code) is str and 1 <= len(code) <= 160, "EDITOR_CAPTURE_ERROR_REQUIRED")
        entry["editor_capture_generation"] += 1
        entry["editor_error"] = code
        if entry["editor_state"] not in {"SAVING", "LOADING", "DISCARDING", "UNCERTAIN"}:
            entry["editor_state"] = "CONFLICT"

    def editor_recovery_snapshot(self, task_id=None):
        entry = self._editor_entry(task_id)
        return None if entry["editor_snapshot"] is None else decode_editor_snapshot(entry["editor_snapshot"])

    def editor_local_payload(self, task_id=None):
        return self._editor_entry(task_id)["editor_payload"]

    def editor_local_documents(self, task_id=None):
        """Return independent metadata over exact, immutable locally owned bytes.

        The session copy survives Qt deletion while a bounded inline or
        chunked atomic custody write is in progress. It is never task/meaning
        state and is not reported as durable before its bound result.
        """
        captured = self._editor_entry(task_id)["editor_local_documents"]
        if captured is None:
            return None
        basis, widget_revision, documents = captured
        return {"basis_revision": basis, "widget_revision": widget_revision, "documents": {
            name: dict(zip(("utf16le_bytes", "document_id", "document_revision", "cursor_position", "anchor_position"), facts))
            for name, facts in documents}}

    @staticmethod
    def _local_document_map(captured):
        if captured is None:
            return None
        _basis, _widget_revision, documents = captured
        return {name: {"utf16le_hex": facts[0].hex(), "document_id": facts[1],
            "document_revision": facts[2], "cursor_position": facts[3], "anchor_position": facts[4]}
            for name, facts in documents}

    def retain_local_editor_documents(self, task_id, *, basis_revision, widget_revision, documents):
        from ceta.contracts.store_transactions import identifier
        entry = self._editor_entry(task_id)
        require(entry["snapshot"] is not None and entry["revision"] == basis_revision,
                "EDITOR_SAVED_TASK_BASIS_REQUIRED")
        require(type(widget_revision) is int and 0 <= widget_revision < 2**53,
                "EDITOR_WIDGET_REVISION")
        require(type(documents) is dict and set(documents) == set(MEANING_FIELDS), "EDITOR_DOCUMENTS")
        fields = ("utf16le_bytes", "document_id", "document_revision", "cursor_position", "anchor_position")
        captured = []
        for name in MEANING_FIELDS:
            facts = documents[name]
            require(type(facts) is dict and set(facts) == set(fields), "EDITOR_DOCUMENT_SHAPE")
            raw = facts["utf16le_bytes"]
            require(type(raw) is bytes and len(raw) % 2 == 0, "EDITOR_LOCAL_BYTES_REQUIRED")
            identifier(facts["document_id"])
            require(type(facts["document_revision"]) is int and 0 <= facts["document_revision"] < 2**53,
                    "EDITOR_DOCUMENT_REVISION")
            for position in ("cursor_position", "anchor_position"):
                require(type(facts[position]) is int and 0 <= facts[position] <= len(raw) // 2,
                        "EDITOR_DOCUMENT_POSITION")
            captured.append((name, tuple(facts[field] for field in fields)))
        owned = (basis_revision, widget_revision, tuple(captured))
        previous = entry["editor_local_documents"]
        if previous == owned:
            return
        require(previous is None or widget_revision > previous[1], "EDITOR_WIDGET_REVISION_CONFLICT")
        entry["editor_local_documents"] = owned
        entry["editor_capture_generation"] += 1

    @staticmethod
    def _editor_local_matches_payload(entry, payload):
        captured = entry["editor_local_documents"]
        if captured is None:
            return True
        basis, widget_revision, documents = captured
        if basis != payload["basis_revision"] or widget_revision != payload["widget_revision"]:
            return False
        return editor_payload_matches_documents(payload, TaskOperatorSession._local_document_map(captured))

    @property
    def editor_recovery_task_ids(self):
        return tuple(task_id for task_id, entry in self._entries.items()
            if entry["editor_payload"] is not None or entry["editor_local_documents"] is not None
            or (entry["editor_snapshot"] is not None
                and decode_editor_snapshot(entry["editor_snapshot"])["state"] == "RETAINED"))

    def editor_recovery_materialized_payload(self, task_id=None):
        """Return raw documents only after all referenced chunks verified."""
        return self._editor_entry(task_id)["editor_materialized_payload"]

    def retain_editor_documents(self, task_id, payload_wire):
        """Capture exact raw documents without changing validated task fields.

        A queued capture is owned in memory until a bound journal result or a
        later exact load is observed. It is never reported as durable early.
        Newer captures coalesce locally while an older request remains owned.
        """
        payload = decode_editor_payload(payload_wire)
        entry = self._editor_entry(task_id)
        require(entry["snapshot"] is not None and entry["revision"] == payload["basis_revision"],
                "EDITOR_SAVED_TASK_BASIS_REQUIRED")
        if entry["editor_payload"] == payload_wire:
            return
        previous = entry["editor_payload"]
        if previous is not None:
            require(payload["widget_revision"] > decode_editor_payload(previous)["widget_revision"],
                    "EDITOR_WIDGET_REVISION_CONFLICT")
        entry["editor_payload"] = payload_wire
        entry["editor_capture_generation"] += 1
        entry["editor_error"] = None
        entry["editor_chunk_cursor"] = 0
        entry["editor_fetched_chunks"] = {}
        entry["editor_fetch_payload"] = None
        entry["editor_materialized_payload"] = None
        entry["editor_next_attempt_at"] = time.monotonic() + 0.15
        if entry["editor_state"] not in {"SAVING", "LOADING", "DISCARDING", "UNCERTAIN"}:
            entry["editor_state"] = "QUEUED"

    def prioritize_editor_custody(self, task_id=None):
        """Flush a locally owned capture before an invalid/disposal boundary."""
        entry = self._editor_entry(task_id)
        if entry["editor_state"] == "QUEUED":
            entry["editor_next_attempt_at"] = 0.0
        self._drain_editor_recovery()

    def expedite_editor_custody(self, task_id=None):
        """Make an already-owned capture eligible on the next ordinary poll.

        This preserves the UI's nonblocking mutation boundary while ensuring a
        rejected editor value does not wait behind the valid-input coalescing
        interval.  It does not dispatch synchronously or alter accepted task
        or meaning state.
        """
        entry = self._editor_entry(task_id)
        if entry["editor_state"] == "QUEUED":
            entry["editor_next_attempt_at"] = 0.0

    def load_editor_recovery(self, task_id=None, *, fetch_payload=True, discovery=False):
        selected = self._selected if task_id is None else task_id
        entry = self._editor_entry(selected)
        require(entry["snapshot"] is not None or discovery, "EDITOR_SAVED_TASK_REQUIRED")
        return self._submit("editor_load", _target_task_id=selected,
                            _editor_fetch=fetch_payload, _editor_discovery=discovery)

    def discover_editor_recoveries(self, task_ids=None):
        """Read metadata for stored tasks through the public owned-service route.

        Discovery never requests raw chunks and never promotes a recovery into
        task or meaning state. The normal TaskView uses this after it observes
        the catalog, so restart recovery does not depend on a private loader.
        """
        from ceta.contracts.store_transactions import identifier
        candidates = self.task_ids if task_ids is None else tuple(task_ids)
        require(self._pending is None and self.status == "READY", "EDITOR_DISCOVERY_NOT_READY")
        for task_id in candidates:
            identifier(task_id)
            entry = self._ensure_entry(task_id, discovery_only=True)
            if (entry["editor_state"] == "UNOBSERVED" and task_id not in self._editor_discovery_queue):
                self._editor_discovery_queue.append(task_id)
        self._drain_editor_recovery()

    def retry_editor_recovery(self, task_id=None):
        """Explicitly use the observed recovery CAS while retaining local text."""
        selected = self._selected if task_id is None else task_id
        entry = self._editor_entry(selected)
        require(self._pending is None and entry["editor_payload"] is not None,
                "EDITOR_LOCAL_CAPTURE_REQUIRED")
        require(self._editor_local_matches_payload(entry, decode_editor_payload(entry["editor_payload"])),
                "EDITOR_CURRENT_LOCAL_CAPTURE_NOT_SERIALIZED")
        require(entry["editor_state"] not in {"UNCERTAIN", "SAVING", "LOADING", "DISCARDING"},
                "EDITOR_RECONCILIATION_REQUIRED")
        if self.status == "RECOVERING":
            require(entry["editor_observed_task_revision"] is not None, "EDITOR_LOAD_REQUIRED")
            self._service.acknowledge_editor_reconciliation(selected, entry["editor_revision"],
                entry["editor_observed_task_revision"])
            self.status = "READY"
        entry.update(editor_state="QUEUED", editor_error=None, editor_next_attempt_at=0.0)
        self._drain_editor_recovery()

    def discard_editor_recovery(self, task_id=None):
        """Explicitly request a CAS tombstone; caller owns disposal consent."""
        selected = self._selected if task_id is None else task_id
        entry = self._editor_entry(selected)
        require(self._pending is None and entry["editor_state"] not in {"SAVING", "LOADING", "DISCARDING", "UNCERTAIN"},
                "EDITOR_RECONCILIATION_REQUIRED")
        require(entry["editor_revision"] is not None and entry["editor_snapshot"] is not None
                and decode_editor_snapshot(entry["editor_snapshot"])["state"] == "RETAINED",
                "EDITOR_DURABLE_CUSTODY_REQUIRED")
        if self.status == "RECOVERING":
            require(entry["editor_observed_task_revision"] is not None, "EDITOR_LOAD_REQUIRED")
            self._service.acknowledge_editor_reconciliation(selected, entry["editor_revision"],
                entry["editor_observed_task_revision"])
            self.status = "READY"
        entry["editor_discard_generation"] = entry["editor_capture_generation"]
        return self._submit("editor_discard", _target_task_id=selected,
                            editor_expected_revision=entry["editor_revision"])

    def _drain_editor_recovery(self):
        if self._pending is not None or self._context_stopping or self.status != "READY":
            return
        for task_id, entry in self._entries.items():
            if entry["editor_state"] != "QUEUED" or entry["editor_payload"] is None:
                continue
            if entry["editor_next_attempt_at"] > time.monotonic():
                continue
            if not self._editor_local_matches_payload(entry, decode_editor_payload(entry["editor_payload"])):
                entry.update(editor_state="CONFLICT", editor_error=entry["editor_error"]
                    or "EDITOR_CURRENT_LOCAL_CAPTURE_NOT_SERIALIZED")
                continue
            try:
                payload = decode_editor_payload(entry["editor_payload"])
                if payload["profile"] == EDITOR_REFERENCE_PROFILE:
                    documents = self._local_document_map(entry["editor_local_documents"])
                    chunks = editor_payload_chunk_wires(payload, documents)
                    cursor = entry["editor_chunk_cursor"]
                    require(0 <= cursor < len(chunks), "EDITOR_CHUNK_CURSOR")
                    self._submit("editor_retain", _target_task_id=task_id,
                        editor_payload=entry["editor_payload"], editor_expected_revision=entry["editor_revision"],
                        editor_capture_commitment=payload["capture_commitment"], editor_chunk_index=cursor,
                        editor_chunk=chunks[cursor])
                else:
                    self._submit("editor_retain", _target_task_id=task_id,
                        editor_payload=entry["editor_payload"], editor_expected_revision=entry["editor_revision"])
            except SubmissionUncertain:
                entry.update(editor_state="UNCERTAIN", editor_error="EDITOR_DISPATCH_UNCERTAIN")
            except Exception as error:
                from ceta.contracts.wire import ContractError
                entry.update(editor_state="CONFLICT", editor_error=(error.code if isinstance(error, ContractError)
                    else "EDITOR_DISPATCH_FAILED"))
            return
        for task_id, entry in self._entries.items():
            if entry["editor_state"] != "FETCHING" or entry["editor_fetch_payload"] is None:
                continue
            payload = entry["editor_fetch_payload"]
            index = len(entry["editor_fetched_chunks"])
            if index >= payload["chunk_count"]:
                continue
            try:
                self._submit("editor_load", _target_task_id=task_id, _editor_fetch=True,
                    editor_expected_revision=entry["editor_revision"],
                    editor_capture_commitment=payload["capture_commitment"], editor_chunk_index=index)
            except SubmissionUncertain:
                entry.update(editor_state="UNCERTAIN", editor_error="EDITOR_CHUNK_DISPATCH_UNCERTAIN")
            except Exception as error:
                from ceta.contracts.wire import ContractError
                entry.update(editor_state="CONFLICT", editor_error=(error.code if isinstance(error, ContractError)
                    else "EDITOR_CHUNK_DISPATCH_FAILED"))
            return
        while self._editor_discovery_queue:
            task_id = self._editor_discovery_queue.pop(0)
            entry = self._entries.get(task_id)
            if entry is None or entry["editor_state"] != "UNOBSERVED":
                continue
            try:
                self.load_editor_recovery(task_id, fetch_payload=False, discovery=True)
            except SubmissionUncertain:
                entry.update(editor_state="UNCERTAIN", editor_error="EDITOR_DISCOVERY_DISPATCH_UNCERTAIN")
            except Exception as error:
                from ceta.contracts.wire import ContractError
                entry.update(editor_state="CONFLICT", editor_error=(error.code if isinstance(error, ContractError)
                    else "EDITOR_DISCOVERY_DISPATCH_FAILED"))
            return

    def propose_meaning(self):
        require(self.created and self.revision is not None and not self.dirty and not self.has_remote, "MEANING_SAVED_TASK_REQUIRED")
        require(self.meaning_basis_current, "MEANING_TASK_BASIS_LOAD_REQUIRED")
        require(not self.has_meaning_remote, "MEANING_REMOTE_SELECTION_REQUIRED")
        return self._submit("meaning_propose", expected_revision=self.revision,
            meaning=meaning_from_text(self.meaning_text), meaning_expected_revision=self.meaning_revision)

    def load_meaning(self):
        require(self.created, "MEANING_SAVED_TASK_REQUIRED")
        return self._submit("meaning_load")

    def adopt_current_meaning_revision(self):
        entry = self._entry(); remote = entry["meaning_remote"]
        require(remote is not None and self._pending is None, "MEANING_REMOTE_OBSERVATION_REQUIRED")
        proposal, revision, task_revision = remote
        require(task_revision == self.revision and not self.has_remote, "MEANING_TASK_BASIS_LOAD_REQUIRED")
        self._service.acknowledge_meaning_reconciliation(self.task_id, revision, task_revision)
        entry.update(meaning_proposal=proposal, meaning_revision=revision, meaning_remote=None, meaning_persistence="UNSAVED")
    @property
    def persistence(self):
        state = self._entry()["persistence"]
        if state in {"SAVING", "UNCERTAIN", "CONFLICT"}: return state
        return "UNSAVED" if self.dirty or not self.created else "SAVED"

    def set_title(self, text):
        text_hex(text, maximum=256)
        entry = self._entry()
        if text != entry["title"]:
            entry["title"], entry["edit_generation"] = text, entry["edit_generation"] + 1

    def set_draft(self, text):
        text_hex(text)
        entry = self._entry()
        if text != entry["draft"]:
            entry["draft"], entry["edit_generation"] = text, entry["edit_generation"] + 1

    def new_task(self):
        task_id = "task:" + uuid.uuid4().hex
        self.select_task(task_id)
        self._blank_placeholders.add(task_id)
        return self._selected

    @staticmethod
    def _new_entry():
        return {"title": "", "draft": "", "instruction": "", "revision": None,
            "snapshot": None, "remote": None, "edit_generation": 0, "persistence": "UNSAVED",
            "meaning_text": {name: "" for name in MEANING_FIELDS}, "meaning_proposal": None,
            "meaning_revision": None, "meaning_remote": None, "meaning_edit_generation": 0,
            "meaning_persistence": "UNSAVED", "meaning_observed_task_revision": None,
            "editor_payload": None, "editor_snapshot": None, "editor_revision": None,
            "editor_state": "UNOBSERVED", "editor_error": None, "editor_capture_generation": 0,
            "editor_discard_generation": None, "editor_observed_task_revision": None,
            "editor_uncertain_command": None, "editor_local_documents": None,
            "editor_chunk_cursor": 0, "editor_fetched_chunks": {},
            "editor_fetch_payload": None, "editor_materialized_payload": None,
            "editor_next_attempt_at": 0.0,
            "editor_discovery_only": False,
            "context_status": "NONE", "context_result": None, "context_error": None,
            "context_revision": None, "context_edit_generation": None,
            "context_native_observation": None, "context_cancel": None}

    def _ensure_entry(self, task_id, *, discovery_only=False):
        if task_id not in self._entries:
            require(len(self._entries) < 256, "TASK_LOCAL_VIEW_CAPACITY")
            self._entries[task_id] = self._new_entry()
            self._entries[task_id]["editor_discovery_only"] = discovery_only
        return self._entries[task_id]

    def select_task(self, task_id):
        from ceta.contracts.store_transactions import identifier
        identifier(task_id)
        # Reuse only a generated, untouched, unsent empty placeholder. No user
        # text, dispatched selector, stored snapshot or unknown result is evicted.
        old = self._entries.get(self._selected)
        if (task_id != self._selected and self._selected in self._blank_placeholders and old is not None
                and old["edit_generation"] == 0 and not old["title"] and not old["draft"]
                and old["snapshot"] is None and old["remote"] is None and old["persistence"] == "UNSAVED"
                and not any(old["meaning_text"].values())
                and (self._pending is None or self._pending["task_id"] != self._selected)):
            self._blank_placeholders.remove(self._selected)
            del self._entries[self._selected]
        entry = self._ensure_entry(task_id)
        entry["editor_discovery_only"] = False
        self._selected, self._view_generation = task_id, self._view_generation + 1
        self.result_text = ""

    def _submit(self, kind, _context_preview=None, _target_task_id=None,
                _editor_fetch=False, _editor_discovery=False, **values):
        require(self._pending is None, "TASK_CALL_PENDING")
        task_id = None if kind == "list" else self._selected if _target_task_id is None else _target_task_id
        command = decode_command(command_wire(kind, self._scope, "task-command:" + uuid.uuid4().hex,
            task_id=task_id, **values))
        entry = None if task_id is None else self._entries[task_id]
        if task_id is not None: self._blank_placeholders.discard(task_id)
        pending = {"task_id": task_id, "kind": kind, "command": command,
            "view_generation": self._view_generation, "edit_generation": None if entry is None else entry["edit_generation"],
            "meaning_edit_generation": None if entry is None else entry["meaning_edit_generation"],
            "was_dirty": False if entry is None or kind.startswith("editor_") else self._meaning_dirty(entry) if kind.startswith("meaning_") else self._entry_dirty(entry),
            "editor_fetch": bool(_editor_fetch), "editor_discovery": bool(_editor_discovery)}
        if kind.startswith("editor_"):
            pending["editor_capture_generation"] = entry["editor_capture_generation"]
        if _context_preview is not None:
            pending["context_preview"] = _context_preview
        try:
            attempt = self._service.begin_call(command.original_wire, "task." + kind)
        except SubmissionUncertain as error:
            pending["attempt"] = error.attempt; self._pending = pending
            if entry is not None:
                entry["editor_state" if kind.startswith("editor_") else "meaning_persistence" if kind.startswith("meaning_") else "persistence"] = "UNCERTAIN"
            self.status, self.detail = "RECOVERING", "Task dispatch uncertain; captured command and local draft retained."
            raise
        pending["attempt"] = attempt; self._pending = pending
        if entry is not None and kind in {"create", "save"}: entry["persistence"] = "SAVING"
        if entry is not None and kind == "meaning_propose": entry["meaning_persistence"] = "SAVING"
        if kind.startswith("editor_"):
            entry["editor_state"] = {"editor_retain": "SAVING", "editor_load": "LOADING", "editor_discard": "DISCARDING"}[kind]
        self.status, self.detail = "ACTIVE", "Task request reserved; durable completion awaits a bound result."
        return attempt

    def create(self, title=None, instruction=None):
        require(not self.created, "TASK_ALREADY_LOADED")
        require(not self.has_remote, "TASK_REMOTE_SELECTION_REQUIRED")
        if title is not None: self.set_title(title)
        if instruction is not None: self.set_draft(instruction)
        return self._submit("create", title=self.title, instruction=self.draft, draft=self.draft)

    def save(self, title=None, draft=None):
        require(self.created and self.revision is not None, "TASK_LOAD_REQUIRED")
        require(not self.has_remote, "TASK_REMOTE_SELECTION_REQUIRED")
        if title is not None: self.set_title(title)
        if draft is not None: self.set_draft(draft)
        return self._submit("save", expected_revision=self.revision, title=self.title, draft=self.draft)

    def load(self, task_id):
        if task_id != self._selected: self.select_task(task_id)
        return self._submit("load")

    def list_tasks(self): return self._submit("list")

    def adopt_current_revision(self):
        """Explicit user action retains local text and selects observed current CAS."""
        entry = self._entry()
        require(entry["remote"] is not None and self._pending is None, "TASK_REMOTE_OBSERVATION_REQUIRED")
        snapshot, revision = entry["remote"]
        self._service.acknowledge_task_reconciliation(self._selected, revision)
        entry.update(snapshot=snapshot, revision=revision, instruction="" if snapshot is None else text_value(snapshot["instruction_hex"]),
                     remote=None, persistence="UNSAVED")

    def _cancel_context_work(self):
        self._context_stopping = True
        # Attempt every retained cancellation, with the active worker first.
        # One interrupted Event.set must not skip the other owned attempts.
        cancellations = []
        if self._context_job is not None:
            cancellations.append(self._context_job["cancel"])
        for entry in self._entries.values():
            if entry["context_cancel"] is not None:
                cancellations.append(entry["context_cancel"])
        primary, seen = None, set()
        for cancellation in cancellations:
            if id(cancellation) in seen:
                continue
            seen.add(id(cancellation))
            try:
                cancellation.set()
            except BaseException as error:
                self._record_shutdown_failure("SESSION_CANCELLATION_FAILED")
                if primary is None:
                    primary = error
        if primary is not None:
            raise primary

    def _record_shutdown_failure(self, code):
        if code not in self._shutdown_codes:
            self._shutdown_codes.append(code)

    @property
    def shutdown_diagnostic_codes(self):
        return tuple(self._shutdown_codes)

    @property
    def stop_requested(self):
        return self._context_stopping

    def stop(self):
        # Compiler cancellation precedes native Stop and performs no validation.
        self.status, self.detail = "STOPPING", "Stop requested; owned exit has not yet been observed."
        primary = None
        try:
            self._cancel_context_work()
        except BaseException as error:
            primary = error
        observation = None
        try:
            observation = self._service.request_stop()
        except BaseException as error:
            self._record_shutdown_failure("SESSION_SERVICE_STOP_FAILED")
            if primary is None:
                primary = error
        if observation is not None:
            try:
                require(type(observation) is dict and type(observation.get("state")) is str
                        and type(observation.get("detail")) is str, "SESSION_STOP_OBSERVATION_REQUIRED")
                self.status, self.detail = observation["state"], observation["detail"]
            except BaseException as error:
                self._record_shutdown_failure("SESSION_STOP_OBSERVATION_FAILED")
                if primary is None:
                    primary = error
        if self.context_busy:
            self.status = "STOPPING"
            self.detail = "Context work is stopping; its worker remains owned."
        if primary is not None:
            raise primary
        return observation

    @property
    def context_available(self):
        """Whether composition supplied an actual compiler owner."""
        return self._compiler is not None

    @property
    def context_busy(self):
        """Global native call or compiler worker remains owned."""
        return self._pending is not None or self._context_job is not None

    @property
    def context_result(self): return self._entry()["context_result"]

    @property
    def context_error(self): return self._entry()["context_error"]

    @property
    def context_native_observation(self):
        return self._entry()["context_native_observation"]

    @property
    def context_status(self):
        entry = self._entry()
        if entry["context_status"] == "PREVIEW":
            if entry["context_cancel"] is not None and entry["context_cancel"].is_set():
                return "CANCELLED"
            if entry["context_revision"] != entry["revision"]:
                return "STALE"
            if (self.dirty or entry["context_edit_generation"] != entry["edit_generation"]):
                return "LOCAL_DRAFT_CHANGED"
        return entry["context_status"]

    def begin_context_preview(self, profile="conversation", output_tokens=512):
        """Compile a fresh native observation; local drafts remain local."""
        return self._begin_context(profile, output_tokens, "compile")

    def begin_context_revalidation(self):
        """Observe the task anew without renewing an old preparation."""
        entry = self._entry()
        result = entry["context_result"]
        require(result is not None and result.kind == "PREVIEW"
                and result.prepared is not None and self.context_status == "PREVIEW"
                and entry["context_cancel"] is not None,
                "CONTEXT_PREVIEW_REQUIRED")
        return self._begin_context(None, None, "revalidate")

    def _begin_context(self, profile, output_tokens, action):
        require(self._compiler is not None, "REQUEST_COMPILER_OWNER_UNAVAILABLE")
        require(not self._context_stopping and self.status not in {"STOPPING", "STOPPED"},
                "CONTEXT_STOPPED")
        require(self._context_job is None, "CONTEXT_WORK_PENDING")
        require(self.created and self.revision is not None and not self.dirty
                and not self.has_remote, "CONTEXT_SAVED_TASK_REQUIRED")
        if action == "compile":
            require(type(profile) is str and 1 <= len(profile) <= 64, "CONTEXT_PROFILE")
            require(type(output_tokens) is int and 1 <= output_tokens <= 1048576,
                    "CONTEXT_OUTPUT_TOKENS")
        entry = self._entry()
        spec = {"action": action, "profile": profile, "output_tokens": output_tokens,
                "revision": self.revision, "prior_result": entry["context_result"],
                "prior_cancel": entry["context_cancel"]}
        entry.update(context_status="LOADING", context_error=None)
        try:
            return self._submit("load", _context_preview=spec)
        except SubmissionUncertain:
            entry.update(context_status="UNCERTAIN", context_error="CONTEXT_LOAD_UNCERTAIN")
            raise
        except Exception as error:
            from ceta.contracts.wire import ContractError
            entry.update(context_status="DENIED",
                         context_error=error.code if isinstance(error, ContractError) else "CONTEXT_LOAD_FAILED")
            raise

    def _finish_context_load(self, pending, entry, response):
        spec = pending["context_preview"]
        if response is None or response.kind == "DENIED_RECONCILE":
            entry.update(context_status="UNCERTAIN" if response is None else "DENIED",
                         context_error="CONTEXT_LOAD_UNCERTAIN" if response is None else response.error_code)
            return
        result = response.task_result
        revision = validate_result(result, pending["command"], "task.load")
        entry["context_native_observation"] = (
            pending["command"].original_wire, response.original_response, revision)
        if result.kind == "TASK_ABSENT":
            entry.update(context_status="ABSENT", context_error="CONTEXT_TASK_ABSENT")
            return
        if self._context_stopping or self.status in {"STOPPING", "STOPPED"}:
            entry.update(context_status="CANCELLED", context_error="CONTEXT_CANCELLED")
            return
        if (revision != spec["revision"] or pending["was_dirty"]
                or entry["edit_generation"] != pending["edit_generation"]):
            entry.update(context_status="STALE", context_error="CONTEXT_TASK_OR_LOCAL_CHANGED")
            return
        require(self._context_job is None, "CONTEXT_WORK_PENDING")
        if spec["action"] == "revalidate":
            cancel = spec["prior_cancel"]
            require(type(cancel) is threading.Event, "CONTEXT_CANCELLATION_CUSTODY_REQUIRED")
        else:
            # A replacement compilation has fresh custody; its predecessor
            # stays inspectable but cannot be revived through another Event.
            if entry["context_cancel"] is not None:
                entry["context_cancel"].set()
            cancel = threading.Event()
        entry["context_cancel"] = cancel
        job = {"task_id": pending["task_id"], "revision": revision,
               "edit_generation": pending["edit_generation"], "spec": spec,
               "snapshot_wire": result.snapshot_wire, "cancel": cancel,
               "done": threading.Event(), "result": None, "error": None, "thread": None,
               "launch_uncertain": False}
        self._context_job = job
        entry.update(context_status="COMPILING", context_error=None)
        compiler = self._compiler

        def work():
            try:
                if spec["action"] == "revalidate":
                    previous = spec["prior_result"]
                    validated = compiler.revalidate(previous.prepared, job["cancel"].is_set)
                    require(validated is previous.prepared, "CONTEXT_REVALIDATION_SUBSTITUTED")
                    job["result"] = previous
                else:
                    job["result"] = compiler.compile_loaded_task(
                        job["snapshot_wire"], spec["profile"], spec["output_tokens"],
                        job["cancel"].is_set)
                from ceta.contracts.request_compiler import CompilationResult, TaskInput
                result = job["result"]
                require(type(result) is CompilationResult and type(result.kind) is str
                        and result.kind in {"PREVIEW", "CLARIFICATION", "OVERFLOW", "DENIED"}
                        and (result.kind != "PREVIEW" or result.prepared is not None),
                        "CONTEXT_RESULT_REQUIRED")
                require(result.task == TaskInput.from_snapshot(job["snapshot_wire"])
                        and result.task.task_id == job["task_id"]
                        and result.task.task_revision == job["revision"],
                        "CONTEXT_RESULT_TASK_BINDING")
            except BaseException as error:
                # A terminated background callback still needs an owned terminal
                # outcome; it must not leave COMPILING without a worker.
                from ceta.contracts.wire import ContractError
                code = error.code if isinstance(error, ContractError) else None
                job["error"] = (code if type(code) is str and 1 <= len(code) <= 160
                                and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in code)
                                else "CONTEXT_COMPILER_FAILED")
                job["cancel"].set()
            finally:
                job["done"].set()

        try:
            thread = threading.Thread(target=work, name="ceta-context-preview", daemon=True)
        except BaseException as error:
            # No start was attempted. Retire this reserved job on the next poll,
            # including when a process-level exception is propagated to its caller.
            job["cancel"].set()
            job["error"] = "CONTEXT_WORKER_CONSTRUCTION_FAILED"
            job["done"].set()
            if not isinstance(error, Exception):
                raise
            return
        job["thread"] = thread
        try:
            thread.start()
        except BaseException as error:
            job["cancel"].set()
            job["error"] = "CONTEXT_WORKER_START_FAILED"
            # An interrupted start can have created a native thread before its
            # Python identity/target becomes visible. Neither ident=None nor
            # is_alive=False proves absence. Retain this launch's cancellation
            # and ownership until the target finishes and actual exit is seen.
            job["launch_uncertain"] = True
            if not isinstance(error, Exception): raise

    def _poll_context(self):
        job = self._context_job
        if job is None: return
        thread = job["thread"]
        if not job["done"].is_set() or (thread is not None and thread.is_alive()):
            if self._context_stopping:
                self.status = "STOPPING"
                self.detail = ("Context worker launch is unresolved; cancellation and ownership are retained."
                               if job["launch_uncertain"] else
                               "Context work is stopping; its worker remains owned.")
            elif job["launch_uncertain"]:
                entry = self._entries[job["task_id"]]
                entry.update(context_status="LAUNCH_UNCERTAIN", context_error=job["error"])
            return
        entry = self._entries[job["task_id"]]
        self._context_job = None
        if self._context_stopping:
            entry.update(context_status="CANCELLED", context_error="CONTEXT_CANCELLED")
        elif job["error"] is not None:
            entry.update(context_status="DENIED", context_error=job["error"])
        elif job["cancel"].is_set():
            entry.update(context_status="CANCELLED", context_error="CONTEXT_CANCELLED")
        elif (entry["revision"] != job["revision"]
                or entry["edit_generation"] != job["edit_generation"]):
            job["cancel"].set()
            entry.update(context_status="STALE", context_error="CONTEXT_TASK_OR_LOCAL_CHANGED")
        else:
            result = job["result"]
            require(result is not None and result.kind in {"PREVIEW", "CLARIFICATION", "OVERFLOW", "DENIED"},
                    "CONTEXT_RESULT_REQUIRED")
            entry.update(context_status=result.kind, context_result=result,
                         context_error=None, context_revision=job["revision"],
                         context_edit_generation=job["edit_generation"])

    def _meaning_result(self, pending, entry, response):
        if response is None or response.kind == "DENIED_RECONCILE":
            entry["meaning_persistence"] = "CONFLICT" if response is not None and response.error_code in {
                "MEANING_REVISION_CONFLICT", "MEANING_TASK_REVISION_CONFLICT"} else "UNCERTAIN"
            self.detail += " Interpretation text retained; inspect current task and proposal before another write."
            return
        result = response.task_result
        revision = validate_result(result, pending["command"], "task." + pending["kind"])
        entry["meaning_observed_task_revision"] = result.current_task_revision
        proposal = None if result.kind == "TASK_MEANING_ABSENT" else decode_proposal(result.snapshot_wire)
        unchanged = entry["meaning_edit_generation"] == pending["meaning_edit_generation"]
        if proposal is None or (pending["kind"] == "meaning_load" and (pending["was_dirty"] or not unchanged)):
            entry.update(meaning_remote=(proposal, revision, result.current_task_revision), meaning_persistence="UNSAVED")
            self.detail += " Current interpretation observed; local text retained for explicit revision selection."
        else:
            entry.update(meaning_proposal=proposal, meaning_revision=revision, meaning_remote=None,
                meaning_persistence="UNSAVED" if not unchanged else "PROPOSED_UNACCEPTED")
            if pending["kind"] == "meaning_load": entry["meaning_text"] = meaning_as_text(proposal["meaning"])

    @staticmethod
    def _captured_from_materialized(payload):
        documents = tuple((name, (bytes.fromhex(item["utf16le_hex"]), item["document_id"],
            item["document_revision"], item["cursor_position"], item["anchor_position"]))
            for name, item in payload["documents"].items())
        return (payload["basis_revision"], payload["widget_revision"], documents)

    def _editor_result(self, pending, entry, response):
        if response is None or response.kind == "DENIED_RECONCILE":
            code = "EDITOR_TRANSPORT_UNCERTAIN" if response is None else response.error_code
            entry.update(editor_state="CONFLICT" if response is not None else "UNCERTAIN", editor_error=code)
            if pending["kind"] in {"editor_retain", "editor_discard"}:
                entry["editor_uncertain_command"] = pending["command"]
            self.detail += " Full editor documents remain locally owned; inspect stored recovery before another write."
            return
        result = response.task_result
        revision = validate_result(result, pending["command"], "task." + pending["kind"])
        unchanged = entry["editor_capture_generation"] == pending["editor_capture_generation"]
        if result.kind == "TASK_EDITOR_CHUNK":
            payload = entry["editor_fetch_payload"]
            chunk = decode_editor_chunk(result.snapshot_wire)
            if (payload is None or payload["profile"] != EDITOR_REFERENCE_PROFILE
                    or payload["capture_commitment"] != chunk["capture_commitment"]
                    or chunk["chunk_index"] in entry["editor_fetched_chunks"]):
                entry.update(editor_state="CONFLICT", editor_error="EDITOR_CHUNK_RECONCILIATION_FAILED")
                return
            entry["editor_fetched_chunks"][chunk["chunk_index"]] = result.snapshot_wire
            entry["editor_revision"] = revision
            if set(entry["editor_fetched_chunks"]) != set(range(payload["chunk_count"])):
                entry.update(editor_state="FETCHING", editor_error=None)
                return
            try:
                materialized = materialize_editor_payload(payload, tuple(
                    entry["editor_fetched_chunks"][index] for index in range(payload["chunk_count"])))
            except Exception:
                entry.update(editor_state="CONFLICT", editor_error="EDITOR_CHUNK_MATERIALIZATION_FAILED")
                return
            entry.update(editor_materialized_payload=materialized, editor_fetch_payload=None,
                editor_fetched_chunks={})
            if entry["editor_local_documents"] is None:
                entry["editor_local_documents"] = self._captured_from_materialized(materialized)
            if entry["editor_payload"] is None:
                entry.update(editor_state="RETAINED", editor_error=None)
            elif unchanged and self._editor_local_matches_payload(entry, decode_editor_payload(entry["editor_payload"])):
                entry.update(editor_state="RETAINED", editor_error=None)
            else:
                entry.update(editor_state="QUEUED", editor_error=None)
            return
        snapshot = None if result.kind == "TASK_EDITOR_ABSENT" else decode_editor_snapshot(result.snapshot_wire)
        capture_error = entry["editor_error"]
        latest = None if entry["editor_payload"] is None else decode_editor_payload(entry["editor_payload"])
        capture_unserialized = (entry["editor_local_documents"] is not None
            and (latest is None or not self._editor_local_matches_payload(entry, latest)))
        capture_failed_during_call = capture_error is not None and not unchanged
        entry.update(editor_snapshot=result.snapshot_wire, editor_revision=revision,
            editor_observed_task_revision=result.current_task_revision)
        uncertain = entry["editor_uncertain_command"]
        exact_uncertain = (snapshot is not None and uncertain is not None
            and snapshot["request_id"] == uncertain.record_id
            and snapshot["request_commitment"] == uncertain.commitment)
        if exact_uncertain:
            entry["editor_uncertain_command"] = None
        if snapshot is None:
            if capture_unserialized or capture_failed_during_call:
                entry.update(editor_state="CONFLICT", editor_error=capture_error
                    or "EDITOR_CURRENT_LOCAL_CAPTURE_NOT_SERIALIZED")
            else:
                entry.update(editor_state="QUEUED" if entry["editor_payload"] is not None else "ABSENT",
                    editor_error=None)
            return
        if pending["kind"] == "editor_discard":
            if unchanged:
                entry.update(editor_payload=None, editor_local_documents=None, editor_materialized_payload=None,
                    editor_fetch_payload=None, editor_fetched_chunks={}, editor_state="DISCARDED", editor_error=None)
            else:
                entry.update(editor_state="CONFLICT", editor_error="EDITOR_CHANGED_DURING_DISCARD")
            return
        if (pending["kind"] == "editor_load" and exact_uncertain and snapshot["state"] == "DISCARDED"
                and entry["editor_discard_generation"] == entry["editor_capture_generation"]):
            entry.update(editor_payload=None, editor_local_documents=None, editor_materialized_payload=None,
                editor_fetch_payload=None, editor_fetched_chunks={}, editor_state="DISCARDED", editor_error=None)
            return
        from ceta.contracts.wire import canonical_bytes
        stored = canonical_bytes(snapshot["payload"])
        if capture_unserialized or capture_failed_during_call:
            entry.update(editor_state="CONFLICT", editor_error=capture_error
                or "EDITOR_CURRENT_LOCAL_CAPTURE_NOT_SERIALIZED")
        elif snapshot["state"] == "STAGING":
            if entry["editor_payload"] == stored:
                entry.update(editor_chunk_cursor=snapshot["staged_chunk_count"], editor_state="QUEUED",
                    editor_error=None, editor_next_attempt_at=0.0)
            elif entry["editor_payload"] is None:
                entry.update(editor_state="STAGING", editor_error="EDITOR_STAGING_RECOVERY_INCOMPLETE")
            else:
                # A later local mutation may race an acknowledged earlier
                # chunk.  Keep its raw custody and let the kernel atomically
                # supersede the incomplete staging capture; neither capture is
                # misreported as validated meaning or as discarded.
                entry.update(editor_chunk_cursor=0, editor_state="QUEUED",
                    editor_error=None, editor_next_attempt_at=0.0)
        elif (pending["kind"] == "editor_load" and pending["editor_fetch"]
                and snapshot["state"] == "RETAINED"
                and snapshot["payload"]["profile"] == EDITOR_REFERENCE_PROFILE):
            entry.update(editor_fetch_payload=snapshot["payload"], editor_fetched_chunks={},
                editor_state="FETCHING", editor_error=None)
        elif entry["editor_payload"] is None:
            entry.update(editor_state=snapshot["state"], editor_error=None)
        elif entry["editor_payload"] == stored and snapshot["state"] == "RETAINED":
            entry.update(editor_state="RETAINED", editor_error=None)
        elif pending["kind"] == "editor_retain":
            entry.update(editor_state="QUEUED", editor_error=None)
        else:
            entry.update(editor_state="CONFLICT", editor_error="EDITOR_LOCAL_AND_STORED_DIFFER")

    def poll(self):
        try:
            observation = self._service.poll()
            require(type(observation) is dict and type(observation.get("state")) is str
                    and type(observation.get("detail")) is str, "SESSION_SERVICE_OBSERVATION_REQUIRED")
        except BaseException:
            self._record_shutdown_failure("SESSION_SERVICE_OBSERVATION_FAILED")
            self.status = "STOPPING" if self._context_stopping else "RECOVERING"
            self.detail = "Service observation failed; owned work and local drafts are retained."
            if self._context_stopping:
                try:
                    self._cancel_context_work()
                except BaseException:
                    self._record_shutdown_failure("SESSION_CANCELLATION_FAILED")
            raise
        self.status, self.detail = observation["state"], observation["detail"]
        try:
            if self.status in {"STOPPING", "STOPPED"}:
                # Publish retained work before calling cancellation hooks. The
                # UI also observes this status when a hook interrupts the poll.
                if self.context_busy:
                    self.status = "STOPPING"
                    self.detail = "Context work is stopping; its worker remains owned."
                self._cancel_context_work()
            self._poll_context()
            if observation["state"] == "STOPPED" and not self.context_busy:
                # The retained context work was settled by this successful poll.
                self.status, self.detail = observation["state"], observation["detail"]
        except BaseException:
            self._record_shutdown_failure("SESSION_CONTEXT_OBSERVATION_FAILED")
            self.status = "STOPPING" if self._context_stopping else "RECOVERING"
            self.detail = "Context observation failed; worker ownership and local drafts are retained."
            raise
        pending, call = self._pending, observation.get("call")
        if pending is None or call is None or call.get("attempt") != pending["attempt"]:
            self._drain_editor_recovery()
            return observation
        response = call.get("response")
        signature = (call["attempt"], call.get("kind"), None if response is None else response.original_response)
        if signature == self._handled: return observation
        self._handled, self._pending = signature, None
        entry = None if pending["task_id"] is None else self._entries[pending["task_id"]]
        if pending["kind"].startswith("editor_"):
            self._editor_result(pending, entry, response)
        elif pending["kind"].startswith("meaning_"):
            self._meaning_result(pending, entry, response)
        elif response is None or response.kind == "DENIED_RECONCILE":
            if entry is not None:
                entry["persistence"] = "CONFLICT" if response is not None and response.error_code == "TASK_REVISION_CONFLICT" else "UNCERTAIN"
            self.detail += " Local draft retained; load current state before another write."
        else:
            result = response.task_result
            revision = validate_result(result, pending["command"], "task." + pending["kind"])
            if result.kind == "TASK_LIST": self.task_ids = result.task_ids
            elif result.kind == "TASK_ABSENT":
                entry["remote"] = (None, None)
                entry["persistence"] = "UNSAVED"
                self.detail += " Current task absence observed; local text retained. Select this state explicitly before creation."
            else:
                snapshot = decode_snapshot(result.snapshot_wire)
                entry["meaning_observed_task_revision"] = revision
                unchanged_local = entry["edit_generation"] == pending["edit_generation"]
                if pending["kind"] == "load" and (pending["was_dirty"] or not unchanged_local):
                    entry["remote"] = (snapshot, revision)
                    entry["persistence"] = "UNSAVED"
                    self.detail += " Stored version observed; unsaved local text preserved. Select its revision explicitly before saving."
                else:
                    entry.update(snapshot=snapshot, revision=revision, instruction=text_value(snapshot["instruction_hex"]),
                                 remote=None, persistence="SAVED")
                    if pending["kind"] == "load":
                        entry.update(title=text_value(snapshot["title_hex"]), draft=text_value(snapshot["draft_hex"]))
                    if not unchanged_local: entry["persistence"] = "UNSAVED"
                self.task_ids = tuple(dict.fromkeys((*self.task_ids, snapshot["task_id"])))
        if "context_preview" in pending:
            self._finish_context_load(pending, entry, response)
        if pending["task_id"] == self._selected and pending["view_generation"] == self._view_generation:
            self.result_text = response.original_response.decode("utf8") if response is not None else "Task transport result uncertain; local draft retained."
        self._drain_editor_recovery()
        return observation
