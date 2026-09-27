"""Content-aware, read-only data table primitives."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from PySide6.QtCore import QModelIndex, QSize, Qt
from PySide6.QtGui import (
    QFont,
    QFontMetrics,
    QPainter,
    QResizeEvent,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QWidget,
)

from frontend.core.i18n import t
from frontend.ui.design_system import CellValue, ColumnDisplayMode, ColumnSpec
from frontend.widgets.status_badge import StatusBadgeDelegate, display_status

RAW_VALUE_ROLE = int(Qt.ItemDataRole.UserRole) + 1
PRIMARY_TEXT_ROLE = RAW_VALUE_ROLE + 1
SECONDARY_TEXT_ROLE = RAW_VALUE_ROLE + 2


def _display_text(value: object) -> str:
    if value is None or value == "":
        return "—"
    return str(value)


def _coerce_cell_value(value: object) -> CellValue:
    if isinstance(value, CellValue):
        return value
    return CellValue(_display_text(value))


class _ColumnTextDelegate(QStyledItemDelegate):
    """Paint one- and two-line cells without Qt's inner focus rectangle."""

    _horizontal_padding = 10

    def __init__(self, spec: ColumnSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._spec = spec

    def initStyleOption(  # noqa: N802
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        super().initStyleOption(option, index)
        option.state &= ~QStyle.StateFlag.State_HasFocus
        option.displayAlignment = self._spec.alignment
        option.textElideMode = (
            Qt.TextElideMode.ElideNone
            if self._spec.display_mode is ColumnDisplayMode.FULL
            else Qt.TextElideMode.ElideRight
        )
        if self._spec.display_mode is ColumnDisplayMode.WRAP_2:
            option.features |= QStyleOptionViewItem.ViewItemFeature.WrapText
        else:
            option.features &= ~QStyleOptionViewItem.ViewItemFeature.WrapText

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        resolved = QStyleOptionViewItem(option)
        self.initStyleOption(resolved, index)
        secondary = str(index.data(SECONDARY_TEXT_ROLE) or "").strip()
        style = resolved.widget.style() if resolved.widget else None
        if not secondary:
            if style is not None:
                style.drawControl(
                    QStyle.ControlElement.CE_ItemViewItem,
                    resolved,
                    painter,
                    resolved.widget,
                )
            else:
                super().paint(painter, resolved, index)
            return

        primary = str(index.data(PRIMARY_TEXT_ROLE) or resolved.text)
        resolved.text = ""
        if style is not None:
            style.drawControl(
                QStyle.ControlElement.CE_ItemViewItem,
                resolved,
                painter,
                resolved.widget,
            )

        painter.save()
        content = resolved.rect.adjusted(
            self._horizontal_padding,
            5,
            -self._horizontal_padding,
            -5,
        )
        line_height = max(17, resolved.fontMetrics.lineSpacing())
        selected = bool(resolved.state & QStyle.StateFlag.State_Selected)
        palette_role = (
            resolved.palette.ColorRole.HighlightedText
            if selected
            else resolved.palette.ColorRole.Text
        )
        painter.setPen(resolved.palette.color(palette_role))
        primary_font = QFont(resolved.font)
        primary_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(primary_font)
        primary_metrics = painter.fontMetrics()
        preserve_text = (
            self._spec.preserve_full
            or self._spec.display_mode is ColumnDisplayMode.FULL
        )
        primary_text = (
            primary
            if preserve_text
            else primary_metrics.elidedText(
                primary,
                Qt.TextElideMode.ElideRight,
                content.width(),
            )
        )
        painter.drawText(
            content.x(),
            content.y(),
            content.width(),
            line_height,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            primary_text,
        )

        secondary_color = resolved.palette.color(palette_role)
        if not selected:
            secondary_color.setAlpha(178)
        painter.setPen(secondary_color)
        painter.setFont(resolved.font)
        secondary_text = (
            secondary
            if preserve_text
            else resolved.fontMetrics.elidedText(
                secondary,
                Qt.TextElideMode.ElideRight,
                content.width(),
            )
        )
        painter.drawText(
            content.x(),
            content.y() + line_height,
            content.width(),
            line_height,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            secondary_text,
        )
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:  # noqa: N802
        result = super().sizeHint(option, index)
        has_secondary = bool(str(index.data(SECONDARY_TEXT_ROLE) or "").strip())
        if has_secondary or self._spec.display_mode is ColumnDisplayMode.WRAP_2:
            # A table row is deliberately capped at two balanced lines; long
            # content remains available through tooltip/accessibility text.
            result.setHeight(60)
        else:
            result.setHeight(48)
        return result


def validate_column_specs(columns: Sequence[ColumnSpec]) -> tuple[ColumnSpec, ...]:
    """Return an immutable, validated column collection."""

    resolved = tuple(columns)
    if not resolved:
        raise ValueError("AdaptiveDataTable requires at least one column")
    return resolved


def configure_table_view(table: QTableView, columns: Sequence[ColumnSpec]) -> None:
    """Apply shared read-only, focus-safe table behavior."""

    specs = validate_column_specs(columns)
    wraps = any(
        column.display_mode is ColumnDisplayMode.WRAP_2 or column.line_limit == 2
        for column in specs
    )
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSortingEnabled(False)
    table.setShowGrid(False)
    table.setWordWrap(wraps)
    table.setTextElideMode(Qt.TextElideMode.ElideRight)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    table.setProperty("uiSurface", "card")
    table.setProperty("managedFocus", True)
    if not table.accessibleDescription():
        table.setAccessibleDescription(t("a11y_read_only_table"))

    vertical_header = table.verticalHeader()
    vertical_header.setVisible(False)
    vertical_header.setDefaultSectionSize(60 if wraps else 48)
    vertical_header.setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
        if wraps
        else QHeaderView.ResizeMode.Fixed
    )

    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setMinimumSectionSize(min(column.minimum_width for column in specs))
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    for index, spec in enumerate(specs):
        header.setSectionResizeMode(index, QHeaderView.ResizeMode.Fixed)
        if spec.status:
            table.setItemDelegateForColumn(
                index,
                StatusBadgeDelegate(table, status_role=RAW_VALUE_ROLE),
            )
        else:
            table.setItemDelegateForColumn(index, _ColumnTextDelegate(spec, table))
        table.setColumnWidth(index, spec.preferred_width or spec.minimum_width)


class AdaptiveDataTable(QTableView):
    """Declarative table with bounded, content-aware column growth."""

    CONTENT_SAMPLE_LIMIT = 100
    DEFAULT_GROWTH_CAP = 420

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
                        cell = CellValue(display_status(raw_value))
                    elif spec.formatter is not None:
                        cell = _coerce_cell_value(spec.formatter(raw_value))
                    else:
                        cell = _coerce_cell_value(raw_value)
                    item = QStandardItem(cell.display_text)
                    item.setEditable(False)
                    item.setTextAlignment(spec.alignment)
                    item.setData(raw_value, RAW_VALUE_ROLE)
                    item.setData(cell.primary, PRIMARY_TEXT_ROLE)
                    item.setData(cell.secondary or "", SECONDARY_TEXT_ROLE)
                    item.setToolTip(cell.full_text)
                    item.setAccessibleText(cell.accessible_text or cell.full_text)
                    items.append(item)
                self.data_model.appendRow(items)
        finally:
            self.setUpdatesEnabled(True)
        if any(
            spec.display_mode is ColumnDisplayMode.WRAP_2 or spec.line_limit == 2
            for spec in self._column_specs
        ):
            self.resizeRowsToContents()
        self.refresh_columns()
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

    def _natural_width(self, column: int, spec: ColumnSpec) -> int:
        metrics = self.fontMetrics()
        primary_font = QFont(self.font())
        primary_font.setWeight(QFont.Weight.DemiBold)
        primary_metrics = QFontMetrics(primary_font)
        width = self.horizontalHeader().fontMetrics().horizontalAdvance(spec.header) + 28
        row_count = min(self.data_model.rowCount(), self.CONTENT_SAMPLE_LIMIT)
        for row in range(row_count):
            index = self.data_model.index(row, column)
            primary = str(index.data(PRIMARY_TEXT_ROLE) or index.data() or "")
            secondary = str(index.data(SECONDARY_TEXT_ROLE) or "")
            content_padding = 36 if spec.status else 28
            content_metrics = primary_metrics if secondary else metrics
            width = max(
                width,
                content_metrics.horizontalAdvance(primary) + content_padding,
            )
            if secondary:
                width = max(width, metrics.horizontalAdvance(secondary) + 28)
        return max(spec.minimum_width, width)

    def refresh_columns(self) -> None:
        """Allocate preferred widths, then shrink or grow within declared bounds."""

        if not self._column_specs:
            return
        # Leave a tiny rounding gutter: on Windows styles the header and
        # viewport can differ by 1–2 device-independent pixels at fractional
        # DPI, which otherwise creates a useless 1–2 px horizontal scrollbar.
        available = max(0, self.viewport().width() - 6)
        natural = [
            self._natural_width(index, spec)
            for index, spec in enumerate(self._column_specs)
        ]
        floors: list[int] = []
        caps: list[int] = []
        widths: list[int] = []

        for index, spec in enumerate(self._column_specs):
            floor = natural[index] if spec.preserve_full else spec.minimum_width
            preferred = spec.preferred_width or natural[index]
            if spec.preserve_full:
                preferred = max(preferred, natural[index])
            default_cap = (
                max(preferred, self.DEFAULT_GROWTH_CAP)
                if spec.grow_weight > 0
                else preferred
            )
            cap = spec.maximum_width or default_cap
            cap = max(cap, floor)
            floors.append(floor)
            caps.append(cap)
            widths.append(max(floor, min(preferred, cap)))

        overflow = sum(widths) - available
        if overflow > 0:
            for index in sorted(
                range(len(widths)),
                key=lambda item: self._column_specs[item].priority,
                reverse=True,
            ):
                reduction = min(max(0, widths[index] - floors[index]), overflow)
                widths[index] -= reduction
                overflow -= reduction
                if overflow <= 0:
                    break

        remaining = max(0, available - sum(widths))
        eligible = {
            index
            for index, spec in enumerate(self._column_specs)
            if spec.grow_weight > 0 and widths[index] < caps[index]
        }
        while remaining > 0 and eligible:
            total_weight = sum(self._column_specs[index].grow_weight for index in eligible)
            allocated = 0
            for index in tuple(eligible):
                weight = self._column_specs[index].grow_weight
                share = max(1, remaining * weight // max(1, total_weight))
                addition = min(share, caps[index] - widths[index], remaining - allocated)
                widths[index] += addition
                allocated += addition
                if widths[index] >= caps[index]:
                    eligible.discard(index)
                if allocated >= remaining:
                    break
            if allocated <= 0:
                break
            remaining -= allocated

        for index, width in enumerate(widths):
            self.setColumnWidth(index, width)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.refresh_columns()


__all__ = [
    "AdaptiveDataTable",
    "PRIMARY_TEXT_ROLE",
    "RAW_VALUE_ROLE",
    "SECONDARY_TEXT_ROLE",
    "configure_table_view",
    "validate_column_specs",
]
