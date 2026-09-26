"""Shared pagination controls for list screens."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget


class PaginationWidget(QWidget):
    page_changed = Signal(int)
    page_requested = page_changed
    page_size_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page = 1
        self._total_pages = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(8)

        self._summary = QLabel("Chưa có dữ liệu")
        self._summary.setObjectName("mutedLabel")
        self._summary.setAccessibleName("Pagination summary")

        rows_label = QLabel("Số dòng")
        rows_label.setObjectName("mutedLabel")
        self._page_size = QComboBox()
        self._page_size.addItems(["5", "10", "20", "50", "100"])
        self._page_size.setCurrentText("10")
        self._page_size.setAccessibleName("Rows per page")
        self._page_size.setFixedWidth(76)
        rows_label.setBuddy(self._page_size)

        self._previous = QPushButton("Trước")
        self._previous.setObjectName("secondaryButton")
        self._previous.setCursor(Qt.PointingHandCursor)
        self._previous.setAccessibleName("Previous page")
        self._next = QPushButton("Tiếp")
        self._next.setObjectName("secondaryButton")
        self._next.setCursor(Qt.PointingHandCursor)
        self._next.setAccessibleName("Next page")

        layout.addWidget(self._summary)
        layout.addStretch()
        layout.addWidget(rows_label)
        layout.addWidget(self._page_size)
        layout.addSpacing(8)
        layout.addWidget(self._previous)
        layout.addWidget(self._next)

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
            first = (self._page - 1) * self.page_size + 1
            last = min(total, self._page * self.page_size)
            self._summary.setText(
                f"Hiển thị {first}–{last} / {total}  ·  Trang {self._page}/{max(1, self._total_pages)}"
            )
        else:
            self._summary.setText("Không có dữ liệu")
        self._previous.setEnabled(self._page > 1)
        self._next.setEnabled(self._total_pages > 0 and self._page < self._total_pages)

    def update_state(self, page: int, total_pages: int, total: int) -> None:
        """Alias for set_page matching the reception view interface."""
        self.set_page(page, total_pages, total)

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


# Compatibility alias
Pagination = PaginationWidget

