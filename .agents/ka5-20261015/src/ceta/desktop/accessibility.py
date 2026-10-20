"""Bounded semantic accessibility over real Qt view state and controls.

This presentation helper never enables an action, reads an editor, changes
focus during polling, or interprets a label as authority. Qt supplies each real
widget's role and enabled/read-only state. Screen-reader delivery still needs
an actual Windows assistive client; an emitted Qt event is only a request.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QThread, QTimer, Qt
from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent
from PySide6.QtWidgets import QApplication, QLabel, QPlainTextEdit, QWidget
from shiboken6 import isValid


MAX_STATE_FIELDS = 12
MAX_STATE_TEXT = 160
MAX_ACTION_DESCRIPTION = 1024
MAX_FOCUS_WIDGETS = 64
URGENT_STATES = frozenset({"STOPPING", "RECOVERING", "UNCERTAIN", "STALE",
                           "FAILED", "INDETERMINATE"})


def _text(value: str, limit: int, *, empty: bool = False) -> str:
    if type(value) is not str or len(value) > limit or (not value and not empty):
        raise ValueError("ACCESSIBILITY_TEXT_INVALID")
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise ValueError("ACCESSIBILITY_TEXT_INVALID")
    try:
        value.encode("utf8", errors="strict")
    except UnicodeError as error:
        raise ValueError("ACCESSIBILITY_TEXT_INVALID") from error
    return value


class AccessibleBindings(QObject):
    """One native view's action descriptions, focus order and state deltas.

    Callers supply only public state labels, never draft, question, model,
    token or diagnostic buffers. One single-shot timer retains only the latest
    bounded state. Unchanged polls are silent; background/hidden windows cannot
    speak over the active task or modal dialog. No accessibility activation or
    application-wide factory/handler is installed.
    """

    def __init__(self, owner: QWidget, status_widget: QLabel, *, name: str,
                 interval_ms: int = 200):
        if not isinstance(owner, QWidget) or not isinstance(status_widget, QLabel):
            raise ValueError("ACCESSIBILITY_WIDGET_INVALID")
        if not isValid(owner) or not isValid(status_widget):
            raise ValueError("ACCESSIBILITY_WIDGET_DELETED")
        if status_widget is not owner and not owner.isAncestorOf(status_widget):
            raise ValueError("ACCESSIBILITY_FOREIGN_WIDGET")
        if type(interval_ms) is not int or not 50 <= interval_ms <= 1000:
            raise ValueError("ACCESSIBILITY_INTERVAL_INVALID")
        name = _text(name, 96)
        app = QApplication.instance()
        if app is None or owner.thread() != app.thread() or QThread.currentThread() != app.thread():
            raise RuntimeError("ACCESSIBILITY_GUI_THREAD_REQUIRED")
        super().__init__(owner)
        self._owner, self._status_widget, self._name = owner, status_widget, name
        self._closed = False
        self._context_id = None
        self._state = ()
        self._announced = None
        self._pending = None
        self._last_error = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.announce_delta)

    @property
    def last_error(self) -> str | None:
        """Sanitized presentation failure only, never a service-state verdict."""
        return self._last_error

    @property
    def observed_state(self) -> tuple[tuple[str, str], ...]:
        return self._state

    def _gui_thread(self) -> None:
        if QThread.currentThread() != self.thread():
            raise RuntimeError("ACCESSIBILITY_GUI_THREAD_REQUIRED")

    def _widget(self, widget: QWidget) -> QWidget:
        self._gui_thread()
        if not isinstance(widget, QWidget) or not isValid(widget):
            raise ValueError("ACCESSIBILITY_WIDGET_INVALID")
        if widget is not self._owner and not self._owner.isAncestorOf(widget):
            raise ValueError("ACCESSIBILITY_FOREIGN_WIDGET")
        return widget

    def describe_action(self, widget: QWidget, *, name: str, description: str,
                        unavailable_reason: str | None = None) -> None:
        """Describe the control's actual enabled state without changing it."""
        widget = self._widget(widget)
        name = _text(name, 96)
        description = _text(description, MAX_ACTION_DESCRIPTION)
        if unavailable_reason is not None:
            unavailable_reason = _text(unavailable_reason, 512)
        if not widget.isEnabled():
            if unavailable_reason is None:
                raise ValueError("ACCESSIBILITY_DISABLED_REASON_REQUIRED")
            description += " Unavailable: " + unavailable_reason
        if len(description) > MAX_ACTION_DESCRIPTION:
            raise ValueError("ACCESSIBILITY_DESCRIPTION_OVERSIZE")
        if widget.accessibleName() != name:
            widget.setAccessibleName(name)
        if widget.accessibleDescription() != description:
            widget.setAccessibleDescription(description)

    def set_focus_order(self, widgets: tuple[QWidget, ...]) -> None:
        """Install explicit native tab order once, including document viewers."""
        if type(widgets) is not tuple or not 2 <= len(widgets) <= MAX_FOCUS_WIDGETS:
            raise ValueError("ACCESSIBILITY_FOCUS_ORDER_INVALID")
        checked = tuple(self._widget(widget) for widget in widgets)
        if len({id(widget) for widget in checked}) != len(checked):
            raise ValueError("ACCESSIBILITY_FOCUS_ORDER_DUPLICATE")
        for widget in checked:
            if isinstance(widget, QPlainTextEdit):
                widget.setTabChangesFocus(True)
            elif isinstance(widget, QLabel):
                # Make public status/detail reachable without a mouse. Text
                # remains plain and complete; trust is not conveyed by color.
                widget.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByKeyboard |
                    Qt.TextInteractionFlag.TextSelectableByMouse)
                # Qt changes QLabel's focus policy while enabling selectable
                # text, so assert the keyboard-reachable policy afterward.
                widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        for first, second in zip(checked, checked[1:]):
            QWidget.setTabOrder(first, second)

    def _foreground(self) -> bool:
        if self._closed or not isValid(self._owner) or not isValid(self._status_widget):
            return False
        app = QApplication.instance()
        if app is None or not self._owner.isVisible() or not self._owner.isActiveWindow():
            return False
        modal = app.activeModalWidget()
        return modal is None or modal is self._owner or modal.isAncestorOf(self._owner)

    def bind_state(self, *, context_id: str,
                   state: tuple[tuple[str, str], ...]) -> None:
        """Capture caller-supplied public state; queue at most one latest delta."""
        self._gui_thread()
        context_id = _text(context_id, 256)
        if type(state) is not tuple or not 1 <= len(state) <= MAX_STATE_FIELDS:
            raise ValueError("ACCESSIBILITY_STATE_INVALID")
        checked = []
        for pair in state:
            if type(pair) is not tuple or len(pair) != 2:
                raise ValueError("ACCESSIBILITY_STATE_INVALID")
            checked.append((_text(pair[0], 64), _text(pair[1], MAX_STATE_TEXT)))
        state = tuple(checked)
        if len({key for key, _value in state}) != len(state):
            raise ValueError("ACCESSIBILITY_STATE_DUPLICATE")
        if self._closed:
            return
        if context_id != self._context_id:
            self._timer.stop()
            self._pending = self._announced = None
            self._context_id = context_id
        self._state = state
        if state == self._announced:
            self._pending = None
            self._timer.stop()
            return
        self._pending = (context_id, state)
        # Do not restart an active timer: rapid state changes cannot postpone
        # notification indefinitely, and they never create an event queue.
        if self._foreground() and not self._timer.isActive():
            self._timer.start()

    def announce_delta(self) -> bool:
        """Request one native notification of the latest foreground state.

        A True result means Qt accepted updateAccessibility, not that an
        assistive client received or read it. Polls retry a sanitized native
        failure only at the configured bounded interval.
        """
        self._gui_thread()
        pending = self._pending
        if pending is None or not self._foreground():
            return False
        context_id, state = pending
        if context_id != self._context_id or state != self._state:
            return False
        message = self._name + ". " + ". ".join(key + ": " + value for key, value in state)
        try:
            event = QAccessibleAnnouncementEvent(self._status_widget, message)
            event.setPoliteness(QAccessible.AnnouncementPoliteness.Assertive
                if any(value in URGENT_STATES for _key, value in state)
                else QAccessible.AnnouncementPoliteness.Polite)
            QAccessible.updateAccessibility(event)
        except Exception:
            # Accessibility failure cannot prevent an already requested Stop,
            # authorize an action, change drafts or suppress a primary fault.
            self._last_error = "ACCESSIBILITY_ANNOUNCEMENT_FAILED"
            return False
        self._announced, self._pending = state, None
        self._last_error = None
        return True

    def close(self) -> None:
        """Retire this presentation timer; resource custody stays with owners."""
        self._gui_thread()
        self._closed = True
        self._timer.stop()
        self._pending = None

