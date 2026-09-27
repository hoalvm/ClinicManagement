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


class ColumnDisplayMode(StrEnum):
    """How a table cell presents text when space is constrained."""

    FULL = "full"
    ELIDE = "elide"
    WRAP_2 = "wrap_2"


@dataclass(frozen=True, slots=True)
class CellValue:
    """Structured table content with an optional muted supporting line."""

    primary: str
    secondary: str | None = None
    tooltip: str | None = None
    accessible_text: str | None = None

    @property
    def display_text(self) -> str:
        return (
            f"{self.primary}\n{self.secondary}"
            if self.secondary
            else self.primary
        )

    @property
    def full_text(self) -> str:
        return self.tooltip or (
            f"{self.primary} — {self.secondary}"
            if self.secondary
            else self.primary
        )


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    """Presentation and data-extraction contract for an adaptive table column."""

    header: str
    key: str | None = None
    minimum_width: int = 88
    preferred_width: int | None = None
    maximum_width: int | None = None
    grow_weight: int = 0
    priority: int = int(ColumnPriority.NORMAL)
    formatter: Callable[[object], str | CellValue] | None = None
    display_mode: ColumnDisplayMode = ColumnDisplayMode.ELIDE
    line_limit: int = 1
    preserve_full: bool = False
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
        if self.maximum_width is not None:
            baseline = self.preferred_width or self.minimum_width
            if self.maximum_width < baseline:
                raise ValueError(
                    "ColumnSpec.maximum_width cannot be less than preferred_width"
                )
        if self.grow_weight < 0:
            raise ValueError("ColumnSpec.grow_weight cannot be negative")
        if self.line_limit not in (1, 2):
            raise ValueError("ColumnSpec.line_limit must be 1 or 2")

        # Compatibility for the first UI upgrade.  New declarations should use
        # the explicit display/growth contracts, while legacy call sites keep
        # their behavior until they are migrated.
        if self.stretch and self.grow_weight == 0:
            object.__setattr__(self, "grow_weight", 1)
        if self.wrap and self.display_mode is ColumnDisplayMode.ELIDE:
            object.__setattr__(self, "display_mode", ColumnDisplayMode.WRAP_2)
            object.__setattr__(self, "line_limit", 2)
        if self.display_mode is ColumnDisplayMode.WRAP_2 and self.line_limit == 1:
            object.__setattr__(self, "line_limit", 2)
        if self.display_mode is ColumnDisplayMode.FULL:
            object.__setattr__(self, "preserve_full", True)
        if self.status:
            # Status is operational information, not decorative metadata.  It
            # must remain readable instead of degrading to an ambiguous pill
            # such as "Đã xác…" when the viewport becomes constrained.
            object.__setattr__(self, "display_mode", ColumnDisplayMode.FULL)
            object.__setattr__(self, "preserve_full", True)


def set_surface_role(widget: QWidget, role: SurfaceRole | str) -> None:
    """Apply a semantic surface role and refresh the widget's style safely."""

    resolved = role if isinstance(role, SurfaceRole) else SurfaceRole(str(role))
    widget.setProperty("uiSurface", resolved.value)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


__all__ = [
    "CellValue",
    "ColumnDisplayMode",
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
