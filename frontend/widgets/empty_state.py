"""Helpful empty-state panel with an optional recovery action."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from frontend.ui.icons import IconName, line_icon


class EmptyState(QFrame):
    """Display an icon, clear explanation, and an optional next action."""

    action_requested = Signal()

    def __init__(
        self,
        title: str,
        description: str | None = None,
        parent: QWidget | None = None,
        *,
        icon: IconName | str | QIcon | None = None,
        action_text: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("emptyState")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel()
        self.icon_label.setObjectName("emptyStateIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setAccessibleName("Empty state illustration")
        self.icon_label.setVisible(False)
        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("emptyStateTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.description_label = QLabel(description or "")
        self.description_label.setObjectName("emptyStateDescription")
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description_label.setWordWrap(True)
        self.description_label.setMaximumWidth(520)
        self.description_label.setVisible(bool(description))
        layout.addWidget(self.description_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.action_button = QPushButton(action_text or "")
        self.action_button.setObjectName("primaryButton")
        self.action_button.setProperty("uiRole", "emptyStateAction")
        self.action_button.setVisible(bool(action_text))
        self.action_button.setAccessibleName(action_text or "Empty state action")
        self.action_button.clicked.connect(self.action_requested)
        layout.addSpacing(6)
        layout.addWidget(self.action_button, 0, Qt.AlignmentFlag.AlignHCenter)

        self.set_icon(icon)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def set_description(self, description: str | None) -> None:
        text = description or ""
        self.description_label.setText(text)
        self.description_label.setVisible(bool(text))

    def set_icon(self, icon: IconName | str | QIcon | None) -> None:
        """Set either a shared line-icon name, a custom QIcon, or no icon."""

        if icon is None:
            self.icon_label.clear()
            self.icon_label.hide()
            return
        resolved = icon if isinstance(icon, QIcon) else line_icon(icon, "#0F766E", size=28)
        self.icon_label.setPixmap(resolved.pixmap(QSize(28, 28)))
        self.icon_label.show()

    def set_action(self, text: str | None) -> None:
        """Update or hide the optional action button."""

        label = text or ""
        self.action_button.setText(label)
        self.action_button.setAccessibleName(label or "Empty state action")
        self.action_button.setVisible(bool(label))

    def set_action_enabled(self, enabled: bool) -> None:
        self.action_button.setEnabled(enabled)


__all__ = ["EmptyState"]
