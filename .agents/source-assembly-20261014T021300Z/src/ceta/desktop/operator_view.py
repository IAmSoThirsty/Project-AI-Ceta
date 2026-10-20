"""Native development inspector using only an injected application session.

This is not the full task/approval UI or a qualified product. Session methods
must return promptly; the application owns asynchronous work, correlation,
per-view drafts and observed shutdown. Qt timing is not a native driver bound.
"""
import re

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QPlainTextEdit,
                              QPushButton, QVBoxLayout, QWidget)

from ceta.contracts.wire import ContractError

OPERATIONS = ("kernel.prepare", "kernel.consume", "kernel.revoke",
              "kernel.resolve_consumption", "kernel.recover_permit", "kernel.recover_preparation")
_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,79}")


class OperatorView(QWidget):
    """Render actual session strings; no owner selection or authority writes."""

    def __init__(self, session):
        super().__init__()
        self._session = session
        self._view_error = None
        self._close_requested = False
        self._stop_requested = False
        self.setObjectName("development_operator")
        self.setAccessibleName("CETA development operator")
        self.setWindowTitle("CETA Development Operator")
        self.resize(840, 680)

        layout = QVBoxLayout(self)
        scope = QLabel("Development record inspector. Positive authority remains unavailable. "
                       "This is a model-free development surface, not the full task interface.")
        scope.setObjectName("development_scope")
        scope.setAccessibleName("Development scope and authority limits")
        scope.setWordWrap(True)
        scope.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(scope)

        draft_label = QLabel("&Record draft")
        self.draft_editor = QPlainTextEdit()
        self.draft_editor.setObjectName("record_draft")
        self.draft_editor.setAccessibleName("Record draft")
        self.draft_editor.setTabChangesFocus(True)
        self.draft_editor.setAccessibleDescription("Editable original record JSON; submission does not approve an effect.")
        self.draft_editor.setPlaceholderText("Paste a bounded canonical record for inspection or a kernel request.")
        self.draft_editor.setPlainText(session.draft)
        draft_label.setBuddy(self.draft_editor)
        layout.addWidget(draft_label)
        layout.addWidget(self.draft_editor, 2)

        actions = QHBoxLayout()
        operation_label = QLabel("&Operation")
        self.operation_picker = QComboBox()
        self.operation_picker.setObjectName("operation_picker")
        self.operation_picker.setAccessibleName("Kernel operation")
        self.operation_picker.addItems(OPERATIONS)
        operation_label.setBuddy(self.operation_picker)
        self.submit_button = QPushButton("&Submit")
        self.submit_button.setObjectName("submit_request")
        self.submit_button.setAccessibleName("Submit kernel request")
        self.stop_button = QPushButton("S&top (Esc)")
        self.stop_button.setObjectName("stop_service")
        self.stop_button.setAccessibleName("Stop owned service")
        self.stop_button.setAccessibleDescription("Requests owned-service shutdown; displayed STOPPED requires observed termination.")
        for widget in (operation_label, self.operation_picker, self.submit_button, self.stop_button):
            actions.addWidget(widget)
        layout.addLayout(actions)

        self.status_label = QLabel()
        self.status_label.setObjectName("operator_status")
        self.status_label.setAccessibleName("Observed service status")
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.detail_label = QLabel()
        self.detail_label.setObjectName("operator_detail")
        self.detail_label.setAccessibleName("Service detail and uncertainty")
        self.detail_label.setTextFormat(Qt.TextFormat.PlainText)
        self.detail_label.setWordWrap(True)
        self.detail_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status_label)
        layout.addWidget(self.detail_label)

        result_label = QLabel("Result / recovery observation")
        self.result_editor = QPlainTextEdit()
        self.result_editor.setObjectName("operation_result")
        self.result_editor.setAccessibleName("Kernel result or recovery observation")
        self.result_editor.setAccessibleDescription("Read-only actual response; a returned denial can require reconciliation after commit.")
        self.result_editor.setReadOnly(True)
        self.result_editor.setTabChangesFocus(True)
        result_label.setBuddy(self.result_editor)
        layout.addWidget(result_label)
        layout.addWidget(self.result_editor, 2)

        QWidget.setTabOrder(self.draft_editor, self.operation_picker)
        QWidget.setTabOrder(self.operation_picker, self.submit_button)
        QWidget.setTabOrder(self.submit_button, self.stop_button)
        QWidget.setTabOrder(self.stop_button, self.result_editor)
        self.draft_editor.textChanged.connect(self._draft_changed)
        self.submit_button.clicked.connect(self._submit)
        self.stop_button.clicked.connect(self._request_stop)
        self.stop_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.stop_shortcut.setObjectName("stop_shortcut")
        self.stop_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.stop_shortcut.setAutoRepeat(False)
        self.stop_shortcut.activated.connect(self._request_stop)
        self.poll_timer = QTimer(self)
        self.poll_timer.setObjectName("session_poll")
        self.poll_timer.setInterval(50)
        self.poll_timer.timeout.connect(self._poll)
        self._refresh()
        self.poll_timer.start()

    def _error(self, error):
        code = error.code
        self._view_error = code if type(code) is str and _CODE.fullmatch(code) else "UI_CONTRACT_ERROR"

    def _sync_draft(self):
        try:
            self._session.set_draft(self.draft_editor.toPlainText())
            return True
        except ContractError as error:
            self._error(error)
            return False

    def _draft_changed(self):
        self._sync_draft()
        self._refresh()

    def _submit(self):
        if not self.submit_button.isEnabled():
            return
        if self._sync_draft():
            self._view_error = None
            try:
                self._session.submit(self.operation_picker.currentText())
            except ContractError as error:
                self._error(error)
        self._refresh()

    def _request_stop(self):
        # Request stop before any draft processing; an invalid draft must not
        # prevent the independent shutdown request.
        stop_error = None
        if self._session.status != "STOPPED":
            try:
                self._session.stop()
                self._stop_requested = True
            except ContractError as error:
                stop_error = error
        saved = self._sync_draft()
        if stop_error is not None:
            self._error(stop_error)
        elif saved:
            self._view_error = None
        self._refresh()

    def _poll(self):
        try:
            self._session.poll()
        except ContractError as error:
            self._error(error)
            self._refresh()
            return
        self._refresh()
        if self._close_requested and self._session.status == "STOPPED":
            self.close()

    def _refresh(self):
        # Poll never loads the draft back from a callback. Only an explicit
        # selection loads the session's preserved draft for that selected view.
        self.status_label.setText("Service status: " + self._session.status)
        detail = self._session.detail
        if self._view_error is not None:
            detail += "\nRequest error: " + self._view_error + ". Draft preserved; inspect state before retrying."
        if self._close_requested and self._session.status != "STOPPED":
            detail += "\nWaiting for observed owned-service STOPPED before closing."
        self.detail_label.setText(detail)
        result = self._session.result_text
        if self.result_editor.toPlainText() != result:
            self.result_editor.setPlainText(result)
        self.submit_button.setEnabled(not self._close_requested
            and self._session.status in {"READY", "RECOVERING", "DEGRADED"})
        # Stop stays reachable during ACTIVE/STOPPING and draft/transport errors.
        self.stop_button.setEnabled(True)

    def select_view(self, view_ref):
        """Explicit view changes delegate correlation and per-view draft ownership."""
        if self._close_requested or not self._sync_draft():
            self._refresh()
            return
        try:
            self._session.select_view(view_ref)
        except ContractError as error:
            self._error(error)
            self._refresh()
            return
        self._view_error = None
        previous = self.draft_editor.blockSignals(True)
        try:
            self.draft_editor.setPlainText(self._session.draft)
        finally:
            self.draft_editor.blockSignals(previous)
        self._refresh()

    def closeEvent(self, event):
        self._close_requested = True
        if self._session.status != "STOPPED":
            event.ignore()
            if not self._stop_requested:
                self._request_stop()
            else:
                self._refresh()
            return
        if not self._sync_draft():
            event.ignore()
            self._refresh()
            return
        self.poll_timer.stop()
        event.accept()


def create_operator_window(session) -> QWidget:
    """Composition supplies the application session and the Qt application."""
    return OperatorView(session)
