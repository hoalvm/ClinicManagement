"""Typed design-system contracts shared by the PySide desktop client.

The desktop application still uses Qt style sheets for presentation, but the
values and semantic roles below give widgets a stable, testable vocabulary.
Role-specific screens should consume these contracts instead of adding local
style sheets or relying on translated display text for application state.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum, StrEnum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


@dataclass(frozen=True, slots=True)
class UiTokens:
    """Core visual tokens for the calm, high-contrast clinical interface."""

    page_background: str = "#F4F7FB"
    surface: str = "#FFFFFF"
    surface_muted: str = "#F8FAFC"
    text: str = "#0F172A"
    text_muted: str = "#475569"
    border: str = "#D7E0EA"
    border_strong: str = "#94A3B8"
    brand: str = "#0F766E"
    brand_hover: str = "#0D9488"
    brand_pressed: str = "#134E4A"
    focus: str = "#14B8A6"
    success: str = "#15803D"
    warning: str = "#B45309"
    error: str = "#DC2626"
    disabled_background: str = "#F1F5F9"
    disabled_text: str = "#94A3B8"
    spacing_unit: int = 8
    control_height: int = 40
    compact_control_height: int = 34
    radius: int = 8
    card_radius: int = 12


UI_TOKENS = UiTokens()
DEFAULT_UI_TOKENS = UI_TOKENS


class SurfaceRole(StrEnum):
    """The three supported visual surfaces plus transparent layout wrappers."""

    PAGE = "page"
    CARD = "card"
    DIALOG = "dialog"
    TRANSPARENT = "transparent"


class FeedbackSeverity(StrEnum):
    """Semantic feedback levels used by inline banners and state containers."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

    @classmethod
    def coerce(cls, value: FeedbackSeverity | str) -> FeedbackSeverity:
        """Normalize legacy values while retaining a safe informational fallback."""

        normalized = str(value).strip().lower()
        if normalized == "danger":
            normalized = cls.ERROR.value
        try:
            return cls(normalized)
        except ValueError:
            return cls.INFO


class ViewState(StrEnum):
    """Mutually exclusive states rendered by :class:`StateHost`."""

    LOADING = "loading"
    CONTENT = "content"
    EMPTY = "empty"
    ERROR = "error"

    @classmethod
    def coerce(cls, value: ViewState | str) -> ViewState:
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError as exc:
            raise ValueError(f"Unsupported view state: {value!r}") from exc


class ColumnPriority(IntEnum):
    """Relative importance used when allocating constrained table width.

    Lower values are more important.  Critical columns are allocated their
    preferred width first; low-priority columns shrink toward their minimum
    before the table falls back to horizontal scrolling.
    """

    CRITICAL = 0
    HIGH = 100
    NORMAL = 200
    LOW = 300


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    """Presentation and data-extraction contract for an adaptive table column."""

    header: str
    key: str | None = None
    minimum_width: int = 88
    preferred_width: int | None = None
    priority: int = int(ColumnPriority.NORMAL)
    formatter: Callable[[object], str] | None = None
    wrap: bool = False
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    stretch: bool = False
    status: bool = False

    def __post_init__(self) -> None:
        if not self.header.strip():
            raise ValueError("ColumnSpec.header must not be blank")
        if self.minimum_width < 40:
            raise ValueError("ColumnSpec.minimum_width must be at least 40")
        if self.preferred_width is not None and self.preferred_width < self.minimum_width:
            raise ValueError("ColumnSpec.preferred_width cannot be less than minimum_width")


def set_surface_role(widget: QWidget, role: SurfaceRole | str) -> None:
    """Apply a semantic surface role and refresh the widget's style safely."""

    resolved = role if isinstance(role, SurfaceRole) else SurfaceRole(str(role))
    widget.setProperty("uiSurface", resolved.value)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


__all__ = [
    "ColumnPriority",
    "ColumnSpec",
    "DEFAULT_UI_TOKENS",
    "FeedbackSeverity",
    "SurfaceRole",
    "UI_TOKENS",
    "UiTokens",
    "ViewState",
    "set_surface_role",
]
