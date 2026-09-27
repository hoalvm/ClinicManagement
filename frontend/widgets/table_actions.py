"""Shared row-action controls for adaptive data tables."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QHBoxLayout, QMenu, QPushButton, QToolButton, QWidget


@dataclass(frozen=True, slots=True)
class RowAction:
    """One accessible command exposed by a table row's overflow menu."""

    label: str
    callback: Callable[[], None]
    enabled: bool = True
    destructive: bool = False


class TableActionMenu(QToolButton):
    """Icon-only overflow menu without Qt's duplicate menu indicator."""

    def __init__(
        self,
        actions: Sequence[RowAction] = (),
        parent: QWidget | None = None,
        *,
        accessible_name: str = "Thao tác khác",
    ) -> None:
        super().__init__(parent)
        self.setObjectName("tableMoreButton")
        self.setProperty("hideMenuIndicator", True)
        self.setText("⋯")
        self.setToolTip(accessible_name)
        self.setAccessibleName(accessible_name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._menu = QMenu(self)
        self.setMenu(self._menu)
        self.set_actions(actions)

    def set_actions(self, actions: Sequence[RowAction]) -> None:
        self._menu.clear()
        for specification in actions:
            action = QAction(specification.label, self._menu)
            action.setEnabled(specification.enabled)
            action.setProperty("destructive", specification.destructive)
            # QAction accessibility is exposed through its text on PySide6;
            # ``setAccessibleText`` exists only on some Qt bindings/versions.
            if hasattr(action, "setAccessibleText"):
                action.setAccessibleText(specification.label)
            action.triggered.connect(
                lambda _checked=False, callback=specification.callback: callback()
            )
            self._menu.addAction(action)
        self.setEnabled(bool(actions))


def table_action_cell(
    primary: QPushButton | None = None,
    overflow: TableActionMenu | None = None,
    *,
    accessible_name: str,
) -> QWidget:
    """Compose the optional next-step action and one overflow trigger."""

    container = QWidget()
    container.setObjectName("tableCellWidget")
    container.setProperty("uiRole", "tableActionCell")
    container.setAccessibleName(accessible_name)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(4, 0, 4, 0)
    layout.setSpacing(6)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if primary is not None:
        layout.addWidget(primary)
    if overflow is not None:
        layout.addWidget(overflow)
    return container


__all__ = ["RowAction", "TableActionMenu", "table_action_cell"]
