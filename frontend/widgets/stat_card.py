"""Dashboard metric card with a compact visual cue and keyboard activation."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


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
        self.setAccessibleName(f"{title}. Open related records")

        colors = {
            "blue": "#0369A1",
            "violet": "#6D28D9",
            "amber": "#B45309",
            "teal": "#0F766E",
            "brand": "#0F766E",
            "warning": "#B45309",
            "info": "#0369A1",
            "success": "#15803D",
        }
        accent_color = colors.get(tone, "#0F766E")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Clean vertical accent indicator
        accent_bar = QFrame()
        accent_bar.setFixedWidth(4)
        accent_bar.setStyleSheet(f"background-color: {accent_color}; border-radius: 2px;")
        layout.addWidget(accent_bar)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self._value = QLabel(str(value) if value is not None else "—")
        self._value.setObjectName("statValue")
        self._title_label = QLabel(title)
        self._title_label.setObjectName("statTitle")
        text_layout.addWidget(self._value)
        text_layout.addWidget(self._title_label)

        layout.addLayout(text_layout, 1)

    def set_title(self, title: str) -> None:
        self._title = title
        self._title_label.setText(title)
        self.setAccessibleName(f"{self._title}: {self._value.text()}. Open related records")

    def set_value(self, value: object) -> None:
        self._value.setText(str(value))
        self.setAccessibleName(f"{self._title}: {value}. Open related records")

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
        # Apply custom accent line color if provided
        for child in self.findChildren(QFrame):
            if child.width() == 4:
                child.setStyleSheet(f"background-color: {accent_color}; border-radius: 2px;")
                break

