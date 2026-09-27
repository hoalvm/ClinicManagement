"""Dashboard metric card with a compact visual cue and keyboard activation."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

_TONE_COLORS = {
    "blue": "#0369A1",
    "violet": "#6D28D9",
    "amber": "#B45309",
    "teal": "#0F766E",
    "brand": "#0F766E",
    "warning": "#B45309",
    "info": "#0369A1",
    "success": "#15803D",
    "error": "#B91C1C",
}


class _AccentBar(QFrame):
    """Tiny custom-painted accent that needs no per-widget style sheet."""

    def __init__(self, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self.setObjectName("statAccent")
        self.setFixedSize(4, 44)

    def set_color(self, color: str) -> None:
        resolved = QColor(color)
        self._color = resolved if resolved.isValid() else QColor("#0F766E")
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802, ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        painter.drawRoundedRect(QRectF(self.rect()), 2, 2)


class StatCard(QFrame):
    clicked = Signal()

    def __init__(
        self,
        title: str,
        value: object = "—",
        *,
        icon_name: str | None = None,
        icon_text: str | None = None,
        tone: str = "teal",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self.setObjectName("statCard")
        self.setProperty("tone", tone)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setAccessibleName(f"{title}. Open related records")

        accent_color = _TONE_COLORS.get(tone, "#0F766E")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Clean vertical accent indicator
        self.accent_bar = _AccentBar(accent_color)
        layout.addWidget(self.accent_bar, 0, Qt.AlignmentFlag.AlignVCenter)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._value = QLabel(str(value) if value is not None else "—")
        self._value.setObjectName("statValue")
        self._title_label = QLabel(title)
        self._title_label.setObjectName("statTitle")
        self._title_label.setWordWrap(True)
        self._title_label.setToolTip(title)
        text_layout.addWidget(self._value)
        text_layout.addWidget(self._title_label)

        layout.addLayout(text_layout, 1)

    def set_title(self, title: str) -> None:
        self._title = title
        self._title_label.setText(title)
        self._title_label.setToolTip(title)
        self.setAccessibleName(f"{self._title}: {self._value.text()}. Open related records")

    def set_value(self, value: object) -> None:
        resolved = "—" if value is None else str(value)
        self._value.setText(resolved)
        self.setAccessibleName(f"{self._title}: {resolved}. Open related records")

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        self.accent_bar.set_color(_TONE_COLORS.get(tone, "#0F766E"))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        inside = self.rect().contains(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and inside:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space}:
            self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ModernStatCard(StatCard):
    """Compatibility wrapper matching ModernStatCard(title, value, accent_color)."""

    def __init__(self, title: str, value: object, accent_color: str = "#0F766E"):
        super().__init__(title, value, parent=None)
        self.accent_bar.set_color(accent_color)


