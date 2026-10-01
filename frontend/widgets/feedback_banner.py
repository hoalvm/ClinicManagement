"""Inline feedback that keeps users in context instead of opening modal dialogs."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from frontend.ui.design_system import FeedbackSeverity

# Default auto-dismiss delays (milliseconds).
_TIMEOUT_MS: dict[FeedbackSeverity, int] = {
    FeedbackSeverity.SUCCESS: 2000,
    FeedbackSeverity.INFO: 2500,
    FeedbackSeverity.WARNING: 5000,
    FeedbackSeverity.ERROR: 5000,
}


class FeedbackBanner(QFrame):
    """A compact error, success, or informational message.

    - ``show_message`` replaces any existing banner and restarts the timer.
    - A manual × button lets users dismiss immediately.
    - Pass ``timeout_ms=0`` to disable auto-dismiss.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("feedbackBanner")
        self.setProperty("severity", FeedbackSeverity.INFO.value)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.clear)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(10)

        self._indicator = QLabel()
        self._indicator.setObjectName("feedbackTitle")
        self._indicator.hide()

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self._title = QLabel()
        self._title.setObjectName("feedbackTitle")
        self._title.setWordWrap(True)
        self._title.setMinimumHeight(18)
        self._message = QLabel()
        self._message.setObjectName("feedbackText")
        self._message.setWordWrap(True)
        self._message.setMinimumHeight(18)
        text_layout.addWidget(self._title)
        text_layout.addWidget(self._message)

        layout.addLayout(text_layout, 1)

        self._close_btn = QPushButton("×")
        self._close_btn.setObjectName("ghostButton")
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setToolTip("Đóng thông báo")
        self._close_btn.setAccessibleName("Đóng thông báo")
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.clear)
        layout.addWidget(self._close_btn, 0, Qt.AlignmentFlag.AlignTop)

        self.setMinimumHeight(63)
        self.hide()

    @property
    def severity(self) -> FeedbackSeverity:
        return FeedbackSeverity.coerce(str(self.property("severity")))

    @property
    def title(self) -> str:
        return self._title.text()

    @property
    def message(self) -> str:
        return self._message.text()

    def show_message(
        self,
        title: str,
        message: str,
        *,
        severity: FeedbackSeverity | str = FeedbackSeverity.INFO,
        timeout_ms: int | None = None,
    ) -> None:
        normalized = FeedbackSeverity.coerce(severity)
        self.setProperty("severity", normalized.value)
        self._title.setText(title)
        self._message.setText(message)
        self.setAccessibleName(f"{title}. {message}")
        self.setAccessibleDescription(normalized.value)
        self.style().unpolish(self)
        self.style().polish(self)
        for label in (self._title, self._message):
            label.style().unpolish(label)
            label.style().polish(label)
        self.show()
        # Always stop the previous timer before resolving the new delay so a
        # rapid-fire sequence cannot let the old countdown expire mid-message.
        self._dismiss_timer.stop()
        resolved_timeout = (
            timeout_ms
            if timeout_ms is not None
            else _TIMEOUT_MS.get(normalized, 2500)
        )
        if resolved_timeout > 0:
            self._dismiss_timer.start(resolved_timeout)

    def clear(self) -> None:
        self._dismiss_timer.stop()
        self.hide()
        self._title.clear()
        self._message.clear()
        self.setAccessibleName("")
