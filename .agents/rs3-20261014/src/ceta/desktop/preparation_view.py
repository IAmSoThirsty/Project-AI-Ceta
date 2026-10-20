"""Inspectable native request preparation over the existing task session.

This view owns no compiler, worker, persistence or positive authority. Immutable
result bytes are paged separately from latest attempt and native observations.
"""
from __future__ import annotations

import json
import unicodedata

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFontDatabase, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QHBoxLayout,
    QLabel, QPlainTextEdit, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

from ceta.contracts.local_ipc import SubmissionUncertain
from ceta.contracts.request_compiler import FIELD_NAMES, PARTITIONS, PROFILES, metadata
from ceta.contracts.wire import ContractError
from ceta.desktop.accessibility import AccessibleBindings


def _metadata_bytes(value):
    """Inspection metadata, never substituted for any original byte witness."""
    return json.dumps(metadata(value), default=metadata,
                      ensure_ascii=True, indent=2).encode("ascii")


def _label(text="", accessible=""):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    if accessible:
        widget.setAccessibleName(accessible)
    return widget


def _set_label(widget, text):
    if widget.text() != text:
        widget.setText(text)


def _readable_text(raw):
    """Readable projection of a bounded caller-supplied byte slice, not evidence."""
    escapes = {"\0": r"\x00", "\t": r"\t", "\n": r"\n", "\r": r"\r"}
    visible = []
    for char in raw.decode("utf8", errors="backslashreplace"):
        if char in escapes:
            visible.append(escapes[char])
        elif unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"}:
            code = ord(char)
            visible.append((f"\\x{code:02x}" if code <= 0x7f
                            else f"\\u{code:04x}" if code <= 0xffff
                            else f"\\U{code:08x}"))
        else:
            visible.append(char)
    return "".join(visible)


class ByteInspector(QWidget):
    """Bounded exact byte/token pages; never a whole payload text conversion."""
    PAGE_BYTES = 1024
    PAGE_TOKENS = 128

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items, self._shown = {}, None
        layout = QVBoxLayout(self)
        self.content_picker = QComboBox()
        self.content_picker.setAccessibleName("Preparation evidence item")
        layout.addWidget(self.content_picker)
        navigation = QHBoxLayout()
        self.previous_button = QPushButton("Previous page")
        self.next_button = QPushButton("Next page")
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.setAccessibleName("Evidence page, starting at one")
        for widget in (self.previous_button, self.page_spin, self.next_button):
            navigation.addWidget(widget)
            if isinstance(widget, QPushButton):
                widget.setAutoDefault(False)
        layout.addLayout(navigation)
        self.page_label = _label(accessible="Exact page offsets and total count")
        layout.addWidget(self.page_label)
        self.byte_editor = QPlainTextEdit()
        self.byte_editor.setReadOnly(True)
        self.byte_editor.setAccessibleName("Hexadecimal and escaped exact bytes or token IDs")
        self.byte_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.byte_editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        layout.addWidget(self.byte_editor, 1)
        self.readable_label = _label(accessible="Readable page bounds and decoding")
        layout.addWidget(self.readable_label)
        self.readable_editor = QPlainTextEdit()
        self.readable_editor.setReadOnly(True)
        self.readable_editor.setAccessibleName("Readable current byte page")
        self.readable_editor.setMaximumHeight(110)
        layout.addWidget(self.readable_editor)
        self.accessibility = AccessibleBindings(self, self.page_label, name="CETA evidence pages")
        self.setAccessibleName("Bounded preparation evidence inspector")
        self.byte_editor.setAccessibleDescription("Read-only current byte or token page, with exact offsets. Tab moves to the next control.")
        self.readable_editor.setAccessibleDescription("Read-only readable projection of this bounded page; complete exact bytes remain in the hexadecimal page.")
        self.accessibility.set_focus_order((self.content_picker, self.previous_button,
            self.page_spin, self.next_button, self.page_label, self.byte_editor,
            self.readable_label, self.readable_editor))
        self.content_picker.currentIndexChanged.connect(self._select_item)
        self.page_spin.valueChanged.connect(self._paint_page)
        self.previous_button.clicked.connect(
            lambda: self.page_spin.setValue(self.page_spin.value() - 1))
        self.next_button.clicked.connect(
            lambda: self.page_spin.setValue(self.page_spin.value() + 1))

    def set_items(self, items):
        # Reuse immutable result descriptors. Unchanged selection/data/page must
        # retain the document, cursor, selection and scroll position.
        selected = self.content_picker.currentText()
        page = self.page_spin.value()
        self._items = items
        keys = tuple(items)
        old_keys = tuple(self.content_picker.itemText(i)
                         for i in range(self.content_picker.count()))
        if old_keys != keys:
            blocked = self.content_picker.blockSignals(True)
            try:
                self.content_picker.clear()
                self.content_picker.addItems(keys)
                index = self.content_picker.findText(selected)
                self.content_picker.setCurrentIndex(max(0, index))
            finally:
                self.content_picker.blockSignals(blocked)
        self._select_item(page=page)

    def _select_item(self, _index=None, *, page=None):
        kind, value = self._items.get(self.content_picker.currentText(),
                                      ("unavailable", "No retained item"))
        size = (len(value) if kind in {"bytes", "tokens"} else 0)
        width = self.PAGE_TOKENS if kind == "tokens" else self.PAGE_BYTES
        pages = max(1, (size + width - 1) // width)
        blocked = self.page_spin.blockSignals(True)
        try:
            self.page_spin.setRange(1, pages)
            self.page_spin.setValue(min(pages, page) if page is not None else 1)
        finally:
            self.page_spin.blockSignals(blocked)
        self._paint_page()

    def _paint_page(self, _page=None):
        name = self.content_picker.currentText()
        kind, value = self._items.get(name, ("unavailable", "No retained item"))
        page = self.page_spin.value()
        signature = (name, kind, value, page)
        if (self._shown is not None and self._shown[0] == name
                and self._shown[1] == kind and self._shown[2] is value
                and self._shown[3] == page):
            return
        self._shown = signature
        if kind == "unavailable":
            heading = "Unavailable: " + value
            text = heading
            readable_heading, readable = "Readable preview unavailable", heading
        else:
            width = self.PAGE_TOKENS if kind == "tokens" else self.PAGE_BYTES
            start = (page - 1) * width
            end = min(len(value), start + width)
            pages = max(1, (len(value) + width - 1) // width)
            unit = "Token IDs" if kind == "tokens" else "Bytes"
            heading = f"{unit} {start}..{end} of {len(value)}; page {page}/{pages}"
            if kind == "tokens":
                readable_heading = "Readable preview: select a byte item"
                readable = "The actual token IDs are shown above."
                rows = [f"{i:08d} | {value[i]}" for i in range(start, end)]
            else:
                readable_heading = (
                    f"Readable bytes {start}..{end} of {len(value)}; "
                    "UTF-8 page with visible control and invalid-byte escapes")
                readable = (_readable_text(value[start:end]) if end > start
                            else "Empty actual bytes.")
                rows = []
                for offset in range(start, end, 16):
                    chunk = value[offset:min(offset + 16, end)]
                    rows.append(f"{offset:08x} | {chunk.hex(' ')} | {repr(chunk)[2:-1]}")
            text = "\n".join(rows) if rows else "Empty actual " + unit.lower() + "."
        _set_label(self.page_label, heading)
        self.byte_editor.setPlainText(text)
        _set_label(self.readable_label, readable_heading)
        self.readable_editor.setPlainText(readable)
        self.previous_button.setEnabled(page > 1)
        self.next_button.setEnabled(page < self.page_spin.maximum())
        self.accessibility.describe_action(self.previous_button, name="Previous evidence page",
            description="Inspect the preceding bounded page of the selected retained item.",
            unavailable_reason="The first page is selected.")
        self.accessibility.describe_action(self.next_button, name="Next evidence page",
            description="Inspect the next bounded page of the selected retained item.",
            unavailable_reason="The last page is selected.")
        self.accessibility.bind_state(context_id="page-selection:" + str(self.content_picker.currentIndex()),
            state=(("Page", str(page)), ("Total pages", str(self.page_spin.maximum()))))


class PreparationView(QDialog):
    """Read-only inspection and explicit preview/revalidation; no dispatch."""
    MEANING_SNIPPET_BYTES = 160
    QUESTION_PREVIEW_BYTES = 1024

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self._session, self._task_id = session, session.task_id
        self._selection_lost = False
        self._error = None
        self._retained_result, self._observation = None, None
        self._observation_items = {}
        self._attempt_items, self._attempt_shown = {}, None
        self._question_shown = object()
        self._native_label = "Latest task-load observation: unavailable."
        self._retained_label = "Retained result: none."
        self.setWindowTitle("CETA Request Preparation")
        self.resize(1060, 900)
        layout = QVBoxLayout(self)
        self.note_label = _label(
            "Choose a profile and output limit, then prepare the saved task. "
            "Inspect the result below. Return to the task to edit or save it. "
            "Preview does not dispatch a request.")
        layout.addWidget(self.note_label)
        controls = QHBoxLayout()
        self.profile_picker = QComboBox()
        self.profile_picker.addItems(sorted(PROFILES))
        self.profile_picker.setCurrentText("conversation")
        self.profile_picker.setAccessibleName("Request profile")
        self.output_tokens_spin = QSpinBox()
        self.output_tokens_spin.setRange(1, 1048576)
        self.output_tokens_spin.setValue(512)
        self.output_tokens_spin.setAccessibleName("Requested output tokens")
        controls.addWidget(_label("Profile"))
        controls.addWidget(self.profile_picker)
        controls.addWidget(_label("Requested output tokens"))
        controls.addWidget(self.output_tokens_spin)
        layout.addLayout(controls)
        self.status_label = _label(accessible="Latest preparation attempt and compiler availability")
        self.detail_label = _label(accessible="Latest attempt errors and native observation")
        self.result_label = _label(accessible="Retained result task revision and binding")
        self.clarification_label = _label(accessible="Clarification workflow and unavailable payload count")
        for widget in (self.status_label, self.detail_label, self.result_label,
                       self.clarification_label):
            layout.addWidget(widget)
        self.clarification_editor = QPlainTextEdit()
        self.clarification_editor.setReadOnly(True)
        self.clarification_editor.setAccessibleName("Readable retained clarification question")
        self.clarification_editor.setMaximumHeight(90)
        layout.addWidget(self.clarification_editor)
        self.meaning_table = QTableWidget(len(FIELD_NAMES), 4)
        self.meaning_table.setHorizontalHeaderLabels(("Field", "Status", "Value", "Attribution"))
        self.meaning_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.meaning_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.meaning_table.cellClicked.connect(self._inspect_meaning)
        self.meaning_table.setAccessibleName("All sixteen meaning fields, status and source attribution")
        self.meaning_table.setMaximumHeight(230)
        self.meaning_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.meaning_table)
        self.inspector = ByteInspector(self)
        layout.addWidget(self.inspector, 1)
        actions = QHBoxLayout()
        self.prepare_button = QPushButton("&Prepare request")
        self.revalidate_button = QPushButton("Check existing preview &freshness")
        self.stop_button = QPushButton("S&top (Esc)")
        self.return_button = QPushButton("&Return to task")
        for widget in (self.prepare_button, self.revalidate_button,
                       self.stop_button, self.return_button):
            widget.setAutoDefault(False)
            actions.addWidget(widget)
        layout.addLayout(actions)
        self.prepare_button.clicked.connect(self._prepare)
        self.revalidate_button.clicked.connect(self._revalidate)
        self.stop_button.clicked.connect(self._stop)
        self.return_button.clicked.connect(self.reject)
        self.stop_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.stop_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.stop_shortcut.setAutoRepeat(False)
        self.stop_shortcut.activated.connect(self._stop)
        self._captured_items = {
            "Captured original input": ("bytes", session.original_instruction.encode("utf8")),
            "Captured saved draft": ("bytes", session.saved_draft.encode("utf8")),
            "Captured task metadata": ("bytes", _metadata_bytes({
                "task_id": self._task_id, "task_revision": session.revision,
                "capture": "Dialog-open observation, not the retained result basis"})),
        }
        self._result_items = self._describe_result(None)
        self.accessibility = AccessibleBindings(self, self.status_label, name="CETA request preparation")
        self.setAccessibleName("Task request preparation and exact evidence")
        self.profile_picker.setAccessibleDescription("Select the purpose profile for explicit preparation of the saved task.")
        self.output_tokens_spin.setAccessibleDescription("Requested finite output limit; this does not admit model generation or reserve authority.")
        self.clarification_editor.setAccessibleDescription("Read-only bounded question preview. Complete exact question bytes remain available in the evidence inspector.")
        self.accessibility.set_focus_order((self.profile_picker, self.output_tokens_spin,
            self.status_label, self.detail_label, self.result_label, self.clarification_label,
            self.clarification_editor, self.meaning_table, self.inspector.content_picker,
            self.inspector.previous_button, self.inspector.page_spin, self.inspector.next_button,
            self.inspector.page_label, self.inspector.byte_editor, self.inspector.readable_label,
            self.inspector.readable_editor, self.prepare_button, self.revalidate_button,
            self.stop_button, self.return_button))
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(50)
        self.poll_timer.timeout.connect(self._poll)
        self._refresh()
        self.poll_timer.start()

    def _ready(self):
        session = self._session
        return (not self._selection_lost and session.task_id == self._task_id
                and session.context_available and not session.context_busy
                and session.status == "READY" and session.created
                and session.revision is not None and not session.dirty
                and not session.has_remote)

    def _prepare(self):
        if not self._ready():
            self._refresh()
            return
        self._action(lambda: self._session.begin_context_preview(
            self.profile_picker.currentText(), self.output_tokens_spin.value()))

    def _revalidate(self):
        if (not self._ready() or self._session.context_status != "PREVIEW"
                or self._retained_result is None
                or self._retained_result.prepared is None):
            self._refresh()
            return
        self._action(self._session.begin_context_revalidation)

    def _action(self, action):
        try:
            action()
            self._error = None
        except SubmissionUncertain:
            self._error = "CONTEXT_LOAD_UNCERTAIN"
        except ContractError as error:
            self._error = error.code
        except Exception:
            self._error = "CONTEXT_UI_ACTION_FAILED"
        self._refresh()

    def _stop(self):
        # Shared cancellation precedes all profile, number and selection checks.
        self._action(self._session.stop)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._stop()
            event.accept()
            return
        super().keyPressEvent(event)

    def _poll(self):
        try:
            self._session.poll()
        except ContractError as error:
            self._error = error.code
        except Exception:
            self._error = "CONTEXT_UI_POLL_FAILED"
        self._refresh()

    def _inspect_meaning(self, row, _column):
        names = sorted(FIELD_NAMES)
        if not 0 <= row < len(names):
            return
        index = self.inspector.content_picker.findText("Meaning value: " + names[row])
        if index >= 0:
            self.inspector.content_picker.setCurrentIndex(index)

    def _describe_result(self, result):
        items = {
            "Preparation notes": ("bytes", _metadata_bytes({
                "result_and_attempt": "Retained result and latest local attempt are separate.",
                "preview": "PREVIEW is local status, not fresh owner/clock validation, "
                           "semantic fidelity, consent, task acceptance or authority.",
                "revalidation": "No separate public owner/clock success receipt exists. "
                                "Returning to PREVIEW alone does not prove fresh revalidation.",
                "native_observation": "The latest exposed task-load observation can predate "
                                      "a failed or uncertain attempt; no public attempt-ID join exists.",
                "readable_preview": "Only bounded byte slices are decoded as UTF-8 with "
                                    "backslashreplace and visible control escapes, without "
                                    "Unicode normalization. Literal escape-like text, page-split "
                                    "UTF-8 and invalid bytes can be ambiguous in this projection; "
                                    "hex offsets and bytes remain the exact witness.",
                "meaning": "Value snippets show at most160 initial bytes; select a field "
                           "row to inspect its complete exact value. Supplied status and "
                           "attribution do not establish semantic fidelity.",
                "clarification": "Return to task, edit, save at its current revision, then "
                                 "prepare again. No answer adoption or correction persistence.",
                "composition": "Production compiler ports and launcher exceptional-exit "
                               "worker ownership remain unfinished; no synthetic fallback.",
            })),
        }
        fields = {} if result is None or result.interpretation is None else {
            field.name: field for field in result.interpretation.fields}
        attribution = []
        for index, name in enumerate(sorted(FIELD_NAMES)):
            field = fields.get(name)
            if field is None:
                status, value, sources = "Not supplied", "Absent field", "No attribution supplied"
                attribution.append({"field": name, "presence": "ABSENT"})
                items["Meaning value: " + name] = ("unavailable", "Field not supplied")
            else:
                status = field.status
                if field.value is None:
                    value = "Unavailable (emitted None)"
                else:
                    end = min(len(field.value), self.MEANING_SNIPPET_BYTES)
                    value = (f"Bytes 0..{end} of {len(field.value)}: "
                             + (_readable_text(field.value[:end]) if end
                                else "Empty actual bytes.")
                             + (" [more bytes; select row]" if end < len(field.value) else ""))
                sources = str(len(field.source_ids)) + " source IDs; inspect attribution pages"
                attribution.append({"field": name, "presence": "EMITTED",
                    "status": field.status, "source_ids": field.source_ids,
                    "mandatory": field.mandatory,
                    "value_bytes": None if field.value is None else len(field.value)})
                items["Meaning value: " + name] = (
                    ("unavailable", "Emitted field has no value") if field.value is None
                    else ("bytes", field.value))
            for column, text in enumerate((name, status, value, sources)):
                cell = QTableWidgetItem(text)
                cell.setToolTip("Select this row to inspect its exact value bytes.")
                self.meaning_table.setItem(index, column, cell)
        items["Meaning fields and attribution"] = ("bytes", _metadata_bytes(attribution))
        items["Rendered payload"] = ("unavailable", "No rendered payload in this retained result")
        items["Token IDs"] = ("unavailable", "No token IDs in this retained result")
        items["Tokenization attribution"] = ("unavailable", "No tokenization object in this retained result")
        if result is None:
            return items
        task = result.task
        items.update({
            "Retained original input": ("bytes", task.original),
            "Retained latest input": ("bytes", task.latest),
            "Retained task snapshot": ("bytes", task.snapshot_wire),
            "Retained task metadata": ("bytes", _metadata_bytes({
                "task_id": task.task_id, "scope_id": task.scope_id,
                "principal_id": task.principal_id, "owner_binding": task.owner_binding,
                "task_revision": task.task_revision,
                "objective_revision": task.objective_revision,
                "objective_generation": task.objective_generation})),
            "Retained title": ("bytes", task.title),
            "Omissions and material markers": ("bytes", _metadata_bytes(result.omissions)),
        })
        if result.rendered_payload is not None:
            items["Rendered payload"] = ("bytes", result.rendered_payload)
        if result.question is not None:
            items["Clarification question"] = ("bytes", result.question)
        if result.interpretation is not None:
            questions = result.interpretation.questions
            items["Question reasons and references"] = ("bytes", _metadata_bytes([
                {"index": i, "reason": q.reason, "material": q.material,
                 "dependent_task_id": q.dependent_task_id, "source_ids": q.source_ids,
                 "text_bytes": len(q.text)} for i, q in enumerate(questions)]))
            for i, question in enumerate(questions):
                items["Question: " + str(i)] = ("bytes", question.text)
            items["Interpretation basis and drift"] = ("bytes", _metadata_bytes({
                "basis_commitment": result.interpretation.basis_commitment,
                "drift_status": None if result.selection is None else result.selection.drift_status,
                "drift_evidence_ids": () if result.selection is None else result.selection.drift_evidence_ids,
                "limit": "Attribution/status are supplied claims, not a semantic fidelity verdict"}))
        source_rows = []
        for i, source in enumerate(result.sources):
            items[f"Source: {i} [{source.partition}]"] = ("bytes", source.content)
            source_rows.append({"index": i, "source_id": source.source_id,
                "revision": source.revision, "partition": source.partition,
                "mandatory": source.mandatory, "coding_only": source.coding_only,
                "audit_only": source.audit_only,
                "omission_changes_task": source.omission_changes_task,
                "content_bytes": len(source.content)})
        items["Sources and six partitions"] = ("bytes", _metadata_bytes({
            "partitions": {p: sum(s.partition == p for s in result.sources)
                           for p in sorted(PARTITIONS)},
            "selected_sources": source_rows,
            "limit": "Selected sources and emitted model parts are separate; an omitted source may remain inspectable"}))
        if result.selection is not None:
            items["Selection state and runtime pins"] = ("bytes", _metadata_bytes(result.selection.state))
            items["Selected quotation requests"] = ("bytes", _metadata_bytes(result.selection.quotes))
        prepared = result.prepared
        if prepared is not None:
            items["Prepared binding"] = ("bytes", prepared.binding_wire)
            items["Context original wire"] = ("bytes", prepared.context.original_wire)
            items["Context canonical wire"] = ("bytes", prepared.context.canonical_wire)
            items["Prepared clock"] = ("bytes", _metadata_bytes(prepared.prepared_clock))
            tokenization = prepared.tokenization
            items["Token IDs"] = ("tokens", tokenization.token_ids)
            items["Tokenization attribution"] = ("bytes", _metadata_bytes({
                "runtime": tokenization.runtime,
                "payload_commitment": tokenization.payload_commitment,
                "input_tokens": len(tokenization.token_ids),
                "exact": tokenization.exact,
                "includes_special_tokens": tokenization.includes_special_tokens}))
            part_rows = []
            for i, part in enumerate(prepared.parts):
                items[f"Part: {i} [{part.partition}/{part.status}]"] = ("bytes", part.content)
                part_rows.append({"index": i, "partition": part.partition,
                                  "status": part.status, "content_bytes": len(part.content)})
            items["Model part roles"] = ("bytes", _metadata_bytes(part_rows))
        return items

    def _refresh(self):
        session = self._session
        if session.task_id != self._task_id:
            # Latch A -> B -> A. Reopening a dialog is an explicit new capture.
            self._selection_lost = True
        changed = False
        if not self._selection_lost:
            result, observation = session.context_result, session.context_native_observation
            if result is not self._retained_result:
                if result is not None and result.task.task_id != self._task_id:
                    self._selection_lost = True
                    self._error = "CONTEXT_RESULT_TARGET_CHANGED"
                else:
                    self._retained_result = result
                    self._result_items = self._describe_result(result)
                    changed = True
                    if result is None:
                        self._retained_label = "Retained result: none."
                    else:
                        binding = ("Unavailable" if result.prepared is None
                                   else result.prepared.commitment)
                        count = "Unavailable" if result.input_tokens is None else str(result.input_tokens)
                        self._result_items["Retained result basis"] = ("bytes", _metadata_bytes({
                            "kind": result.kind, "task_id": result.task.task_id,
                            "task_revision": result.task.task_revision,
                            "objective_revision": result.task.objective_revision,
                            "objective_generation": result.task.objective_generation,
                            "prepared_commitment": None if result.prepared is None else binding,
                            "input_tokens": result.input_tokens,
                            "reason_code": result.reason_code,
                        }))
                        self._retained_label = (
                            f"Retained result: {result.kind} | Task {result.task.task_id}\n"
                            f"Result task CAS: {result.task.task_revision}\n"
                            f"Objective: {result.task.objective_revision} / {result.task.objective_generation}\n"
                            f"Prepared binding: {binding} | Actual input tokens: {count}\n"
                            f"Result reason: {result.reason_code or 'Not supplied'}")
            if not self._selection_lost and observation is not self._observation:
                self._observation = observation
                self._observation_items = {}
                if observation is None:
                    self._native_label = "Latest task-load observation: unavailable."
                else:
                    request, response, revision = observation
                    self._native_label = (
                        f"Latest task-load observation for task {self._task_id}: {revision}. "
                        "Inspect its request and response below.")
                    self._observation_items = {
                        "Latest native request": ("bytes", request),
                        "Latest native response": ("bytes", response),
                        "Latest native revision": ("bytes", _metadata_bytes({
                            "captured_task_id": self._task_id, "observed_task_revision": revision})),
                    }
                changed = True
            if not self._selection_lost:
                attempt = (session.context_status, session.context_error, session.status,
                           session.context_available, self._error)
                if attempt != self._attempt_shown:
                    self._attempt_shown = attempt
                    self._attempt_items = {
                        "Latest attempt details": ("bytes", _metadata_bytes({
                            "captured_task_id": self._task_id,
                            "local_context_status": session.context_status,
                            "context_error": session.context_error,
                            "shared_service_status": session.status,
                            "compiler_available": session.context_available,
                            "dialog_error": self._error,
                            "limit": "Local status and errors are not a separate owner/clock "
                                     "success receipt or a native-observation attempt-ID join.",
                        })),
                    }
                    changed = True
        if changed or not self.inspector._items:
            self.inspector.set_items({**self._captured_items, **self._result_items,
                                      **self._observation_items, **self._attempt_items})
        if self._selection_lost:
            attempt = "Selection changed; captured content retained. Return and reopen for the selected task."
            detail = "Return to task and reopen preparation for the selected task."
        else:
            attempt = "Latest preparation attempt/local status: " + session.context_status
            detail = ("Preparation error: " + (session.context_error or "None reported")
                      + "\n" + self._native_label)
        availability = ("Compiler available" if session.context_available
                        else "Compiler unavailable in this build; preparation is disabled")
        _set_label(self.status_label, f"Captured task {self._task_id} | {availability}\n{attempt}")
        _set_label(self.detail_label, detail + "\nShared service: " + session.status
                   + (" | Request error: " + self._error if self._error else ""))
        _set_label(self.result_label, self._retained_label)
        result = self._retained_result
        if result is not None and result.kind == "CLARIFICATION":
            question_end = min(len(result.question), self.QUESTION_PREVIEW_BYTES)
            guidance = (
                "Retained clarification: return to task, edit the draft, save it, then prepare again. "
                f"Question preview bytes 0..{question_end} of {len(result.question)}; "
                "inspect Clarification question for all exact bytes and question references.")
        else:
            payload = ("Unavailable" if result is None or result.rendered_payload is None
                       else str(len(result.rendered_payload)) + " actual bytes")
            tokens = "Unavailable" if result is None or result.input_tokens is None else str(result.input_tokens)
            guidance = f"Retained rendered payload: {payload}; actual input count: {tokens}. Byte/token pages disclose offsets and totals."
        _set_label(self.clarification_label, guidance)
        question = None if result is None else result.question
        if question is not self._question_shown:
            self._question_shown = question
            self.clarification_editor.setVisible(question is not None)
            self.clarification_editor.setPlainText(
                "" if question is None else _readable_text(
                    question[:self.QUESTION_PREVIEW_BYTES]))
        ready = self._ready()
        self.prepare_button.setEnabled(ready)
        self.revalidate_button.setEnabled(ready and session.context_status == "PREVIEW"
            and result is not None and result.kind == "PREVIEW" and result.prepared is not None)
        self.profile_picker.setEnabled(ready)
        self.output_tokens_spin.setEnabled(ready)
        self.stop_button.setEnabled(True)
        self.return_button.setEnabled(True)
        self._bind_accessibility()

    def _bind_accessibility(self):
        session = self._session
        if self._selection_lost or session.task_id != self._task_id:
            reason = "A different task is selected; return and reopen preparation for it. Captured evidence remains inspectable."
        elif not session.context_available:
            reason = "No compiler owner is available in this composition; retained evidence and Stop remain usable."
        elif session.status in {"STOPPING", "STOPPED"}:
            reason = "The owned service is stopping or has stopped."
        elif session.context_busy or session.status != "READY":
            reason = "Wait for the current owned request to finish or use Stop."
        elif not session.created or session.revision is None:
            reason = "Create or load a stored task before preparation."
        elif session.dirty:
            reason = "Save the task draft before preparing its exact current revision."
        elif session.has_remote:
            reason = "Return to the task and select its observed current stored revision first."
        else:
            reason = "The current retained result does not provide a revalidatable preview."
        for widget, name, description, unavailable in (
            (self.prepare_button, "Prepare saved task request",
                "Prepare the saved task with the selected profile and finite output limit. Preview does not dispatch a model request.", reason),
            (self.revalidate_button, "Check retained preview freshness",
                "Revalidate the retained prepared preview against actual current task, compiler and runtime owners.", reason),
            (self.profile_picker, "Request preparation profile",
                "Choose the purpose profile used by an explicit saved-task preparation request.", reason),
            (self.output_tokens_spin, "Requested output token limit",
                "Choose the finite requested output limit; this control does not start or authorize generation.", reason),
            (self.stop_button, "Stop owned service",
                "Escape requests shared Stop immediately, before profile, limit or selection validation. STOPPED requires observed retirement.", reason),
            (self.return_button, "Return to task; retain preparation evidence",
                "Return to the task. The session retains any active owned request and immutable preparation result.", reason),
        ):
            self.accessibility.describe_action(widget, name=name, description=description,
                                               unavailable_reason=unavailable)
        result = self._retained_result
        self.accessibility.bind_state(context_id=self._task_id, state=(
            ("Service", session.status),
            ("Task selection", "Different task selected" if self._selection_lost else "Captured task selected"),
            ("Compiler", "Available" if session.context_available else "Unavailable"),
            ("Latest preparation", "Captured evidence retained" if self._selection_lost else session.context_status),
            ("Retained result", "None" if result is None else result.kind),
            ("Request error", "Reported; inspect detail" if self._error is not None else "None reported"),
        ))

    def done(self, result):
        # Parent/session retains active native calls and workers after Return.
        self.poll_timer.stop()
        super().done(result)
        self.accessibility.close()
        self.inspector.accessibility.close()

    def closeEvent(self, event):
        self.reject()
        event.accept()
