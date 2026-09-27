"""Shared authenticated application shell for every ClinicCare role."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget


class ApplicationShell(QWidget):
    """Place one role-configured sidebar beside one expanding page workspace.

    Navigation labels and permissions remain role-owned, while this component
    guarantees the same surface hierarchy, zero-gap geometry, and responsive
    sidebar contract for Admin, Doctor, Staff, and Patient windows.
    """

    def __init__(
        self,
        sidebar: QWidget,
        workspace: QWidget,
        parent: QWidget | None = None,
        *,
        compact_handler: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("applicationShell")
        self.setProperty("uiSurface", "page")
        self.sidebar = sidebar
        self.workspace = workspace
        self._compact_handler = compact_handler

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(sidebar)
        layout.addWidget(workspace, 1)
        workspace.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    def set_sidebar_compact(self, compact: bool) -> None:
        """Apply compact mode when the configured sidebar supports it."""

        setter = self._compact_handler or getattr(self.sidebar, "set_compact", None)
        if callable(setter):
            setter(bool(compact))


__all__ = ["ApplicationShell"]
