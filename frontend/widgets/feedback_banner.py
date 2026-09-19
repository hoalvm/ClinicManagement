"""Inline feedback that keeps users in context instead of opening modal dialogs."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class FeedbackBanner(QFrame):
    """A compact error, success, or informational message."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("feedbackBanner")
        self.setProperty("severity", "info")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(10)

        self._indicator = QLabel("i")
        self._indicator.setObjectName("feedbackTitle")
        self._indicator.setFixedWidth(16)
        self._indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self._title = QLabel()
        self._title.setObjectName("feedbackTitle")
        self._message = QLabel()
        self._message.setObjectName("feedbackText")
        self._message.setWordWrap(True)
        text_layout.addWidget(self._title)
        text_layout.addWidget(self._message)

        layout.addWidget(self._indicator, 0)
        layout.addLayout(text_layout, 1)
        self.hide()

    def show_message(self, title: str, message: str, *, severity: str = "info") -> None:
        normalized = severity if severity in {"error", "success", "info"} else "info"
        self.setProperty("severity", normalized)
        self._indicator.setText({"error": "!", "success": "✓", "info": "i"}[normalized])
        self._title.setText(title)
        self._message.setText(message)
        self.setAccessibleName(f"{title}. {message}")
        self.style().unpolish(self)
        self.style().polish(self)
        self.show()

    def clear(self) -> None:
        self.hide()
        self._title.clear()
        self._message.clear()
