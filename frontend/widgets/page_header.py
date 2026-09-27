"""Consistent title, subtitle, back navigation, and page actions."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from frontend.core.i18n import get_i18n, t


class PageHeader(QFrame):
    """Reusable page heading that keeps navigation and actions aligned."""

    back_requested = Signal()
    action_clicked = Signal()
    compact_changed = Signal(bool)

    COMPACT_BREAKPOINT = 760

    def __init__(
        self,
        title: str,
        subtitle: str | None = None,
        parent: QWidget | None = None,
        *,
        show_back: bool = False,
        back_text: str | None = None,
        action_label: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("pageHeader")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._compact = False

        self._root = QGridLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setHorizontalSpacing(14)
        self._root.setVerticalSpacing(10)
        self._root.setColumnStretch(1, 1)

        self._uses_default_back_text = back_text is None
        resolved_back_text = back_text or t("btn_back")
        self.back_button = QPushButton(resolved_back_text)
        self.back_button.setObjectName("secondaryButton")
        self.back_button.setProperty("compact", True)
        self.back_button.setAccessibleName(resolved_back_text)
        self.back_button.clicked.connect(self.back_requested)
        self.back_button.setVisible(show_back)
        self._root.addWidget(self.back_button, 0, 0, Qt.AlignmentFlag.AlignVCenter)

        self.text_layout = QVBoxLayout()
        self.text_layout.setContentsMargins(0, 0, 0, 0)
        self.text_layout.setSpacing(4)
        self.text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setAccessibleName(title)
        self.text_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle or "")
        self.subtitle_label.setObjectName("mutedLabel")
        self.subtitle_label.setProperty("uiRole", "pageSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))
        self.text_layout.addWidget(self.subtitle_label)
        self._root.addLayout(self.text_layout, 0, 1)

        self.actions_layout = QHBoxLayout()
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(8)
        self.actions_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._root.addLayout(self.actions_layout, 0, 2)

        self.action_button: QPushButton | None = None
        if action_label:
            self.action_button = QPushButton(action_label)
            self.action_button.setObjectName("primaryButton")
            self.action_button.setAccessibleName(action_label)
            self.action_button.clicked.connect(self.action_clicked.emit)
            self.add_action(self.action_button)
        get_i18n().language_changed.connect(self._retranslate_ui)

    @property
    def is_compact(self) -> bool:
        return self._compact

    @property
    def title(self) -> str:
        return self.title_label.text()

    @property
    def subtitle(self) -> str:
        return self.subtitle_label.text()

    def set_title(self, title: str) -> None:
        """Update the visible page title."""

        self.title_label.setText(title)
        self.title_label.setAccessibleName(title)

    def set_subtitle(self, subtitle: str | None) -> None:
        """Update the supporting copy and hide it when empty."""

        text = subtitle or ""
        self.subtitle_label.setText(text)
        self.subtitle_label.setVisible(bool(text))

    def set_back_visible(self, visible: bool) -> None:
        self.back_button.setVisible(visible)

    def set_back_enabled(self, enabled: bool) -> None:
        self.back_button.setEnabled(enabled)

    def add_action(self, widget: QWidget) -> None:
        """Append a page-level action to the right side of the header."""

        if not widget.accessibleName() and hasattr(widget, "text"):
            widget.setAccessibleName(str(widget.text()))
        self.actions_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
        self._reflow()

    def insert_action(self, index: int, widget: QWidget) -> None:
        """Insert a page-level action at a stable visual position."""

        if not widget.accessibleName() and hasattr(widget, "text"):
            widget.setAccessibleName(str(widget.text()))
        self.actions_layout.insertWidget(index, widget, 0, Qt.AlignmentFlag.AlignVCenter)
        self._reflow()

    def remove_action(self, widget: QWidget) -> None:
        """Remove an action without deleting it, allowing later reuse."""

        self.actions_layout.removeWidget(widget)

    def _retranslate_ui(self, _lang: str | None = None) -> None:
        if self._uses_default_back_text:
            label = t("btn_back")
            self.back_button.setText(label)
            self.back_button.setAccessibleName(label)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self, *, force: bool = False) -> None:
        compact = self.width() < self.COMPACT_BREAKPOINT
        if not force and compact == self._compact:
            return

        self._root.removeItem(self.text_layout)
        self._root.removeItem(self.actions_layout)
        if compact:
            self._root.addLayout(self.text_layout, 0, 1, 1, 2)
            self._root.addLayout(
                self.actions_layout,
                1,
                0,
                1,
                3,
                Qt.AlignmentFlag.AlignRight,
            )
        else:
            self._root.addLayout(self.text_layout, 0, 1)
            self._root.addLayout(
                self.actions_layout,
                0,
                2,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            )
        changed = compact != self._compact
        self._compact = compact
        self.setProperty("compact", compact)
        if changed:
            self.compact_changed.emit(compact)


__all__ = ["PageHeader"]
