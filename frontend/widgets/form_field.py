"""Standardized, accessible clinical form field (Label + Control + Inline Error)."""

from __future__ import annotations

from typing import TypeVar

from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

T = TypeVar("T", bound=QWidget)


class FormField(QWidget):
    """Reusable form input group keeping labels, inputs, and validation messages aligned."""

    def __init__(
        self,
        label_text: str,
        control: T,
        *,
        required: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.control = control

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        display_text = f"{label_text} *" if required else label_text
        self.label = QLabel(display_text)
        self.label.setObjectName("fieldLabel")
        if hasattr(self.label, "setBuddy"):
            self.label.setBuddy(self.control)
        layout.addWidget(self.label)

        layout.addWidget(self.control)

        self.error_label = QLabel()
        self.error_label.setObjectName("errorText")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

    def set_error(self, message: str | None) -> None:
        if message:
            self.error_label.setText(message)
            self.error_label.setVisible(True)
            self.control.setProperty("hasError", True)
        else:
            self.clear_error()
        self.control.style().unpolish(self.control)
        self.control.style().polish(self.control)

    def clear_error(self) -> None:
        self.error_label.clear()
        self.error_label.setVisible(False)
        self.control.setProperty("hasError", False)
        self.control.style().unpolish(self.control)
        self.control.style().polish(self.control)

    def text(self) -> str:
        if isinstance(self.control, QLineEdit):
            return self.control.text().strip()
        if isinstance(self.control, QTextEdit):
            return self.control.toPlainText().strip()
        if isinstance(self.control, QComboBox):
            return self.control.currentText().strip()
        return ""

    def set_text(self, text: str) -> None:
        if isinstance(self.control, (QLineEdit, QTextEdit)):
            self.control.setText(text)
        elif isinstance(self.control, QComboBox):
            self.control.setCurrentText(text)
