"""Dashboard metric card with a compact visual cue and keyboard activation."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from frontend.ui.icons import line_icon


class StatCard(QFrame):
    clicked = Signal()

    def __init__(
        self,
        title: str,
        *,
        icon_name: str | None = None,
        icon_text: str = "•",
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

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 17, 18, 17)
        layout.setSpacing(14)

        icon_frame = QFrame()
        icon_frame.setObjectName("statIcon")
        icon_frame.setFixedSize(44, 44)
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon = QLabel(icon_text)
        icon.setObjectName("statIconText")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        if icon_name:
            colors = {
                "blue": "#0369A1",
                "violet": "#6D28D9",
                "amber": "#B45309",
                "teal": "#0F766E",
            }
            icon.setText("")
            icon.setPixmap(
                line_icon(icon_name, colors.get(tone, "#0F766E"), size=22).pixmap(QSize(22, 22))
            )
        icon_layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        self._value = QLabel("—")
        self._value.setObjectName("statValue")
        label = QLabel(title)
        label.setObjectName("statTitle")
        text_layout.addWidget(self._value)
        text_layout.addWidget(label)

        layout.addWidget(icon_frame)
        layout.addLayout(text_layout, 1)

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
