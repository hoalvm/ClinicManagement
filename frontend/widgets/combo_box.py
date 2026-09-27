"""Accessible combo box with a deterministic, high-DPI chevron."""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionComboBox,
    QStyleOptionViewItem,
    QWidget,
)


class _ComboItemDelegate(QStyledItemDelegate):
    """Retain selection while suppressing the native inner focus rectangle."""

    def initStyleOption(  # noqa: N802
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        super().initStyleOption(option, index)
        option.state &= ~QStyle.StateFlag.State_HasFocus


class ChevronComboBox(QComboBox):
    """A combo box that paints its arrow with Qt primitives.

    Qt style sheets do not support CSS border triangles.  Drawing the chevron
    avoids the small grey square produced by the previous rule and remains
    crisp at fractional Windows display scaling.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("paintedChevron", True)
        self.setProperty("managedFocus", True)
        self.view().setItemDelegate(_ComboItemDelegate(self.view()))

    def showPopup(self) -> None:  # noqa: N802
        """Open a popup wide enough for useful labels without leaving the screen."""

        metrics = self.view().fontMetrics()
        natural_width = self.width()
        for index in range(self.count()):
            natural_width = max(
                natural_width,
                metrics.horizontalAdvance(self.itemText(index)) + 48,
            )
        screen = QGuiApplication.screenAt(self.mapToGlobal(self.rect().center()))
        available_width = (
            screen.availableGeometry().width() - 48 if screen is not None else 960
        )
        self.view().setMinimumWidth(min(natural_width, available_width))
        super().showPopup()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)

        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        arrow_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox,
            option,
            QStyle.SubControl.SC_ComboBoxArrow,
            self,
        )
        center = arrow_rect.center()
        half_width = max(3.0, min(4.5, arrow_rect.width() / 6.0))
        half_height = max(2.0, half_width * 0.55)
        color = QColor("#64748B" if self.isEnabled() else "#94A3B8")

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, 1.7)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolyline(
            [
                QPointF(center.x() - half_width, center.y() - half_height),
                QPointF(center.x(), center.y() + half_height),
                QPointF(center.x() + half_width, center.y() - half_height),
            ]
        )


__all__ = ["ChevronComboBox"]
