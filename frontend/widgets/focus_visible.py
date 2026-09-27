"""Keyboard-only focus rings without disabling native focus or accessibility."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QFocusEvent
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QWidget,
)

_MANAGER_OBJECT_NAME = "clinicCareFocusVisibleManager"


def _refresh_style(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def set_focus_visible(widget: QWidget, visible: bool) -> None:
    """Set the styling hook on an entire control and refresh its Qt style."""

    resolved = bool(visible)
    if widget.property("focusVisible") is resolved:
        return
    widget.setProperty("focusVisible", resolved)
    _refresh_style(widget)


class FocusVisibleManager(QObject):
    """Application event filter implementing the common ``:focus-visible`` heuristic.

    Tab, Backtab, shortcuts, and keyboard navigation enable the outer focus
    ring.  Pointer interaction suppresses it.  Focus policy and event delivery
    are never changed, so keyboard operation and screen-reader semantics stay
    native to Qt.
    """

    _KEYBOARD_REASONS = {
        Qt.FocusReason.TabFocusReason,
        Qt.FocusReason.BacktabFocusReason,
        Qt.FocusReason.ShortcutFocusReason,
    }
    _NAVIGATION_KEYS = {
        Qt.Key.Key_Tab,
        Qt.Key.Key_Backtab,
        Qt.Key.Key_Left,
        Qt.Key.Key_Right,
        Qt.Key.Key_Up,
        Qt.Key.Key_Down,
        Qt.Key.Key_Space,
        Qt.Key.Key_Return,
        Qt.Key.Key_Enter,
    }
    _FOCUS_CONTROLS = (
        QAbstractButton,
        QAbstractItemView,
        QAbstractSpinBox,
        QComboBox,
        QLineEdit,
        QTextEdit,
    )

    def __init__(self, application: QApplication) -> None:
        super().__init__(application)
        self.setObjectName(_MANAGER_OBJECT_NAME)
        self._application = application
        self._keyboard_mode = False
        self._visible_owner: QWidget | None = None

    @property
    def keyboard_mode(self) -> bool:
        return self._keyboard_mode

    @property
    def visible_owner(self) -> QWidget | None:
        return self._visible_owner

    def uninstall(self) -> None:
        if self._visible_owner is not None:
            set_focus_visible(self._visible_owner, False)
            self._visible_owner = None
        self._application.removeEventFilter(self)
        self.deleteLater()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        event_type = event.type()

        if event_type == QEvent.Type.KeyPress and hasattr(event, "key"):
            if event.key() in self._NAVIGATION_KEYS:
                self._keyboard_mode = True
        elif event_type in {
            QEvent.Type.MouseButtonPress,
            QEvent.Type.TouchBegin,
            QEvent.Type.TabletPress,
        }:
            self._keyboard_mode = False
            self._clear_visible_owner()
        elif event_type == QEvent.Type.FocusIn:
            owner = self._focus_owner(watched)
            if owner is not None:
                reason = (
                    event.reason()
                    if isinstance(event, QFocusEvent)
                    else Qt.FocusReason.OtherFocusReason
                )
                if reason == Qt.FocusReason.MouseFocusReason:
                    self._keyboard_mode = False
                elif reason in self._KEYBOARD_REASONS:
                    self._keyboard_mode = True
                self._set_visible_owner(owner if self._keyboard_mode else None)
        elif event_type == QEvent.Type.FocusOut:
            owner = self._focus_owner(watched)
            if owner is not None and owner is self._visible_owner:
                self._clear_visible_owner()

        return False

    def _focus_owner(self, watched: QObject) -> QWidget | None:
        if not isinstance(watched, QWidget):
            return None

        candidate: QWidget | None = watched
        while candidate is not None:
            if bool(candidate.property("managedFocus")):
                return candidate
            candidate = candidate.parentWidget()

        if isinstance(watched, self._FOCUS_CONTROLS):
            return watched
        parent = watched.parentWidget()
        if isinstance(parent, QAbstractItemView):
            return parent
        return None

    def _set_visible_owner(self, owner: QWidget | None) -> None:
        if owner is self._visible_owner:
            return
        self._clear_visible_owner()
        if owner is not None:
            set_focus_visible(owner, True)
            self._visible_owner = owner

    def _clear_visible_owner(self) -> None:
        if self._visible_owner is None:
            return
        set_focus_visible(self._visible_owner, False)
        self._visible_owner = None


def install_focus_visible(
    application: QApplication | None = None,
) -> FocusVisibleManager:
    """Install one focus-visible manager on the current Qt application."""

    resolved_application = application or QApplication.instance()
    if not isinstance(resolved_application, QApplication):
        raise RuntimeError("A QApplication must exist before installing focus-visible")

    existing = resolved_application.findChild(FocusVisibleManager, _MANAGER_OBJECT_NAME)
    if existing is not None:
        return existing

    manager = FocusVisibleManager(resolved_application)
    resolved_application.installEventFilter(manager)
    return manager


__all__ = ["FocusVisibleManager", "install_focus_visible", "set_focus_visible"]
