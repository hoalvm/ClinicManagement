"""Inline feedback that keeps users in context instead of opening modal dialogs."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from frontend.ui.design_system import FeedbackSeverity


class FeedbackBanner(QFrame):
    """A compact error, success, or informational message."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("feedbackBanner")
        self.setProperty("severity", FeedbackSeverity.INFO.value)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(10)

        self._indicator = QLabel()
        self._indicator.setObjectName("feedbackTitle")
        self._indicator.hide()

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self._title = QLabel()
        self._title.setObjectName("feedbackTitle")
        self._title.setWordWrap(True)
        self._message = QLabel()
        self._message.setObjectName("feedbackText")
        self._message.setWordWrap(True)
        text_layout.addWidget(self._title)
        text_layout.addWidget(self._message)

        layout.addLayout(text_layout, 1)
        self.hide()

    @property
    def severity(self) -> FeedbackSeverity:
        return FeedbackSeverity.coerce(str(self.property("severity")))

    @property
    def title(self) -> str:
        return self._title.text()

    @property
    def message(self) -> str:
        return self._message.text()

    def show_message(
        self,
        title: str,
        message: str,
        *,
        severity: FeedbackSeverity | str = FeedbackSeverity.INFO,
    ) -> None:
        normalized = FeedbackSeverity.coerce(severity)
        self.setProperty("severity", normalized.value)
        self._title.setText(title)
        self._message.setText(message)
        self.setAccessibleName(f"{title}. {message}")
        self.setAccessibleDescription(normalized.value)
        self.style().unpolish(self)
        self.style().polish(self)
        for label in (self._title, self._message):
            label.style().unpolish(label)
            label.style().polish(label)
        self.show()

    def clear(self) -> None:
        self.hide()
        self._title.clear()
        self._message.clear()
        self.setAccessibleName("")
