"""Clean two-column structured key-value information card for patient records and invoices."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QWidget,
)

from frontend.widgets.status_badge import StatusBadge


class KeyValueCard(QFrame):
    """Reusable card displaying structured fieldLabel and fieldValue pairs."""

    def __init__(
        self,
        title: str,
        fields: list[tuple[str, str]],
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("infoCard")
        self._fields = fields
        self._value_widgets: dict[str, QLabel] = {}

        layout = QGridLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setHorizontalSpacing(24)
        layout.setVerticalSpacing(10)

        section_title = QLabel(title)
        section_title.setObjectName("sectionTitle")
        layout.addWidget(section_title, 0, 0, 1, 2)

        for row, (label, key) in enumerate(fields, start=1):
            lbl_widget = QLabel(label)
            lbl_widget.setObjectName("fieldLabel")
            lbl_widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

            val_widget: QLabel
            if key == "status":
                val_widget = StatusBadge()
                val_widget.setMaximumWidth(180)
            else:
                val_widget = QLabel("—")
                val_widget.setObjectName("fieldValue")
                val_widget.setWordWrap(True)
                val_widget.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                    | Qt.TextInteractionFlag.TextSelectableByKeyboard
                )

            val_widget.setAccessibleName(label)
            layout.addWidget(lbl_widget, row, 0, Qt.AlignmentFlag.AlignTop)
            layout.addWidget(val_widget, row, 1, Qt.AlignmentFlag.AlignTop)
            self._value_widgets[key] = val_widget

        layout.setColumnMinimumWidth(0, 140)
        layout.setColumnStretch(1, 1)

    def set_value(self, key: str, value: Any) -> None:
        widget = self._value_widgets.get(key)
        if not widget:
            return
        if isinstance(widget, StatusBadge):
            widget.set_status(value)
        else:
            text = str(value) if value is not None and value != "" else "—"
            widget.setText(text)

    def set_values(self, data: dict[str, Any]) -> None:
        for _, key in self._fields:
            if key in data:
                self.set_value(key, data[key])

    def clear(self) -> None:
        for _, key in self._fields:
            widget = self._value_widgets.get(key)
            if widget:
                if isinstance(widget, StatusBadge):
                    widget.set_status("")
                else:
                    widget.setText("—")
