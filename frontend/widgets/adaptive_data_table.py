"""Responsive, read-only data table primitives."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from PySide6.QtCore import QModelIndex, QSize, Qt
from PySide6.QtGui import QResizeEvent, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QWidget,
)

from frontend.core.i18n import t
from frontend.ui.design_system import ColumnSpec
from frontend.widgets.status_badge import StatusBadgeDelegate, display_status

RAW_VALUE_ROLE = int(Qt.ItemDataRole.UserRole) + 1


def _display_text(value: object) -> str:
    if value is None or value == "":
        return "—"
    return str(value)


class _ColumnTextDelegate(QStyledItemDelegate):
    """Apply column-level wrapping, elision, and alignment."""

    def __init__(self, spec: ColumnSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._spec = spec

    def initStyleOption(  # noqa: N802
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        super().initStyleOption(option, index)
        option.displayAlignment = self._spec.alignment
        option.textElideMode = Qt.TextElideMode.ElideRight
        if self._spec.wrap:
            option.features |= QStyleOptionViewItem.ViewItemFeature.WrapText
        else:
            option.features &= ~QStyleOptionViewItem.ViewItemFeature.WrapText

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:  # noqa: N802
        result = super().sizeHint(option, index)
        if self._spec.wrap:
            result.setHeight(max(44, min(result.height(), 72)))
        else:
            result.setHeight(max(result.height(), 44))
        return result


def validate_column_specs(columns: Sequence[ColumnSpec]) -> tuple[ColumnSpec, ...]:
    """Return an immutable, validated column collection."""

    resolved = tuple(columns)
    if not resolved:
        raise ValueError("AdaptiveDataTable requires at least one column")
    if sum(column.stretch for column in resolved) > 1:
        raise ValueError("Only one ColumnSpec can use stretch=True")
    return resolved


def configure_table_view(table: QTableView, columns: Sequence[ColumnSpec]) -> None:
    """Apply shared read-only and accessibility-safe table behavior."""

    specs = validate_column_specs(columns)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSortingEnabled(False)
    table.setShowGrid(False)
    table.setWordWrap(any(column.wrap for column in specs))
    table.setTextElideMode(Qt.TextElideMode.ElideRight)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    table.setProperty("uiSurface", "card")
    if not table.accessibleDescription():
        table.setAccessibleDescription(t("a11y_read_only_table"))

    vertical_header = table.verticalHeader()
    vertical_header.setVisible(False)
    vertical_header.setDefaultSectionSize(44)
    vertical_header.setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
        if any(column.wrap for column in specs)
        else QHeaderView.ResizeMode.Fixed
    )

    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setMinimumSectionSize(min(column.minimum_width for column in specs))
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    for index, spec in enumerate(specs):
        if spec.status:
            table.setItemDelegateForColumn(
                index,
                StatusBadgeDelegate(table, status_role=RAW_VALUE_ROLE),
            )
        else:
            table.setItemDelegateForColumn(index, _ColumnTextDelegate(spec, table))
        if spec.stretch:
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.Stretch)
        else:
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(index, spec.preferred_width or spec.minimum_width)


class AdaptiveDataTable(QTableView):
    """A declarative table that protects important columns at narrow widths."""

    def __init__(
        self,
        columns: Sequence[ColumnSpec],
        parent: QWidget | None = None,
        *,
        accessible_name: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._column_specs = validate_column_specs(columns)
        self.data_model = QStandardItemModel(0, len(self._column_specs), self)
        self.setModel(self.data_model)
        if accessible_name:
            self.setAccessibleName(accessible_name)
        self.set_columns(self._column_specs)

    @property
    def column_specs(self) -> tuple[ColumnSpec, ...]:
        return self._column_specs

    def set_columns(self, columns: Sequence[ColumnSpec]) -> None:
        """Replace table metadata while preserving the model instance."""

        specs = validate_column_specs(columns)
        self._column_specs = specs
        self.data_model.setColumnCount(len(specs))
        self.data_model.setHorizontalHeaderLabels([spec.header for spec in specs])
        configure_table_view(self, specs)
        self.refresh_columns()

    def set_rows(self, rows: Iterable[Mapping[str, Any] | Sequence[Any]]) -> None:
        """Replace rows using mappings keyed by ``ColumnSpec.key`` or sequences."""

        self.setUpdatesEnabled(False)
        try:
            self.data_model.removeRows(0, self.data_model.rowCount())
            for row in rows:
                items: list[QStandardItem] = []
                for index, spec in enumerate(self._column_specs):
                    raw_value = self._row_value(row, index, spec)
                    if spec.status:
                        text = display_status(raw_value)
                    elif spec.formatter is not None:
                        text = spec.formatter(raw_value)
                    else:
                        text = _display_text(raw_value)
                    item = QStandardItem(str(text))
                    item.setEditable(False)
                    item.setTextAlignment(spec.alignment)
                    item.setData(raw_value, RAW_VALUE_ROLE)
                    item.setToolTip(str(text))
                    item.setAccessibleText(str(text))
                    items.append(item)
                self.data_model.appendRow(items)
        finally:
            self.setUpdatesEnabled(True)
        if any(spec.wrap for spec in self._column_specs):
            self.resizeRowsToContents()
        self.viewport().update()

    @staticmethod
    def _row_value(
        row: Mapping[str, Any] | Sequence[Any],
        index: int,
        spec: ColumnSpec,
    ) -> object:
        if isinstance(row, Mapping):
            return row.get(spec.key or spec.header)
        if isinstance(row, Sequence) and not isinstance(row, (str, bytes, bytearray)):
            return row[index] if index < len(row) else None
        raise TypeError("Rows must be mappings or non-string sequences")

    def refresh_columns(self) -> None:
        """Allocate width by importance, shrinking optional content first."""

        if not self._column_specs:
            return
        available = max(0, self.viewport().width())
        widths = [spec.preferred_width or spec.minimum_width for spec in self._column_specs]
        stretch_index = next(
            (index for index, spec in enumerate(self._column_specs) if spec.stretch),
            None,
        )
        fixed_indexes = [
            index for index in range(len(self._column_specs)) if index != stretch_index
        ]
        stretch_minimum = (
            self._column_specs[stretch_index].minimum_width if stretch_index is not None else 0
        )
        overflow = sum(widths[index] for index in fixed_indexes) + stretch_minimum - available
        if overflow > 0:
            for index in sorted(
                fixed_indexes,
                key=lambda item: self._column_specs[item].priority,
                reverse=True,
            ):
                minimum = self._column_specs[index].minimum_width
                reduction = min(max(0, widths[index] - minimum), overflow)
                widths[index] -= reduction
                overflow -= reduction
                if overflow <= 0:
                    break

        for index in fixed_indexes:
            self.setColumnWidth(index, widths[index])

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.refresh_columns()


__all__ = [
    "AdaptiveDataTable",
    "RAW_VALUE_ROLE",
    "configure_table_view",
    "validate_column_specs",
]
