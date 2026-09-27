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

from frontend.core.i18n import t

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
        self.setObjectName("fieldWrapper")
        self.setProperty("uiSurface", "transparent")
        self.setProperty("required", required)
        self.control = control
        self.required = required
        self._label_text = label_text

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.label = QLabel()
        self.label.setObjectName("fieldLabel")
        self.label.setWordWrap(True)
        if hasattr(self.label, "setBuddy"):
            self.label.setBuddy(self.control)
        layout.addWidget(self.label)

        layout.addWidget(self.control)

        self.error_label = QLabel()
        self.error_label.setObjectName("errorText")
        self.error_label.setWordWrap(True)
        self.error_label.setAccessibleName(t("field_error_accessible", label=label_text))
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        self.control.setAccessibleName(self.control.accessibleName() or label_text)
        self.control.setProperty("hasError", False)
        self.set_label_text(label_text)

    def set_label_text(self, label_text: str) -> None:
        """Update a translated label without losing the required marker or buddy."""

        self._label_text = label_text
        self.label.setText(f"{label_text} *" if self.required else label_text)
        self.error_label.setAccessibleName(t("field_error_accessible", label=label_text))
        self.control.setAccessibleName(label_text)

    def set_error(self, message: str | None) -> None:
        if message:
            self.error_label.setText(message)
            self.error_label.setVisible(True)
            self.control.setProperty("hasError", True)
            self.control.setAccessibleDescription(message)
        else:
            self.clear_error()
            return
        self._refresh_control_style()

    def clear_error(self) -> None:
        self.error_label.clear()
        self.error_label.setVisible(False)
        self.control.setProperty("hasError", False)
        self.control.setAccessibleDescription("")
        self._refresh_control_style()

    def _refresh_control_style(self) -> None:
        style = self.control.style()
        style.unpolish(self.control)
        style.polish(self.control)
        self.control.update()

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
