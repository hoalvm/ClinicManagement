"""Accessible combo box with a deterministic, high-DPI chevron."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QComboBox, QStyle, QStyleOptionComboBox, QWidget


class ChevronComboBox(QComboBox):
    """A combo box that paints its arrow with Qt primitives.

    Qt style sheets do not support CSS border triangles.  Drawing the chevron
    avoids the small grey square produced by the previous rule and remains
    crisp at fractional Windows display scaling.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("paintedChevron", True)

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
