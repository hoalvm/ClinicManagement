"""Accessible checkbox whose checked state remains visible under QSS."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QCheckBox, QStyle, QStyleOptionButton, QWidget


class SemanticCheckBox(QCheckBox):
    """Draw a deterministic check mark over the themed indicator."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("semanticCheck", True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)
        if self.checkState() is not Qt.CheckState.Checked:
            return

        option = QStyleOptionButton()
        self.initStyleOption(option)
        indicator = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator,
            option,
            self,
        )
        if indicator.isEmpty():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor("#FFFFFF"), max(1.8, indicator.width() / 9))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        left = indicator.left() + indicator.width() * 0.23
        middle_x = indicator.left() + indicator.width() * 0.43
        right = indicator.left() + indicator.width() * 0.78
        middle_y = indicator.top() + indicator.height() * 0.68
        painter.drawPolyline(
            [
                QPointF(left, indicator.top() + indicator.height() * 0.52),
                QPointF(middle_x, middle_y),
                QPointF(right, indicator.top() + indicator.height() * 0.32),
            ]
        )


__all__ = ["SemanticCheckBox"]
