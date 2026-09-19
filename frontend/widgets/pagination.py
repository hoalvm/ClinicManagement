"""Shared pagination controls for list screens."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget


class PaginationWidget(QWidget):
    page_changed = Signal(int)
    page_size_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page = 1
        self._total_pages = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()

        self._summary = QLabel("No results")
        self._summary.setObjectName("mutedLabel")
        self._previous = QPushButton("Previous")
        self._previous.setObjectName("secondaryButton")
        self._next = QPushButton("Next")
        self._next.setObjectName("secondaryButton")
        self._page_size = QComboBox()
        self._page_size.addItems(["5", "10", "20", "50", "100"])
        self._page_size.setCurrentText("10")
        self._page_size.setAccessibleName("Rows per page")

        layout.addWidget(self._summary)
        layout.addSpacing(12)
        layout.addWidget(self._previous)
        layout.addWidget(self._next)
        layout.addWidget(QLabel("Rows:"))
        layout.addWidget(self._page_size)

        self._previous.clicked.connect(self._go_previous)
        self._next.clicked.connect(self._go_next)
        self._page_size.currentTextChanged.connect(
            lambda value: self.page_size_changed.emit(int(value))
        )
        self.set_page(1, 0, 0)

    @property
    def page_size(self) -> int:
        return int(self._page_size.currentText())

    def set_page(self, page: int, total_pages: int, total: int) -> None:
        self._page = max(1, page)
        self._total_pages = max(0, total_pages)
        if total:
            self._summary.setText(
                f"Page {self._page} of {max(1, self._total_pages)} · {total} total"
            )
        else:
            self._summary.setText("No results")
        self._previous.setEnabled(self._page > 1)
        self._next.setEnabled(self._total_pages > 0 and self._page < self._total_pages)

    def set_controls_enabled(self, enabled: bool) -> None:
        self._page_size.setEnabled(enabled)
        self._previous.setEnabled(enabled and self._page > 1)
        self._next.setEnabled(enabled and self._total_pages > 0 and self._page < self._total_pages)

    def reset(self) -> None:
        self.set_page(1, 0, 0)

    def _go_previous(self) -> None:
        if self._page > 1:
            self.page_changed.emit(self._page - 1)

    def _go_next(self) -> None:
        if self._page < self._total_pages:
            self.page_changed.emit(self._page + 1)
