"""Shared pagination controls for list screens."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QWidget

from frontend.core.i18n import get_i18n, t
from frontend.widgets.combo_box import ChevronComboBox


class PaginationWidget(QWidget):
    page_changed = Signal(int)
    page_requested = page_changed
    page_size_changed = Signal(int)

    COMPACT_BREAKPOINT = 620

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page = 1
        self._total_pages = 0
        self._total = 0
        self._compact = False
        self.setObjectName("pagination")
        self.setProperty("uiSurface", "transparent")

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self._layout.setHorizontalSpacing(8)
        self._layout.setVerticalSpacing(8)
        self._layout.setColumnStretch(1, 1)

        self._summary = QLabel()
        self._summary.setObjectName("mutedLabel")

        self._rows_label = QLabel()
        self._rows_label.setObjectName("mutedLabel")
        self._page_size = ChevronComboBox()
        self._page_size.addItems(["5", "10", "20", "50", "100"])
        self._page_size.setCurrentText("10")
        self._page_size.setMinimumWidth(72)
        self._page_size.setMaximumWidth(96)
        self._rows_label.setBuddy(self._page_size)

        self._previous = QPushButton()
        self._previous.setObjectName("secondaryButton")
        self._previous.setProperty("compact", True)
        self._previous.setCursor(Qt.PointingHandCursor)
        self._next = QPushButton()
        self._next.setObjectName("secondaryButton")
        self._next.setProperty("compact", True)
        self._next.setCursor(Qt.PointingHandCursor)

        self._place_controls(compact=False)

        self._previous.clicked.connect(self._go_previous)
        self._next.clicked.connect(self._go_next)
        self._page_size.currentTextChanged.connect(
            lambda value: self.page_size_changed.emit(int(value))
        )
        get_i18n().language_changed.connect(self.retranslate_ui)
        self.set_page(1, 0, 0)
        self.retranslate_ui()

    @property
    def is_compact(self) -> bool:
        return self._compact

    @property
    def page_size(self) -> int:
        return int(self._page_size.currentText())

    def set_page(self, page: int, total_pages: int, total: int) -> None:
        self._page = max(1, page)
        self._total_pages = max(0, total_pages)
        self._total = max(0, total)
        self._update_summary()
        self._previous.setEnabled(self._page > 1)
        self._next.setEnabled(self._total_pages > 0 and self._page < self._total_pages)

    def _update_summary(self) -> None:
        if self._total:
            first = (self._page - 1) * self.page_size + 1
            last = min(self._total, self._page * self.page_size)
            self._summary.setText(
                t(
                    "pagination_summary",
                    first=first,
                    last=last,
                    total=self._total,
                    page=self._page,
                    total_pages=max(1, self._total_pages),
                )
            )
        else:
            self._summary.setText(t("pagination_empty"))

    def retranslate_ui(self, _lang: str | None = None) -> None:
        """Update all labels and accessibility text after a language switch."""

        self._rows_label.setText(t("pagination_rows"))
        self._previous.setText(t("pagination_previous"))
        self._next.setText(t("pagination_next"))
        self._summary.setAccessibleName(t("pagination_a11y_summary"))
        self._page_size.setAccessibleName(t("pagination_a11y_rows"))
        self._previous.setAccessibleName(t("pagination_a11y_previous"))
        self._next.setAccessibleName(t("pagination_a11y_next"))
        self._update_summary()

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

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        compact = self.width() < self.COMPACT_BREAKPOINT
        if compact != self._compact:
            self._place_controls(compact=compact)

    def _place_controls(self, *, compact: bool) -> None:
        for widget in (
            self._summary,
            self._rows_label,
            self._page_size,
            self._previous,
            self._next,
        ):
            self._layout.removeWidget(widget)

        if compact:
            self._layout.addWidget(self._summary, 0, 0, 1, 4)
            self._layout.addWidget(self._rows_label, 1, 0)
            self._layout.addWidget(self._page_size, 1, 1, Qt.AlignmentFlag.AlignLeft)
            self._layout.addWidget(self._previous, 1, 2)
            self._layout.addWidget(self._next, 1, 3)
        else:
            self._layout.addWidget(self._summary, 0, 0)
            self._layout.addWidget(self._rows_label, 0, 2)
            self._layout.addWidget(self._page_size, 0, 3)
            self._layout.addWidget(self._previous, 0, 4)
            self._layout.addWidget(self._next, 0, 5)
        self._compact = compact
        self.setProperty("compact", compact)


# Compatibility alias
Pagination = PaginationWidget

