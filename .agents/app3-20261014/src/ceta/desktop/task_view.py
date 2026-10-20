"""Native task creation and explicit durable draft custody over typed use cases."""
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

from ceta.contracts.wire import ContractError
from ceta.desktop.accessibility import AccessibleBindings
from shiboken6 import isValid


class TaskView(QWidget):
    def __init__(self, session):
        super().__init__()
        self._session, self._rendered, self._error = session, None, None
        self._text_error = None
        self._meaning_views, self._meaning_modal = {}, None
        self._local_rendered_task_id = None
        self._catalog_recovery_discovery_started = False
        self._catalog_recovery_list_requested = False
        self._editor_discovery_requested = set()
        self._close_requested, self._close_dirty_confirmed = False, False
        self.setWindowTitle("CETA Tasks")
        self.resize(920, 760)
        layout = QVBoxLayout(self)
        description = QLabel("Create a task, save its draft, reopen stored tasks, and inspect its interpretation separately.")
        description.setWordWrap(True); description.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(description)
        navigation = QHBoxLayout()
        self.task_picker = QComboBox(); self.task_picker.setAccessibleName("Stored task")
        self.new_button = QPushButton("&New task")
        self.list_button = QPushButton("&Refresh tasks")
        self.load_button = QPushButton("&Open stored task")
        self.reload_current_button = QPushButton("Reload &current task")
        self.reload_current_button.setToolTip("Query this task ID, including an uncertain creation not yet listed in the catalog.")
        for widget in (self.task_picker, self.list_button, self.load_button, self.reload_current_button): navigation.addWidget(widget)
        layout.addLayout(navigation)
        local_navigation = QHBoxLayout()
        self.local_task_picker = QComboBox(); self.local_task_picker.setAccessibleName("Retained local task drafts")
        self.local_select_button = QPushButton("Return to local &draft")
        for widget in (self.local_task_picker, self.local_select_button, self.new_button): local_navigation.addWidget(widget)
        layout.addLayout(local_navigation)
        meaning_recovery = QHBoxLayout()
        self.meaning_recovery_picker = QComboBox()
        self.meaning_recovery_picker.setAccessibleName("Retained interpretation drafts")
        self.meaning_recovery_button = QPushButton("Recover interpretation draft")
        self.meaning_recovery_button.clicked.connect(self._recover_meaning)
        for widget in (self.meaning_recovery_picker, self.meaning_recovery_button): meaning_recovery.addWidget(widget)
        layout.addLayout(meaning_recovery)
        title_label = QLabel("&Title")
        self.title_editor = QLineEdit(); self.title_editor.setAccessibleName("Task title")
        title_label.setBuddy(self.title_editor); layout.addWidget(title_label); layout.addWidget(self.title_editor)
        draft_label = QLabel("&Instruction / draft")
        self.draft_editor = QPlainTextEdit(); self.draft_editor.setAccessibleName("Task instruction and draft")
        self.draft_editor.setTabChangesFocus(True)
        draft_label.setBuddy(self.draft_editor); layout.addWidget(draft_label); layout.addWidget(self.draft_editor, 3)
        actions = QHBoxLayout()
        self.create_button = QPushButton("&Create task")
        self.save_button = QPushButton("&Save draft")
        self.meaning_button = QPushButton("&Interpretation")
        self.preparation_button = QPushButton("Request &preparation")
        self.rebase_button = QPushButton("Use observed state; keep local draft")
        self.rebase_button.setToolTip("Explicitly select the loaded current revision for a later save; keep your local text.")
        self.stop_button = QPushButton("S&top (Esc)")
        for widget in (self.create_button, self.save_button, self.meaning_button, self.preparation_button, self.rebase_button, self.stop_button): actions.addWidget(widget)
        layout.addLayout(actions)
        self.status_label = QLabel(); self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.status_label.setAccessibleName("Task persistence and service status")
        self.detail_label = QLabel(); self.detail_label.setTextFormat(Qt.TextFormat.PlainText); self.detail_label.setWordWrap(True)
        layout.addWidget(self.status_label); layout.addWidget(self.detail_label)
        original_label = QLabel("Original submitted instruction")
        self.original_editor = QPlainTextEdit(); self.original_editor.setReadOnly(True)
        self.original_editor.setAccessibleName("Immutable original task instruction")
        layout.addWidget(original_label); layout.addWidget(self.original_editor)
        self.result_editor = QPlainTextEdit(); self.result_editor.setReadOnly(True)
        self.result_editor.setAccessibleName("Actual task persistence or recovery response")
        layout.addWidget(self.result_editor)
        self.title_editor.textChanged.connect(self._edited)
        self.draft_editor.textChanged.connect(self._edited)
        self.new_button.clicked.connect(lambda: self._action(self._session.new_task))
        self.local_select_button.clicked.connect(lambda: self._action(lambda: self._session.select_task(self.local_task_picker.currentText())))
        self.list_button.clicked.connect(lambda: self._action(self._session.list_tasks))
        self.load_button.clicked.connect(lambda: self._action(lambda: self._session.load(self.task_picker.currentText())))
        self.reload_current_button.clicked.connect(lambda: self._action(lambda: self._session.load(self._session.task_id)))
        self.create_button.clicked.connect(lambda: self._action(self._session.create))
        self.save_button.clicked.connect(lambda: self._action(self._session.save))
        self.meaning_button.clicked.connect(self._meaning)
        self.preparation_button.clicked.connect(self._preparation)
        self.rebase_button.clicked.connect(lambda: self._action(self._session.adopt_current_revision))
        self.stop_button.clicked.connect(self._stop)
        self.stop_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.stop_shortcut.setAutoRepeat(False); self.stop_shortcut.activated.connect(self._stop)
        self.accessibility = AccessibleBindings(self, self.status_label, name="CETA tasks")
        self.setAccessibleName("CETA task drafts and recovery")
        self.detail_label.setAccessibleName("Task blockers and recovery detail")
        self.title_editor.setAccessibleDescription("Task title. The stored title changes only after a successful task command.")
        self.draft_editor.setAccessibleDescription("Editable task draft. Save explicitly to request persistence; edits do not approve work.")
        self.original_editor.setAccessibleDescription("Read-only original submitted instruction. Tab moves to the next control.")
        self.result_editor.setAccessibleDescription("Read-only actual task response. Uncertainty remains until the owned service reconciles it.")
        self.accessibility.set_focus_order((self.task_picker, self.list_button, self.load_button,
            self.reload_current_button, self.local_task_picker, self.local_select_button,
            self.new_button, self.meaning_recovery_picker, self.meaning_recovery_button,
            self.title_editor, self.draft_editor, self.create_button, self.save_button,
            self.meaning_button, self.preparation_button, self.rebase_button,
            self.stop_button, self.status_label, self.detail_label,
            self.original_editor, self.result_editor))
        self.poll_timer = QTimer(self); self.poll_timer.setInterval(50); self.poll_timer.timeout.connect(self._poll)
        self._refresh(); self.poll_timer.start()

    def _edited(self):
        try:
            self._session.set_title(self.title_editor.text())
            self._session.set_draft(self.draft_editor.toPlainText())
            self._error = self._text_error = None
        except ContractError as error: self._error = self._text_error = error.code
        self._refresh()

    def _action(self, action):
        if self._close_requested or self._text_error is not None: return
        try: action(); self._error = None
        except ContractError as error: self._error = error.code
        self._refresh()

    def _stop(self):
        # No persistence or draft validation precedes the Stop request.
        try: self._session.stop()
        except ContractError as error: self._error = error.code
        self._refresh()

    def _meaning(self):
        if self._close_requested or self._text_error is not None: return
        existing = self._meaning_views.get(self._session.task_id)
        if existing is not None and isValid(existing):
            existing.retain_after_exception(); self._refresh(); return
        from ceta.desktop.meaning_view import MeaningView
        view = MeaningView(self._session, self)
        self._meaning_views[view._task_id] = view
        view.finished.connect(lambda _result: self._finish_meaning(view))
        view.destroyed.connect(lambda _object=None: self._editor_destroyed(view))
        if view._task_id in self._session.editor_recovery_task_ids:
            view.recover_local_documents()
        self._meaning_modal = view
        failed = False
        try:
            view.exec()
        except Exception:
            failed = True
        except BaseException:
            failed = True
            raise
        finally:
            self._meaning_modal = None
            if failed or not view.return_authorized: self._retain_meaning(view)
            else: self._finish_meaning(view)
            self._refresh()

    def _retain_meaning(self, view):
        # Ownership precedes any recovery UI work. No rejected widget value is
        # substituted into the session or another task's editor.
        if not isValid(view):
            self._error = "MEANING_EDITOR_RECOVERY_AVAILABLE"
            return
        self._meaning_views[view._task_id] = view
        self._error = "MEANING_EDITOR_RETAINED"
        view.retain_after_exception()

    def _editor_destroyed(self, view):
        # Native deletion is only a lifetime observation. The session retains
        # its exact capture, pending request and durable recovery observation.
        if self._meaning_views.get(view._task_id) is view:
            del self._meaning_views[view._task_id]
        if view._task_id in self._session.editor_recovery_task_ids:
            self._error = "MEANING_EDITOR_RECOVERY_AVAILABLE"

    def _finish_meaning(self, view):
        # The modal callback may still inspect the dialog after Return. Dispose
        # only after exec returns, or after a later modeless, guarded Return.
        if view is self._meaning_modal or not isValid(view) or not view.return_authorized: return
        try:
            view.poll_timer.stop()
            view.deleteLater()
        except Exception:
            self._retain_meaning(view)
        else:
            if self._meaning_views.get(view._task_id) is view:
                del self._meaning_views[view._task_id]
            if not self._meaning_views and self._error == "MEANING_EDITOR_RETAINED": self._error = None
        self._refresh()

    def _recover_meaning(self):
        task_id = self.meaning_recovery_picker.currentText()
        if not task_id:
            return
        view = self._meaning_views.get(task_id)
        # A rejected raw task document also has custody. Keep it visible until
        # repaired, rather than navigating away and replacing its widget text.
        if task_id != self._session.task_id and self._text_error is None:
            try: self._session.select_task(task_id)
            except ContractError as error: self._error = error.code
        if self._session.task_id == task_id and not self._session.created:
            try:
                if self._session._pending is None:
                    self._session.load(task_id)
                    self._error = "MEANING_RECOVERY_LOADING_TASK"
            except ContractError as error:
                self._error = error.code
            self._refresh()
            return
        if view is None or not isValid(view):
            if task_id != self._session.task_id:
                self._error = "MEANING_RECOVERY_TASK_SELECTION_REQUIRED"
                return
            from ceta.desktop.meaning_view import MeaningView
            view = MeaningView(self._session, self)
            self._meaning_views[task_id] = view
            view.finished.connect(lambda _result: self._finish_meaning(view))
            view.destroyed.connect(lambda _object=None: self._editor_destroyed(view))
            view.recover_local_documents()
        view.retain_after_exception()
        self._refresh()

    def _preparation(self):
        if self._close_requested or self._text_error is not None: return
        from ceta.desktop.preparation_view import PreparationView
        view = PreparationView(self._session, self)
        try:
            view.exec()
        finally:
            view.poll_timer.stop()
            view.deleteLater()
            self._refresh()

    def _poll(self):
        try: self._session.poll()
        except ContractError as error: self._error = error.code
        # A fresh normal task view first observes the catalog, then issues
        # metadata-only editor recovery reads. It never privately reads raw
        # chunks or overwrites task/meaning state during discovery.
        # Optional metadata discovery yields to actual compiler custody,
        # unconfirmed drafts/recovery, and an explicit remote revision choice.
        # A background read must not reserve their shared service channel.
        if (not self._close_requested and self._session.status == "READY"
                and self._session._pending is None and not self._session.context_busy
                and not self._session.has_unconfirmed and not self._session.has_remote):
            try:
                if not self._catalog_recovery_discovery_started:
                    self._catalog_recovery_discovery_started = True
                    # A freshly opened session may already hold the selected
                    # task because normal startup loaded it before TaskView
                    # was constructed.  That observed catalog is sufficient
                    # to begin public metadata discovery on the next poll;
                    # otherwise first obtain the catalog through list_tasks.
                    self._catalog_recovery_list_requested = True
                    if not self._session.task_ids:
                        self._session.list_tasks()
                elif self._catalog_recovery_list_requested:
                    unknown = tuple(task_id for task_id in self._session.task_ids
                                    if task_id not in self._editor_discovery_requested)
                    if unknown:
                        self._editor_discovery_requested.update(unknown)
                        self._session.discover_editor_recoveries(unknown)
            except ContractError as error:
                self._error = error.code
        self._refresh()
        if self._close_requested and self._session.status == "STOPPED": self.close()

    def _refresh(self):
        session = self._session
        frozen = self._close_requested or session.status in {"STOPPING", "STOPPED"}
        self.meaning_button.setEnabled(not self._close_requested and self._text_error is None and session.created
            and session.status not in {"STOPPING", "STOPPED"})
        # Inspection stays available when composition has no compiler; the
        # dialog explains the missing owner and disables preparation actions.
        self.preparation_button.setEnabled(not self._close_requested and self._text_error is None
            and session.created and session.status not in {"STOPPING", "STOPPED"})
        rendered = (session.task_id, session.title, session.draft)
        if rendered != self._rendered:
            for widget, value in ((self.title_editor, session.title), (self.draft_editor, session.draft)):
                # Never overwrite widget text after rejected edits in this view.
                if self._text_error is not None and self._rendered is not None and self._rendered[0] == session.task_id: continue
                if (widget.text() if isinstance(widget, QLineEdit) else widget.toPlainText()) == value: continue
                blocked = widget.blockSignals(True)
                try:
                    if isinstance(widget, QLineEdit): widget.setText(value)
                    else: widget.setPlainText(value)
                finally: widget.blockSignals(blocked)
            self._rendered = rendered
        current_ids = tuple(self.task_picker.itemText(i) for i in range(self.task_picker.count()))
        if current_ids != session.task_ids:
            selected = self.task_picker.currentText(); self.task_picker.clear(); self.task_picker.addItems(session.task_ids)
            position = self.task_picker.findText(selected)
            if position >= 0: self.task_picker.setCurrentIndex(position)
        local_ids = tuple(self.local_task_picker.itemText(i) for i in range(self.local_task_picker.count()))
        if local_ids != session.local_task_ids:
            local_selected = self.local_task_picker.currentText()
            self.local_task_picker.clear(); self.local_task_picker.addItems(session.local_task_ids)
            position = self.local_task_picker.findText(local_selected)
            if position >= 0: self.local_task_picker.setCurrentIndex(position)
        if self._local_rendered_task_id != session.task_id:
            position = self.local_task_picker.findText(session.task_id)
            if position >= 0: self.local_task_picker.setCurrentIndex(position)
            self._local_rendered_task_id = session.task_id
        retained_ids = tuple(dict.fromkeys((*self._meaning_views, *session.editor_recovery_task_ids)))
        recovery_ids = tuple(self.meaning_recovery_picker.itemText(i) for i in range(self.meaning_recovery_picker.count()))
        if recovery_ids != retained_ids:
            selected = self.meaning_recovery_picker.currentText()
            self.meaning_recovery_picker.clear(); self.meaning_recovery_picker.addItems(retained_ids)
            position = self.meaning_recovery_picker.findText(selected)
            if position >= 0: self.meaning_recovery_picker.setCurrentIndex(position)
        self.meaning_recovery_button.setEnabled(bool(retained_ids))
        self.status_label.setText("Task " + session.task_id + " | " + session.persistence + " | Service " + session.status)
        detail = session.detail + ("\nRequest error: " + self._error + ". Editor text retained." if self._error else "")
        self.detail_label.setText(detail)
        if self.original_editor.toPlainText() != session.original_instruction: self.original_editor.setPlainText(session.original_instruction)
        if self.result_editor.toPlainText() != session.result_text: self.result_editor.setPlainText(session.result_text)
        can_write = not self._close_requested and session.status == "READY"
        can_read = not self._close_requested and session.status in {"READY", "RECOVERING"}
        self.create_button.setEnabled(can_write and not session.created and not session.has_remote and self._text_error is None)
        self.save_button.setEnabled(can_write and session.created and not session.has_remote and self._text_error is None)
        self.list_button.setEnabled(can_read and self._text_error is None)
        self.load_button.setEnabled(can_read and bool(session.task_ids) and self._text_error is None)
        self.reload_current_button.setEnabled(can_read and self._text_error is None)
        self.new_button.setEnabled(not frozen and self._text_error is None)
        self.local_select_button.setEnabled(not frozen and bool(session.local_task_ids) and self._text_error is None)
        self.rebase_button.setEnabled(can_read and session.has_remote and self._text_error is None)
        self.stop_button.setEnabled(True)
        self.title_editor.setReadOnly(frozen)
        self.draft_editor.setReadOnly(frozen)
        for view in tuple(self._meaning_views.values()):
            if isValid(view): view._refresh()
        self._bind_accessibility()

    def _bind_accessibility(self):
        session = self._session
        if self._close_requested:
            reason = "This view is closing; Stop and recovery remain available."
        elif session.status in {"STOPPING", "STOPPED"}:
            reason = "The owned service is stopping or has stopped."
        elif self._text_error is not None:
            reason = "Correct the rejected editor text first; its exact local text is retained."
        elif session.status not in {"READY", "RECOVERING"}:
            reason = "Wait for the current owned request to finish or use Stop."
        else:
            reason = "The current task state does not admit this operation."
        describe = self.accessibility.describe_action
        actions = (
            (self.task_picker, "Stored task", "Select an observed stored task; Open stored task requests its current state.", reason),
            (self.list_button, "Refresh stored tasks", "Query the authenticated owner's stored task catalog.", reason),
            (self.load_button, "Open stored task", "Load the selected task. Unsubmitted local drafts remain separately retained.",
                reason if session.task_ids else "No stored task is listed; refresh the task catalog."),
            (self.reload_current_button, "Reload current task", "Query this task's current stored revision, including uncertain creation.", reason),
            (self.local_task_picker, "Retained local task drafts", "Select a locally retained task draft without accepting it.", reason),
            (self.local_select_button, "Return to local draft", "Show the selected retained local draft.",
                reason if session.local_task_ids else "No retained local task draft is available."),
            (self.new_button, "New task draft", "Start a new unsubmitted task draft; this does not store or approve it.", reason),
            (self.meaning_recovery_picker, "Retained interpretation drafts", "Select the task whose interpretation edits remain under recovery custody.", reason),
            (self.meaning_recovery_button, "Recover interpretation draft", "Reopen retained interpretation documents for explicit review and disposition.",
                "No retained interpretation document is available."),
            (self.create_button, "Create stored task", "Request durable creation of the current task draft; no work is approved.",
                "This task is already stored; use Save draft." if session.created else reason),
            (self.save_button, "Save task draft", "Request a revision-checked save of this draft, preserving the original instruction.",
                "Create a stored task first." if not session.created else
                "Choose the observed stored revision before saving local edits." if session.has_remote else reason),
            (self.meaning_button, "Inspect task interpretation", "Inspect, record or recover an unaccepted interpretation separately from the original task.",
                "Create a stored task first." if not session.created else reason),
            (self.preparation_button, "Inspect request preparation", "Inspect compiler availability and prepare a saved task when its actual prerequisites are present. Preview does not dispatch.",
                "Create a stored task first." if not session.created else reason),
            (self.rebase_button, "Use observed task revision", "Select the observed current stored revision while keeping your local draft text.",
                "No different stored task revision is awaiting selection." if not session.has_remote else reason),
            (self.stop_button, "Stop owned service", "Escape requests Stop immediately. STOPPING is a request; STOPPED requires observed resource retirement.", reason),
        )
        for widget, name, description, unavailable in actions:
            describe(widget, name=name, description=description, unavailable_reason=unavailable)
        self.accessibility.bind_state(context_id=session.task_id, state=(
            ("Service", session.status), ("Task persistence", session.persistence),
            ("Editor validation", "Correction required" if self._text_error is not None else "Valid local input"),
            ("Recovery", "Retained interpretation edits available" if self.meaning_recovery_picker.count() else "No retained interpretation listed"),
        ))

    def closeEvent(self, event):
        event.ignore()
        for view in tuple(self._meaning_views.values()):
            # Rejected edits live only in these real documents. Neither a
            # clean session cache nor an observed Stop permits their disposal.
            if not isValid(view): continue
            view.reject()
            if not view.return_authorized:
                view.show(); view.raise_(); view.activateWindow()
                return
        if not self._close_dirty_confirmed and (self._session.has_unconfirmed or self._text_error):
            choice = QMessageBox.question(self, "Unsaved task drafts", "One or more task drafts have unsaved or uncertain changes. Close this view anyway? Stored versions remain available.",
                QMessageBox.StandardButton.Close | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
            if choice != QMessageBox.StandardButton.Close:
                event.ignore(); return
            self._close_dirty_confirmed = True
        self._close_requested = True
        if self._session.status != "STOPPED": event.ignore(); self._stop(); return
        self.poll_timer.stop(); self.accessibility.close(); event.accept()
