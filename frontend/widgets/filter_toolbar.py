"""Responsive list filtering with debounced search and immediate facets."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QGridLayout, QLineEdit, QPushButton, QSizePolicy, QWidget

from frontend.widgets.combo_box import ChevronComboBox

FilterOption = str | tuple[str, object]


class FilterToolbar(QWidget):
    """Reusable filter bar for list-first screens.

    Search input is emitted after a short pause, while combo-box facets are
    emitted immediately.  The clear action is only visible while at least one
    condition differs from its initial value.
    """

    search_changed = Signal(str)
    filter_changed = Signal(str, object)
    filters_changed = Signal(object)
    clear_requested = Signal()
    compact_changed = Signal(bool)

    COMPACT_BREAKPOINT = 720
    NARROW_BREAKPOINT = 480

    def __init__(
        self,
        search_placeholder: str = "Tìm kiếm…",
        parent: QWidget | None = None,
        *,
        debounce_ms: int = 350,
        clear_text: str = "Xóa bộ lọc",
        search_accessible_name: str = "Tìm kiếm",
    ) -> None:
        super().__init__(parent)
        if debounce_ms < 0:
            raise ValueError("debounce_ms cannot be negative")

        self.setObjectName("filterToolbar")
        self.setProperty("uiSurface", "card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._compact = False
        self._narrow = False
        self._filters: dict[str, ChevronComboBox] = {}
        self._default_indexes: dict[str, int] = {}

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setHorizontalSpacing(10)
        self._layout.setVerticalSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("filterSearchInput")
        self.search_input.setPlaceholderText(search_placeholder)
        self.search_input.setAccessibleName(search_accessible_name)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(180)

        self.clear_button = QPushButton(clear_text)
        self.clear_button.setObjectName("ghostButton")
        self.clear_button.setProperty("compact", True)
        self.clear_button.setAccessibleName(clear_text)
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.hide()

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(debounce_ms)

        self.search_input.textChanged.connect(self._on_search_edited)
        self._search_timer.timeout.connect(self._emit_search)
        self.clear_button.clicked.connect(self.clear)
        self._place_controls()

    @property
    def is_compact(self) -> bool:
        return self._compact

    @property
    def is_narrow(self) -> bool:
        return self._narrow

    @property
    def debounce_ms(self) -> int:
        return self._search_timer.interval()

    def set_debounce_ms(self, value: int) -> None:
        if value < 0:
            raise ValueError("debounce_ms cannot be negative")
        self._search_timer.setInterval(value)

    def add_filter(
        self,
        key: str,
        options: Iterable[FilterOption],
        *,
        accessible_name: str | None = None,
        default_index: int = 0,
    ) -> ChevronComboBox:
        """Create and register a semantic combo facet, returning the control."""

        if not key.strip():
            raise ValueError("filter key must not be blank")
        if key in self._filters:
            raise ValueError(f"filter key is already registered: {key}")

        combo = ChevronComboBox()
        combo.setObjectName("filterCombo")
        combo.setAccessibleName(accessible_name or key)
        uses_item_data = False
        for option in options:
            if isinstance(option, tuple):
                label, value = option
                combo.addItem(label, value)
                uses_item_data = True
            else:
                combo.addItem(option, option)
        combo.setProperty("filterUsesItemData", uses_item_data)
        if not 0 <= default_index < max(1, combo.count()):
            raise ValueError("default_index is outside the available options")
        if combo.count():
            combo.setCurrentIndex(default_index)
        return self.add_filter_combo(key, combo, default_index=default_index)

    def add_filter_combo(
        self,
        key: str,
        combo: ChevronComboBox,
        *,
        default_index: int | None = None,
    ) -> ChevronComboBox:
        """Register a preconfigured :class:`ChevronComboBox` facet."""

        if not key.strip():
            raise ValueError("filter key must not be blank")
        if key in self._filters:
            raise ValueError(f"filter key is already registered: {key}")
        if not isinstance(combo, ChevronComboBox):
            raise TypeError("FilterToolbar facets must use ChevronComboBox")

        resolved_default = combo.currentIndex() if default_index is None else default_index
        if combo.count() and not 0 <= resolved_default < combo.count():
            raise ValueError("default_index is outside the available options")

        combo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        combo.setMinimumWidth(max(152, combo.minimumWidth()))
        self._filters[key] = combo
        self._default_indexes[key] = resolved_default
        combo.currentIndexChanged.connect(
            lambda _index, filter_key=key: self._on_filter_changed(filter_key)
        )
        self._place_controls()
        self._update_clear_visibility()
        return combo

    def filter_combo(self, key: str) -> ChevronComboBox:
        return self._filters[key]

    def values(self) -> dict[str, object]:
        """Return current search and facet values for a list request."""

        values: dict[str, object] = {"search": self.search_input.text().strip()}
        values.update(
            {
                key: self._combo_value(combo)
                for key, combo in self._filters.items()
            }
        )
        return values

    def has_active_filters(self) -> bool:
        if self.search_input.text().strip():
            return True
        return any(
            combo.currentIndex() != self._default_indexes[key]
            for key, combo in self._filters.items()
        )

    def clear(self) -> None:
        """Restore defaults and emit one coherent, immediately applicable state."""

        self._search_timer.stop()
        search_blocker = QSignalBlocker(self.search_input)
        self.search_input.clear()
        combo_blockers = [QSignalBlocker(combo) for combo in self._filters.values()]
        for key, combo in self._filters.items():
            combo.setCurrentIndex(self._default_indexes[key])
        del combo_blockers
        del search_blocker

        self._update_clear_visibility()
        self.search_changed.emit("")
        for key in self._filters:
            self.filter_changed.emit(key, self.values()[key])
        self.filters_changed.emit(self.values())
        self.clear_requested.emit()

    def flush_search(self) -> None:
        """Apply a pending search immediately (useful before explicit refresh)."""

        if self._search_timer.isActive():
            self._search_timer.stop()
            self._emit_search()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._place_controls()

    def _on_search_edited(self, _text: str) -> None:
        self._update_clear_visibility()
        if self.debounce_ms == 0:
            self._emit_search()
        else:
            self._search_timer.start()

    def _emit_search(self) -> None:
        value = self.search_input.text().strip()
        self.search_changed.emit(value)
        self.filters_changed.emit(self.values())

    def _on_filter_changed(self, key: str) -> None:
        self._update_clear_visibility()
        value = self.values()[key]
        self.filter_changed.emit(key, value)
        self.filters_changed.emit(self.values())

    def _update_clear_visibility(self) -> None:
        self.clear_button.setVisible(self.has_active_filters())

    @staticmethod
    def _combo_value(combo: ChevronComboBox) -> object:
        # A conventional "All" option intentionally carries ``None`` while
        # later options have backend codes. Only fall back to display text for
        # combos whose entire model was created without item data.
        uses_item_data = bool(combo.property("filterUsesItemData")) or any(
            combo.itemData(index) is not None for index in range(combo.count())
        )
        return combo.currentData() if uses_item_data else combo.currentText()

    def _place_controls(self) -> None:
        controls: list[QWidget] = [self.search_input, *self._filters.values(), self.clear_button]
        for widget in controls:
            self._layout.removeWidget(widget)

        width = self.width()
        compact = width < self.COMPACT_BREAKPOINT
        narrow = width < self.NARROW_BREAKPOINT
        filter_count = len(self._filters)
        for column in range(filter_count + 2):
            self._layout.setColumnStretch(column, 0)

        if narrow:
            self._layout.addWidget(self.search_input, 0, 0)
            for row, combo in enumerate(self._filters.values(), start=1):
                self._layout.addWidget(combo, row, 0)
            self._layout.addWidget(
                self.clear_button, filter_count + 1, 0, Qt.AlignmentFlag.AlignLeft
            )
            self._layout.setColumnStretch(0, 1)
        elif compact:
            span = max(1, filter_count + 1)
            self._layout.addWidget(self.search_input, 0, 0, 1, span)
            for column, combo in enumerate(self._filters.values()):
                self._layout.addWidget(combo, 1, column)
            self._layout.addWidget(
                self.clear_button,
                1,
                filter_count,
                Qt.AlignmentFlag.AlignRight,
            )
            for column in range(span):
                self._layout.setColumnStretch(column, 1 if column < filter_count else 0)
        else:
            self._layout.addWidget(self.search_input, 0, 0)
            for column, combo in enumerate(self._filters.values(), start=1):
                self._layout.addWidget(combo, 0, column)
            self._layout.addWidget(
                self.clear_button,
                0,
                filter_count + 1,
                Qt.AlignmentFlag.AlignRight,
            )
            self._layout.setColumnStretch(0, 1)
            for column in range(1, filter_count + 2):
                self._layout.setColumnStretch(column, 0)

        changed = compact != self._compact
        self._compact = compact
        self._narrow = narrow
        self.setProperty("compact", compact)
        self.setProperty("narrow", narrow)
        if changed:
            self.compact_changed.emit(compact)


__all__ = ["FilterOption", "FilterToolbar"]
