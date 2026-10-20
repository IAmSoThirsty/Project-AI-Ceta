"""Inspect and edit an unaccepted interpretation separately from captured input."""
import uuid
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (QDialog, QFormLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget, QMessageBox)
from ceta.contracts.task_meaning import MEANING_FIELDS, meaning_as_text
from ceta.contracts.wire import ContractError
from ceta.contracts.editor_recovery import (editor_payload_wire, utf16_text_value,
    decode_editor_payload)
from ceta.desktop.accessibility import AccessibleBindings

LABELS = {"clarified_meaning": "Objective", "scope": "Scope", "exclusions": "Exclusions",
    "completion_predicates": "Done when", "assumptions": "Assumptions", "unresolved_questions": "Open questions",
    "standing_instructions": "Standing instructions", "authority": "Requested authority",
    "budgets": "Requested limits", "evidence": "Supporting evidence"}

class MeaningView(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self._session, self._task_id, self._rendered = session, session.task_id, None
        self._error, self._text_error = None, None
        self._return_authorized, self._recovery_error = False, None
        self._widget_revision = 0
        self._recovery_active, self._restore_requested, self._discard_requested = False, False, False
        self._return_after_discard = None
        self._restored_source_facts = None
        self._document_owners = {}
        self.setWindowTitle("CETA Task Interpretation"); self.resize(820, 780)
        layout = QVBoxLayout(self)
        note = QLabel("Keep the original request and its interpretation separate. Recording a proposal does not accept the task or authorize work.")
        note.setTextFormat(Qt.TextFormat.PlainText); note.setWordWrap(True); layout.addWidget(note)
        layout.addWidget(QLabel("Original submitted instruction"))
        self.original_editor = QPlainTextEdit(session.original_instruction); self.original_editor.setReadOnly(True)
        self.original_editor.setAccessibleName("Original instruction for interpretation"); self.original_editor.setMaximumHeight(120)
        layout.addWidget(self.original_editor)
        layout.addWidget(QLabel("Loaded saved draft"))
        self.basis_editor = QPlainTextEdit(session.saved_draft); self.basis_editor.setReadOnly(True)
        self.basis_editor.setAccessibleName("Loaded saved task draft"); self.basis_editor.setMaximumHeight(90)
        layout.addWidget(self.basis_editor)
        layout.addWidget(QLabel("Draft used by selected interpretation"))
        self.proposal_basis_editor = QPlainTextEdit(); self.proposal_basis_editor.setReadOnly(True)
        self.proposal_basis_editor.setAccessibleName("Stored interpretation draft basis"); self.proposal_basis_editor.setMaximumHeight(90)
        layout.addWidget(self.proposal_basis_editor)
        layout.addWidget(QLabel("Latest stored observation before revision selection"))
        self.observation_editor = QPlainTextEdit(); self.observation_editor.setReadOnly(True)
        self.observation_editor.setAccessibleName("Observed stored interpretation and draft basis")
        self.observation_editor.setMaximumHeight(140); layout.addWidget(self.observation_editor)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        form_widget = QWidget(); form = QFormLayout(form_widget)
        self.editors = {}
        for name in MEANING_FIELDS:
            editor = QPlainTextEdit(); editor.setMaximumHeight(90); editor.setTabChangesFocus(True)
            editor.setAccessibleName(LABELS[name]); self.editors[name] = editor
            self._document_owners[name] = (editor.document(), "editor-document:" + uuid.uuid4().hex)
            editor.textChanged.connect(lambda field=name, widget=editor: self._edited(field, widget))
            editor.cursorPositionChanged.connect(self._editor_facts_changed)
            editor.selectionChanged.connect(self._editor_facts_changed)
            form.addRow(LABELS[name], editor)
        scroll.setWidget(form_widget); layout.addWidget(scroll, 1)
        actions = QHBoxLayout()
        self.propose_button = QPushButton("Record &proposal")
        self.load_button = QPushButton("&Inspect stored proposal")
        self.adopt_button = QPushButton("Use observed revision; keep my text")
        self.close_button = QPushButton("&Return to task")
        self.stop_button = QPushButton("S&top (Esc)")
        for widget in (self.propose_button, self.load_button, self.adopt_button, self.stop_button, self.close_button): actions.addWidget(widget)
        layout.addLayout(actions)
        recovery_actions = QHBoxLayout()
        self.retain_recovery_button = QPushButton("Retain recovery copy")
        self.load_recovery_button = QPushButton("Load retained edits")
        self.discard_recovery_button = QPushButton("Discard retained edits")
        for widget in (self.retain_recovery_button, self.load_recovery_button, self.discard_recovery_button):
            recovery_actions.addWidget(widget)
        layout.addLayout(recovery_actions)
        self.retain_recovery_button.clicked.connect(self._retain_editor)
        self.load_recovery_button.clicked.connect(self._load_editor)
        self.discard_recovery_button.clicked.connect(self._discard_editor)
        self.status_label = QLabel(); self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.status_label.setAccessibleName("Interpretation proposal status"); layout.addWidget(self.status_label)
        self.detail_label = QLabel(); self.detail_label.setTextFormat(Qt.TextFormat.PlainText)
        self.detail_label.setWordWrap(True); layout.addWidget(self.detail_label)
        self.propose_button.clicked.connect(lambda: self._action(session.propose_meaning))
        self.load_button.clicked.connect(lambda: self._action(session.load_meaning))
        self.adopt_button.clicked.connect(lambda: self._action(session.adopt_current_meaning_revision))
        self.close_button.clicked.connect(self.reject)
        self.stop_button.clicked.connect(self._stop)
        self.accessibility = AccessibleBindings(self, self.status_label, name="CETA interpretation")
        self.setAccessibleName("Unaccepted task interpretation and retained edits")
        self.detail_label.setAccessibleName("Interpretation blockers and editor recovery status")
        for editor in (self.original_editor, self.basis_editor, self.proposal_basis_editor,
                       self.observation_editor):
            editor.setAccessibleDescription("Read-only source observation. Tab moves to the next field; this text does not approve work.")
        for editor in self.editors.values():
            editor.setAccessibleDescription("Editable unaccepted interpretation field. Recording a proposal does not accept the task or authorize work.")
        self.accessibility.set_focus_order((self.original_editor, self.basis_editor,
            self.proposal_basis_editor, self.observation_editor, *self.editors.values(),
            self.propose_button, self.load_button, self.adopt_button, self.stop_button,
            self.close_button, self.retain_recovery_button, self.load_recovery_button,
            self.discard_recovery_button, self.status_label, self.detail_label))
        self.poll_timer = QTimer(self); self.poll_timer.setInterval(50); self.poll_timer.timeout.connect(self._poll)
        self._refresh(); self.poll_timer.start()

    def _edited(self, name, editor):
        if self._session.task_id != self._task_id: self._refresh(); return
        self._discard_requested = False
        self._return_after_discard = None
        # Custody begins with every widget mutation, before validating whether
        # the visible text can become an interpretation proposal.
        self._capture_editor()
        try:
            self._session.set_meaning_fields({field: widget.toPlainText() for field, widget in self.editors.items()})
            self._text_error = self._error = None
        except ContractError as error:
            self._text_error = self._error = error.code
            self._session.expedite_editor_custody(self._task_id)
        self._refresh()

    def _editor_facts_changed(self):
        if self._recovery_active and not self._restore_requested:
            self._discard_requested = False
            self._return_after_discard = None
            self._capture_editor()

    def _capture_editor(self):
        if self._session.task_id != self._task_id or not self._session.created:
            return
        self._recovery_active = True
        snapshot = self._session.editor_recovery_snapshot(self._task_id)
        if snapshot is not None:
            self._widget_revision = max(self._widget_revision, snapshot["payload"]["widget_revision"])
        self._widget_revision += 1
        documents, local_documents = {}, {}
        try:
            for name, editor in self.editors.items():
                cursor = editor.textCursor()
                document = editor.document()
                previous, document_id = self._document_owners[name]
                if document is not previous:
                    document_id = "editor-document:" + uuid.uuid4().hex
                    self._document_owners[name] = (document, document_id)
                raw = document.toRawText().encode("utf-16-le", errors="surrogatepass")
                local_documents[name] = {"utf16le_bytes": raw,
                    "document_id": document_id, "document_revision": document.revision(),
                    "cursor_position": cursor.position(), "anchor_position": cursor.anchor()}
            self._session.retain_local_editor_documents(self._task_id, basis_revision=self._session.revision,
                widget_revision=self._widget_revision, documents=local_documents)
            for name, facts in local_documents.items():
                documents[name] = {"utf16le_hex": facts["utf16le_bytes"].hex(),
                    **{key: facts[key] for key in ("document_id", "document_revision", "cursor_position", "anchor_position")}}
            wire = editor_payload_wire(basis_revision=self._session.revision,
                widget_revision=self._widget_revision, documents=documents)
            self._session.retain_editor_documents(self._task_id, wire)
            self._recovery_error = None
        except Exception as error:
            # Serialization, Qt access, or service dispatch may fail after a
            # mutation. The live document stays open and the session marks the
            # capture retryable instead of treating a runtime fault as consent.
            code = error.code if isinstance(error, ContractError) else "EDITOR_CAPTURE_RUNTIME_FAILURE"
            try:
                self._session.note_editor_capture_failure(self._task_id, code)
            except Exception:
                pass
            self._recovery_error = "Recovery copy is not durable: " + code + ". Full documents remain in this window."

    def _retain_editor(self):
        if self._session.task_id != self._task_id:
            return
        self._capture_editor()
        self._session.prioritize_editor_custody(self._task_id)
        try:
            self._session.retry_editor_recovery(self._task_id)
        except ContractError as error:
            self._recovery_error = error.code
        self._refresh()

    def _load_editor(self):
        if self._session.task_id != self._task_id:
            return
        if self._recovery_active or self._text_error is not None:
            choice = QMessageBox.question(self, "Inspect retained interpretation edits?",
                "Load the stored recovery for inspection? Your current documents will stay visible if they differ.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if choice != QMessageBox.StandardButton.Yes:
                return
        try:
            self._session.load_editor_recovery(self._task_id)
            self._restore_requested = not self._recovery_active
            self._error = None
        except ContractError as error:
            self._recovery_error = error.code
        self._refresh()

    def _discard_editor(self):
        choice = QMessageBox.question(self, "Discard retained interpretation edits?",
            "Deliberately discard these interpretation edits? The stored history will preserve the earlier copy.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if choice != QMessageBox.StandardButton.Yes:
            return
        try:
            self._begin_discard()
            self._recovery_error = None
        except ContractError as error:
            self._recovery_error = error.code
        self._refresh()

    def _begin_discard(self, *, return_result=None):
        """Bind a positive local disposition to the exact captured revision.

        A queued capture is first made durable.  The same intent is then sent
        as the authenticated discard CAS only if that exact capture remains
        current.  Editing any widget clears the local intent before it can
        consume a newer capture.
        """
        self._discard_requested = True
        if return_result is not None:
            self._return_after_discard = return_result
        self._session.prioritize_editor_custody(self._task_id)
        self._dispatch_discard_if_ready()

    def _dispatch_discard_if_ready(self):
        if not self._discard_requested or self._session.task_id != self._task_id:
            return False
        if self._session._pending is not None:
            return False
        if self._session.editor_recovery_status(self._task_id) != "RETAINED":
            return False
        self._session.discard_editor_recovery(self._task_id)
        return True

    def _restore_editor(self):
        if not self._restore_requested or self._session.task_id != self._task_id:
            return
        state = self._session.editor_recovery_status(self._task_id)
        if state in {"LOADING", "SAVING", "DISCARDING"}:
            return
        self._restore_requested = False
        if self._session.editor_recovery_error(self._task_id) is not None:
            return
        snapshot = self._session.editor_recovery_snapshot(self._task_id)
        if snapshot is None or snapshot["state"] != "RETAINED":
            return
        payload = self._session.editor_recovery_materialized_payload(self._task_id)
        if payload is None and snapshot["payload"]["profile"] == "ceta-task-editor-payload-v1":
            payload = snapshot["payload"]
        if payload is None:
            return
        self._apply_editor_payload(payload)
        self._recovery_error = "Stored raw edits recovered. Review and correct them before recording a proposal."

    def recover_local_documents(self):
        """Explicitly recover this task's owned raw capture after Qt deletion."""
        local = self._session.editor_local_documents(self._task_id)
        wire = self._session.editor_local_payload(self._task_id)
        if local is not None:
            payload = {"basis_revision": local["basis_revision"], "widget_revision": local["widget_revision"],
                "documents": {name: {"utf16le_hex": facts["utf16le_bytes"].hex(),
                    **{key: facts[key] for key in ("document_id", "document_revision", "cursor_position", "anchor_position")}}
                    for name, facts in local["documents"].items()}}
            self._apply_editor_payload(payload, local_source=True)
            self._recovery_error = "Locally owned documents recovered; inspect the recovery status for durable completion."
        elif wire is not None:
            self._apply_editor_payload(decode_editor_payload(wire))
            self._recovery_error = "Locally owned documents recovered; inspect the recovery status for durable completion."
        else:
            snapshot = self._session.editor_recovery_snapshot(self._task_id)
            if snapshot is not None and snapshot["state"] == "RETAINED":
                payload = self._session.editor_recovery_materialized_payload(self._task_id)
                if payload is None and snapshot["payload"]["profile"] == "ceta-task-editor-payload-v1":
                    payload = snapshot["payload"]
                if payload is None:
                    try:
                        self._session.load_editor_recovery(self._task_id, fetch_payload=True)
                        self._restore_requested = True
                        self._recovery_error = "Loading bounded retained recovery chunks."
                    except ContractError as error:
                        self._recovery_error = error.code
                else:
                    self._apply_editor_payload(payload)
                    self._recovery_error = "Stored raw edits recovered. Review them before recording a proposal."
        self._refresh()

    def _apply_editor_payload(self, payload, *, local_source=False):
        # The stored source facts remain separate from the new Qt document's
        # native revision. Restoring text never validates or accepts its meaning.
        self._restored_source_facts = payload
        self._widget_revision = payload["widget_revision"]
        self._recovery_active = True
        self._text_error = "EDITOR_RECOVERY_REQUIRES_REVIEW"
        for name, editor in self.editors.items():
            document = payload["documents"][name]
            blocked = editor.blockSignals(True)
            try:
                text = (bytes.fromhex(document["utf16le_hex"]).decode("utf-16-le", errors="surrogatepass")
                    if local_source else utf16_text_value(document["utf16le_hex"]))
                editor.setPlainText(text)
                cursor = editor.textCursor()
                cursor.setPosition(document["anchor_position"])
                cursor.setPosition(document["cursor_position"], cursor.MoveMode.KeepAnchor)
                editor.setTextCursor(cursor)
            finally:
                editor.blockSignals(blocked)

    def _stop(self):
        try: self._session.stop()
        except ContractError as error: self._error = error.code
        self._refresh()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._stop(); event.accept()
        else: super().keyPressEvent(event)

    def _action(self, action):
        if self._session.task_id != self._task_id or self._text_error is not None: return
        try: action(); self._error = None
        except ContractError as error: self._error = error.code
        self._refresh()

    def _poll(self):
        try: self._session.poll()
        except ContractError as error: self._error = error.code
        self._restore_editor()
        if self._discard_requested:
            state = self._session.editor_recovery_status(self._task_id)
            if state == "RETAINED" and self._session._pending is None:
                try:
                    self._dispatch_discard_if_ready()
                except ContractError as error:
                    self._recovery_error = error.code + ". Full documents remain under custody."
            elif state == "DISCARDED":
                result = self._return_after_discard
                self._discard_requested = False
                self._return_after_discard = None
                self._recovery_active = False
                self._text_error = None
                self._recovery_error = "Edits deliberately discarded; historical copies remain available."
                if result is not None:
                    self.done(result)
        self._refresh()

    def _refresh(self):
        session = self._session
        same_task = session.task_id == self._task_id
        if same_task:
            if self.basis_editor.toPlainText() != session.saved_draft: self.basis_editor.setPlainText(session.saved_draft)
            from ceta.contracts.task_drafts import text_value
            proposal = session.meaning_proposal
            basis = "" if proposal is None else text_value(proposal["draft_hex"])
            if self.proposal_basis_editor.toPlainText() != basis: self.proposal_basis_editor.setPlainText(basis)
            observation = session.meaning_observation
            observed_text = ""
            if observation is not None:
                observed, revision, task_revision = observation
                observed_text = "Current saved task revision: " + task_revision
                if observed is None:
                    observed_text = "Observed stored proposal: ABSENT\n" + observed_text
                else:
                    state = "STALE" if observed["basis_revision"] != task_revision else "UNACCEPTED"
                    observed_text = "Observed stored proposal: " + state + "\n" + observed_text
                    observed_text += "\nObserved proposal revision: " + revision
                    observed_text += "\nDraft used by observed proposal:\n" + text_value(observed["draft_hex"])
                    fields = meaning_as_text(observed["meaning"])
                    observed_text += "\n\n" + "\n\n".join(LABELS[name] + ":\n" + fields[name] for name in MEANING_FIELDS)
            if self.observation_editor.toPlainText() != observed_text: self.observation_editor.setPlainText(observed_text)
        # A different selected task cannot receive edits from this dialog.
        values = session.meaning_text if same_task else {}
        if same_task:
            for name, editor in self.editors.items():
                if self._text_error is not None: continue
                if editor.toPlainText() == values[name]: continue
                blocked = editor.blockSignals(True)
                try: editor.setPlainText(values[name])
                finally: editor.blockSignals(blocked)
            self._rendered = values
        editable = same_task and session.status not in {"STOPPING", "STOPPED"}
        for editor in self.editors.values(): editor.setReadOnly(not editable)
        ready = editable and session.status == "READY" and session._pending is None and self._text_error is None
        self.propose_button.setEnabled(ready and session.created and not session.dirty
            and session.meaning_basis_current and not session.has_remote and not session.has_meaning_remote)
        reading = editable and session.status in {"READY", "RECOVERING"} and session._pending is None and session.created
        self.load_button.setEnabled(reading and self._text_error is None)
        self.adopt_button.setEnabled(reading and session.has_meaning_remote and self._text_error is None)
        recovery_idle = same_task and session.created and session._pending is None
        self.retain_recovery_button.setEnabled(recovery_idle and session.status == "READY")
        self.load_recovery_button.setEnabled(recovery_idle and session.status in {"READY", "RECOVERING"})
        self.discard_recovery_button.setEnabled(recovery_idle and self._recovery_active
            and session.status in {"READY", "RECOVERING"})
        self.status_label.setText(session.meaning_status if same_task else "Task selection changed; return to the selected task.")
        detail = self._error or ("Stored task changed; return to task and reload its current saved draft before recording a proposal."
            if same_task and session.created and not session.meaning_basis_current else session.detail)
        if self._recovery_error: detail += "\n" + self._recovery_error
        if same_task and self._recovery_active:
            detail += "\nEditor recovery: " + session.editor_recovery_status(self._task_id)
            recovery_error = session.editor_recovery_error(self._task_id)
            if recovery_error:
                detail += " (" + recovery_error + ")"
        self.detail_label.setText(detail)
        self._bind_accessibility(same_task)

    def _bind_accessibility(self, same_task):
        session = self._session
        if not same_task:
            reason = "A different task is selected; return to that task. Retained documents stay with this task."
        elif session.status in {"STOPPING", "STOPPED"}:
            reason = "The owned service is stopping or has stopped; retained documents remain inspectable."
        elif self._text_error is not None:
            reason = "Correct rejected field text first; its complete document remains under recovery custody."
        elif session._pending is not None:
            reason = "Wait for the bound current request to finish or use Stop."
        elif not session.created:
            reason = "Create a stored task before recording or loading an interpretation."
        elif not session.meaning_basis_current:
            reason = "Return to the task and load its current saved draft first."
        elif session.dirty:
            reason = "Save the task draft before recording a proposal for its current revision."
        else:
            reason = "The current task state does not admit this operation."
        actions = (
            (self.propose_button, "Record unaccepted interpretation proposal",
                "Request a revision-checked record of these interpretation fields. This does not accept the task or authorize work.", reason),
            (self.load_button, "Inspect stored interpretation proposal",
                "Query the actual stored proposal and its draft basis without replacing rejected documents.", reason),
            (self.adopt_button, "Use observed interpretation revision",
                "Explicitly select the observed stored revision while retaining your local interpretation text.",
                reason if not same_task or session.has_meaning_remote else "No different stored proposal revision is awaiting selection."),
            (self.stop_button, "Stop owned service",
                "Escape requests Stop immediately, before field validation. STOPPING does not mean resource retirement has been observed.", reason),
            (self.close_button, "Return to task with guarded edit disposition",
                "Return only after the existing edit-custody guard succeeds. Invalid retained text requires explicit disposition.", reason),
            (self.retain_recovery_button, "Retain complete interpretation recovery copy",
                "Request a durable recovery copy of the current complete documents. Completion requires its bound journal result.", reason),
            (self.load_recovery_button, "Load retained interpretation edits",
                "Query this task's retained recovery before explicit review and restoration.", reason),
            (self.discard_recovery_button, "Explicitly discard retained interpretation edits",
                "Request an authenticated revision-checked discarded state. Prior full text remains in history; window destruction is not consent.",
                reason if self._recovery_active else "No active interpretation recovery has been captured in this view."),
        )
        for widget, name, description, unavailable in actions:
            self.accessibility.describe_action(widget, name=name, description=description,
                                               unavailable_reason=unavailable)
        self.accessibility.bind_state(context_id=self._task_id, state=(
            ("Service", session.status),
            ("Task selection", "Captured task selected" if same_task else "Different task selected"),
            ("Interpretation", session.meaning_status if same_task else "Captured documents retained"),
            ("Editor validation", "Correction required" if self._text_error is not None else "Valid local input"),
            ("Editor recovery", session.editor_recovery_status(self._task_id)
                if same_task and self._recovery_active else "No active recovery in this view"),
        ))

    @property
    def return_authorized(self):
        """Dialog disposal consent only; never task acceptance or authority."""
        return self._return_authorized

    @property
    def has_rejected_edits(self): return self._text_error is not None

    def retain_after_exception(self):
        """Keep the real documents reachable; validation and task binding survive."""
        self._return_authorized = False
        self._recovery_error = ("This interpretation window could not finish. Its edits are still here. "
            "Correct invalid text and record a valid proposal, or deliberately discard it with Return to task.")
        self.setModal(False)
        self.poll_timer.start()
        self._refresh()
        self.show(); self.raise_(); self.activateWindow()

    def _can_return(self, result):
        if self._text_error is None and not self._recovery_active: return True
        if (self._text_error is None and self._session.task_id == self._task_id
                and self._session.editor_recovery_status(self._task_id) == "RETAINED"
                and self._session.meaning_proposal is not None and not self._session.meaning_dirty):
            # The current raw capture has a bound durable recovery, and the
            # corrected form has a separately recorded, unaccepted proposal.
            # Return transfers recovery to that owner without discarding it.
            return True
        if self._discard_requested:
            self._recovery_error = "Discard is awaiting a bound journal result; the full documents remain here."
            return False
        if QMessageBox.question(self, "Discard invalid interpretation edits?",
            "These invalid edits have not been retained in the task. Discard them and return?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return False
        try:
            self._begin_discard(return_result=result)
        except ContractError as error:
            self._recovery_error = error.code + ". Load the recovery to reconcile it before disposal."
            return False
        self._recovery_error = "Discard is awaiting a bound journal result; the full documents remain here."
        return False

    def closeEvent(self, event):
        self.done(QDialog.DialogCode.Rejected)
        if self._return_authorized: event.accept()
        else: event.ignore()

    def reject(self):
        self.done(QDialog.DialogCode.Rejected)

    def accept(self):
        self.done(QDialog.DialogCode.Accepted)

    def done(self, result):
        # Direct done/accept, reject, Return and window close share the same guard.
        # A cleanup failure does not confer consent to delete rejected documents.
        if not self._can_return(result): return
        try:
            self.poll_timer.stop()
            self._return_authorized = True
            super().done(result)
        except BaseException:
            self.retain_after_exception()
            raise
