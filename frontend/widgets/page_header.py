"""Consistent title, subtitle, back navigation, and page actions."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class PageHeader(QFrame):
    """Reusable page heading that keeps navigation and actions aligned."""

    back_requested = Signal()
    action_clicked = Signal()

    def __init__(
        self,
        title: str,
        subtitle: str | None = None,
        parent: QWidget | None = None,
        *,
        show_back: bool = False,
        back_text: str = "Back",
        action_label: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("pageHeader")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        self.back_button = QPushButton(back_text)
        self.back_button.setObjectName("secondaryButton")
        self.back_button.setProperty("compact", True)
        self.back_button.setAccessibleName(back_text or "Go back")
        self.back_button.clicked.connect(self.back_requested)
        self.back_button.setVisible(show_back)
        root.addWidget(self.back_button, 0, Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setAccessibleName("Page title")
        text_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle or "")
        self.subtitle_label.setObjectName("mutedLabel")
        self.subtitle_label.setProperty("uiRole", "pageSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))
        text_layout.addWidget(self.subtitle_label)
        root.addLayout(text_layout, 1)

        self.actions_layout = QHBoxLayout()
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(8)
        root.addLayout(self.actions_layout)

        self.action_button: QPushButton | None = None
        if action_label:
            self.action_button = QPushButton(action_label)
            self.action_button.setObjectName("primaryButton")
            self.action_button.clicked.connect(self.action_clicked.emit)
            self.add_action(self.action_button)

    @property
    def title(self) -> str:
        return self.title_label.text()

    @property
    def subtitle(self) -> str:
        return self.subtitle_label.text()

    def set_title(self, title: str) -> None:
        """Update the visible page title."""

        self.title_label.setText(title)

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

        self.actions_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)

    def insert_action(self, index: int, widget: QWidget) -> None:
        """Insert a page-level action at a stable visual position."""

        self.actions_layout.insertWidget(index, widget, 0, Qt.AlignmentFlag.AlignVCenter)

    def remove_action(self, widget: QWidget) -> None:
        """Remove an action without deleting it, allowing later reuse."""

        self.actions_layout.removeWidget(widget)


__all__ = ["PageHeader"]
