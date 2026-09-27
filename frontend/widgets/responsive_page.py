"""Single-scroll page container with an observable compact breakpoint."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from frontend.ui.design_system import SurfaceRole, set_surface_role


class ResponsivePage(QScrollArea):
    """Own the sole vertical scroll region for a page's body content."""

    compact_changed = Signal(bool)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        compact_breakpoint: int = 900,
        margins: tuple[int, int, int, int] = (24, 24, 24, 24),
        spacing: int = 16,
    ) -> None:
        super().__init__(parent)
        if compact_breakpoint < 320:
            raise ValueError("compact_breakpoint must be at least 320 pixels")
        self._compact_breakpoint = compact_breakpoint
        self._is_compact = False

        self.setObjectName("responsivePage")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("responsivePageContent")
        set_surface_role(self.content_widget, SurfaceRole.TRANSPARENT)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(*margins)
        self.content_layout.setSpacing(spacing)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self.content_widget)

    @property
    def is_compact(self) -> bool:
        return self._is_compact

    @property
    def compact_breakpoint(self) -> int:
        return self._compact_breakpoint

    def set_compact_breakpoint(self, width: int) -> None:
        if width < 320:
            raise ValueError("compact_breakpoint must be at least 320 pixels")
        self._compact_breakpoint = width
        self._update_compact_state()

    def add_widget(
        self,
        widget: QWidget,
        stretch: int = 0,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag(0),
    ) -> None:
        self.content_layout.addWidget(widget, stretch, alignment)

    def add_stretch(self, stretch: int = 1) -> None:
        self.content_layout.addStretch(stretch)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_compact_state()

    def _update_compact_state(self) -> None:
        compact = self.viewport().width() < self._compact_breakpoint
        if compact == self._is_compact:
            return
        self._is_compact = compact
        self.setProperty("compact", compact)
        self.content_widget.setProperty("compact", compact)
        self.compact_changed.emit(compact)


__all__ = ["ResponsivePage"]
