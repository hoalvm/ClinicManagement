"""Small, themeable line icons drawn with Qt primitives.

The module deliberately avoids bundled image assets and icon fonts.  Icons are
rendered lazily after a ``QApplication`` exists and cached by name, palette,
size, and device-pixel ratio.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from PySide6.QtCore import QLineF, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QAbstractButton


class IconName(StrEnum):
    """Names supported by :func:`line_icon`."""

    DASHBOARD = "dashboard"
    USER = "user"
    CALENDAR = "calendar"
    MEDICAL = "medical"
    INVOICE = "invoice"
    LOGOUT = "logout"
    REFRESH = "refresh"
    BACK = "back"
    SEARCH = "search"
    EYE = "eye"
    EDIT = "edit"
    SAVE = "save"


AVAILABLE_ICONS = tuple(icon.value for icon in IconName)

_ALIASES: dict[str, IconName] = {
    "appointments": IconName.CALENDAR,
    "medical_history": IconName.MEDICAL,
    "profile": IconName.USER,
    "invoice_history": IconName.INVOICE,
}


def _normalise_name(name: IconName | str) -> IconName:
    if isinstance(name, IconName):
        return name
    candidate = str(name).strip().lower().replace("-", "_").replace(" ", "_")
    if candidate in _ALIASES:
        return _ALIASES[candidate]
    try:
        return IconName(candidate)
    except ValueError as exc:
        supported = ", ".join(AVAILABLE_ICONS)
        raise ValueError(f"Unknown icon {name!r}. Supported icons: {supported}") from exc


def _as_color(value: QColor | str, *, argument: str) -> QColor:
    color = QColor(value)
    if not color.isValid():
        raise ValueError(f"{argument} must be a valid Qt color")
    return color


def _disabled_color(color: QColor) -> QColor:
    muted = QColor(color)
    muted.setAlpha(96)
    return muted


def _device_pixel_ratio() -> float:
    application = QGuiApplication.instance()
    if application is None:
        raise RuntimeError("line_icon() requires a QApplication or QGuiApplication instance")
    screen = application.primaryScreen()
    return max(1.0, float(screen.devicePixelRatio()) if screen is not None else 1.0)


def _prepare_painter(pixmap: QPixmap, color: QColor, logical_size: int) -> QPainter:
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.scale(logical_size / 24.0, logical_size / 24.0)
    pen = QPen(color, 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    return painter


def _draw_dashboard(painter: QPainter) -> None:
    for rect in (
        QRectF(3, 3, 7, 9),
        QRectF(14, 3, 7, 6),
        QRectF(3, 16, 7, 5),
        QRectF(14, 13, 7, 8),
    ):
        painter.drawRoundedRect(rect, 1.4, 1.4)


def _draw_user(painter: QPainter) -> None:
    painter.drawEllipse(QPointF(12, 7.2), 3.7, 3.7)
    shoulders = QPainterPath()
    shoulders.moveTo(4, 21)
    shoulders.cubicTo(4.8, 15.8, 7.6, 13.3, 12, 13.3)
    shoulders.cubicTo(16.4, 13.3, 19.2, 15.8, 20, 21)
    painter.drawPath(shoulders)


def _draw_calendar(painter: QPainter) -> None:
    painter.drawRoundedRect(QRectF(3, 4.5, 18, 16.5), 2.2, 2.2)
    painter.drawLine(QLineF(3, 9.5, 21, 9.5))
    painter.drawLine(QLineF(7.5, 2.5, 7.5, 6.5))
    painter.drawLine(QLineF(16.5, 2.5, 16.5, 6.5))
    painter.drawLine(QLineF(7, 13.5, 9, 13.5))
    painter.drawLine(QLineF(12, 13.5, 14, 13.5))
    painter.drawLine(QLineF(17, 13.5, 18, 13.5))
    painter.drawLine(QLineF(7, 17.5, 9, 17.5))
    painter.drawLine(QLineF(12, 17.5, 14, 17.5))


def _draw_medical(painter: QPainter) -> None:
    painter.drawRoundedRect(QRectF(4, 4, 16, 17), 2.2, 2.2)
    painter.drawRoundedRect(QRectF(8, 2.5, 8, 4), 1.2, 1.2)
    painter.drawLine(QLineF(12, 9, 12, 16))
    painter.drawLine(QLineF(8.5, 12.5, 15.5, 12.5))


def _draw_invoice(painter: QPainter) -> None:
    receipt = QPainterPath()
    receipt.moveTo(5, 3)
    receipt.lineTo(19, 3)
    receipt.lineTo(19, 21)
    receipt.lineTo(16.6, 19.4)
    receipt.lineTo(14.3, 21)
    receipt.lineTo(12, 19.4)
    receipt.lineTo(9.7, 21)
    receipt.lineTo(7.4, 19.4)
    receipt.lineTo(5, 21)
    receipt.closeSubpath()
    painter.drawPath(receipt)
    painter.drawLine(QLineF(8, 8, 16, 8))
    painter.drawLine(QLineF(8, 12, 16, 12))
    painter.drawLine(QLineF(8, 16, 13.5, 16))


def _draw_logout(painter: QPainter) -> None:
    door = QPainterPath()
    door.moveTo(10, 4)
    door.lineTo(4, 4)
    door.lineTo(4, 20)
    door.lineTo(10, 20)
    painter.drawPath(door)
    painter.drawLine(QLineF(9, 12, 21, 12))
    painter.drawLine(QLineF(17, 8, 21, 12))
    painter.drawLine(QLineF(17, 16, 21, 12))


def _draw_refresh(painter: QPainter) -> None:
    first_arc = QPainterPath()
    first_arc.arcMoveTo(QRectF(4, 4, 16, 16), 38)
    first_arc.arcTo(QRectF(4, 4, 16, 16), 38, 220)
    painter.drawPath(first_arc)
    painter.drawLine(QLineF(4.2, 8.1, 4.2, 13.1))
    painter.drawLine(QLineF(4.2, 8.1, 9.2, 8.1))

    second_arc = QPainterPath()
    second_arc.arcMoveTo(QRectF(4, 4, 16, 16), 218)
    second_arc.arcTo(QRectF(4, 4, 16, 16), 218, 220)
    painter.drawPath(second_arc)
    painter.drawLine(QLineF(19.8, 15.9, 19.8, 10.9))
    painter.drawLine(QLineF(19.8, 15.9, 14.8, 15.9))


def _draw_back(painter: QPainter) -> None:
    painter.drawLine(QLineF(4, 12, 20, 12))
    painter.drawLine(QLineF(4, 12, 10, 6))
    painter.drawLine(QLineF(4, 12, 10, 18))


def _draw_search(painter: QPainter) -> None:
    painter.drawEllipse(QPointF(10, 10), 6, 6)
    painter.drawLine(QLineF(14.5, 14.5, 20.5, 20.5))


def _draw_eye(painter: QPainter) -> None:
    eye = QPainterPath()
    eye.moveTo(2.5, 12)
    eye.cubicTo(6.1, 6.8, 9.2, 5.2, 12, 5.2)
    eye.cubicTo(14.8, 5.2, 17.9, 6.8, 21.5, 12)
    eye.cubicTo(17.9, 17.2, 14.8, 18.8, 12, 18.8)
    eye.cubicTo(9.2, 18.8, 6.1, 17.2, 2.5, 12)
    eye.closeSubpath()
    painter.drawPath(eye)
    painter.drawEllipse(QPointF(12, 12), 3, 3)


def _draw_edit(painter: QPainter) -> None:
    pencil = QPainterPath()
    pencil.moveTo(5, 19)
    pencil.lineTo(6.4, 13.6)
    pencil.lineTo(15.1, 4.9)
    pencil.lineTo(19.1, 8.9)
    pencil.lineTo(10.4, 17.6)
    pencil.closeSubpath()
    painter.drawPath(pencil)
    painter.drawLine(QLineF(13.7, 6.3, 17.7, 10.3))
    painter.drawLine(QLineF(5, 19, 4, 21))
    painter.drawLine(QLineF(4, 21, 9, 20))


def _draw_save(painter: QPainter) -> None:
    painter.drawRoundedRect(QRectF(4, 3, 16, 18), 2, 2)
    painter.drawRect(QRectF(7, 3, 9, 6))
    painter.drawRoundedRect(QRectF(8, 13, 8, 8), 1.2, 1.2)
    painter.drawLine(QLineF(14, 5, 14, 8))


_DRAWERS = {
    IconName.DASHBOARD: _draw_dashboard,
    IconName.USER: _draw_user,
    IconName.CALENDAR: _draw_calendar,
    IconName.MEDICAL: _draw_medical,
    IconName.INVOICE: _draw_invoice,
    IconName.LOGOUT: _draw_logout,
    IconName.REFRESH: _draw_refresh,
    IconName.BACK: _draw_back,
    IconName.SEARCH: _draw_search,
    IconName.EYE: _draw_eye,
    IconName.EDIT: _draw_edit,
    IconName.SAVE: _draw_save,
}


def _render_pixmap(name: IconName, color: QColor, size: int, ratio: float) -> QPixmap:
    pixel_size = max(1, round(size * ratio))
    pixmap = QPixmap(pixel_size, pixel_size)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = _prepare_painter(pixmap, color, size)
    _DRAWERS[name](painter)
    painter.end()
    return pixmap


@lru_cache(maxsize=256)
def _cached_icon(
    name: IconName,
    normal_rgba: int,
    active_rgba: int,
    selected_rgba: int,
    disabled_rgba: int,
    size: int,
    ratio: float,
) -> QIcon:
    icon = QIcon()
    colors = {
        QIcon.Mode.Normal: QColor.fromRgba(normal_rgba),
        QIcon.Mode.Active: QColor.fromRgba(active_rgba),
        QIcon.Mode.Selected: QColor.fromRgba(selected_rgba),
        QIcon.Mode.Disabled: QColor.fromRgba(disabled_rgba),
    }
    for mode, color in colors.items():
        icon.addPixmap(_render_pixmap(name, color, size, ratio), mode, QIcon.State.Off)
    return icon


def line_icon(
    name: IconName | str,
    color: QColor | str = "#64748B",
    *,
    size: int = 20,
    active_color: QColor | str | None = None,
    selected_color: QColor | str | None = None,
    disabled_color: QColor | str | None = None,
) -> QIcon:
    """Return a cached, high-DPI line icon with explicit Qt state colors.

    A ``QApplication`` must exist before this function is called.  Aliases for
    route names (``profile``, ``appointments``, ``medical_history``, and
    ``invoice_history``) are accepted for convenient sidebar integration.
    """

    if size <= 0:
        raise ValueError("size must be greater than zero")
    icon_name = _normalise_name(name)
    normal = _as_color(color, argument="color")
    active = _as_color(active_color, argument="active_color") if active_color else normal
    selected = _as_color(selected_color, argument="selected_color") if selected_color else active
    disabled = (
        _as_color(disabled_color, argument="disabled_color")
        if disabled_color
        else _disabled_color(normal)
    )
    ratio = round(_device_pixel_ratio(), 2)
    cached = _cached_icon(
        icon_name,
        normal.rgba(),
        active.rgba(),
        selected.rgba(),
        disabled.rgba(),
        size,
        ratio,
    )
    return QIcon(cached)


def apply_line_icon(
    button: QAbstractButton,
    name: IconName | str,
    color: QColor | str = "#64748B",
    *,
    size: int = 18,
    active_color: QColor | str | None = None,
    selected_color: QColor | str | None = None,
    disabled_color: QColor | str | None = None,
    accessible_name: str | None = None,
) -> None:
    """Apply a line icon and accessible metadata to a Qt button."""

    button.setIcon(
        line_icon(
            name,
            color,
            size=size,
            active_color=active_color,
            selected_color=selected_color,
            disabled_color=disabled_color,
        )
    )
    button.setIconSize(QSize(size, size))
    if accessible_name:
        button.setAccessibleName(accessible_name)
        if not button.text() and not button.toolTip():
            button.setToolTip(accessible_name)


def clear_icon_cache() -> None:
    """Drop rendered icon variants, primarily for live theme changes."""

    _cached_icon.cache_clear()


__all__ = [
    "AVAILABLE_ICONS",
    "IconName",
    "apply_line_icon",
    "clear_icon_cache",
    "line_icon",
]
