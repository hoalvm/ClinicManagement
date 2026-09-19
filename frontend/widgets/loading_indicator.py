"""Reusable indeterminate loading indicator."""

from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget


class LoadingIndicator(QWidget):
    def __init__(self, text: str = "Loading…", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("loadingIndicator")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._label = QLabel(text)
        self._bar = QProgressBar()
        self._bar.setRange(0, 0)
        self._bar.setTextVisible(False)
        self._bar.setFixedWidth(110)
        layout.addWidget(self._bar)
        layout.addWidget(self._label)
        layout.addStretch()
        self.hide()

    def start(self, text: str | None = None) -> None:
        if text:
            self._label.setText(text)
        self.show()

    def stop(self) -> None:
        self.hide()
