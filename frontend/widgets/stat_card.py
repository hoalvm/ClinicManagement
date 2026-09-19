"""Dashboard statistic card."""

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class StatCard(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        self._value = QLabel("—")
        self._value.setObjectName("statValue")
        label = QLabel(title)
        label.setObjectName("statTitle")
        layout.addWidget(self._value)
        layout.addWidget(label)

    def set_value(self, value: object) -> None:
        self._value.setText(str(value))
