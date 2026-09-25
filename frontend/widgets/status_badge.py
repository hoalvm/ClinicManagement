"""Semantic status pills for labels and item-view cells."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from PySide6.QtCore import QModelIndex, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)


@dataclass(frozen=True, slots=True)
class StatusColors:
    """Foreground, background, and outline colors for a semantic status."""

    foreground: str
    background: str
    border: str


_SUCCESS: Final = StatusColors("#166534", "#DCFCE7", "#BBF7D0")
_INFO: Final = StatusColors("#075985", "#E0F2FE", "#BAE6FD")
_VIOLET: Final = StatusColors("#5B21B6", "#EDE9FE", "#DDD6FE")
_WARNING: Final = StatusColors("#92400E", "#FEF3C7", "#FDE68A")
_DANGER: Final = StatusColors("#991B1B", "#FEE2E2", "#FECACA")
_NEUTRAL: Final = StatusColors("#334155", "#E2E8F0", "#CBD5E1")

STATUS_COLORS = MappingProxyType(
    {
        "PAID": _SUCCESS,
        "COMPLETED": _SUCCESS,
        "CONFIRMED": _INFO,
        "CHECKED_IN": _INFO,
        "SCHEDULED": _INFO,
        "IN_PROGRESS": _VIOLET,
        "PENDING": _WARNING,
        "UNPAID": _WARNING,
        "OVERDUE": _DANGER,
        "CANCELLED": _DANGER,
        "CANCELED": _DANGER,
        "FAILED": _DANGER,
        "ACTIVE": _SUCCESS,
        "INACTIVE": _DANGER,
        "HOAT_DONG": _SUCCESS,
        "HOẠT ĐỘNG": _SUCCESS,
        "DA_KHOA": _DANGER,
        "ĐÃ KHÓA": _DANGER,
        "DANG_KHAM": _VIOLET,
        "ĐANG KHÁM": _VIOLET,
        "HOAN_TAT": _SUCCESS,
        "HOÀN TẤT": _SUCCESS,
        "CHO_KHAM": _WARNING,
        "CHỜ KHÁM": _WARNING,
        "DA_THANH_TOAN": _SUCCESS,
        "ĐÃ THANH TOÁN": _SUCCESS,
        "CHUA_THANH_TOAN": _WARNING,
        "CHƯA THANH TOÁN": _WARNING,
        "PATIENT": _INFO,
        "DOCTOR": _VIOLET,
        "STAFF": _SUCCESS,
        "ADMIN": _WARNING,
        "CASH": _INFO,
        "CARD": _VIOLET,
    }
)

STATUS_LABELS_VN: Final[dict[str, str]] = {
    "PAID": "Đã thanh toán",
    "UNPAID": "Chưa thanh toán",
    "COMPLETED": "Hoàn thành",
    "CONFIRMED": "Đã xác nhận",
    "CHECKED_IN": "Chờ khám",
    "SCHEDULED": "Đã đặt",
    "IN_PROGRESS": "Đang khám",
    "PENDING": "Chờ xử lý",
    "OVERDUE": "Quá hạn",
    "CANCELLED": "Đã hủy",
    "CANCELED": "Đã hủy",
    "FAILED": "Thất bại",
    "ACTIVE": "Hoạt động",
    "INACTIVE": "Đã khóa",
    "HOAT_DONG": "Hoạt động",
    "HOẠT ĐỘNG": "Hoạt động",
    "DA_KHOA": "Đã khóa",
    "ĐÃ KHÓA": "Đã khóa",
    "DANG_KHAM": "Đang khám",
    "ĐANG KHÁM": "Đang khám",
    "HOAN_TAT": "Hoàn thành",
    "HOÀN TẤT": "Hoàn thành",
    "CHO_KHAM": "Chờ khám",
    "CHỜ KHÁM": "Chờ khám",
    "DA_THANH_TOAN": "Đã thanh toán",
    "ĐÃ THANH TOÁN": "Đã thanh toán",
    "CHUA_THANH_TOAN": "Chưa thanh toán",
    "CHƯA THANH TOÁN": "Chưa thanh toán",
    "PATIENT": "Bệnh nhân",
    "DOCTOR": "Bác sĩ",
    "STAFF": "Nhân viên",
    "ADMIN": "Quản trị viên",
    "CASH": "Tiền mặt",
    "CARD": "Thẻ",
    "TRANSFER": "Chuyển khoản",
}

STATUS_LABELS_EN: Final[dict[str, str]] = {
    "PAID": "Paid",
    "UNPAID": "Unpaid",
    "COMPLETED": "Completed",
    "CONFIRMED": "Confirmed",
    "CHECKED_IN": "Checked In",
    "SCHEDULED": "Scheduled",
    "IN_PROGRESS": "In Progress",
    "PENDING": "Pending",
    "OVERDUE": "Overdue",
    "CANCELLED": "Cancelled",
    "CANCELED": "Cancelled",
    "FAILED": "Failed",
    "ACTIVE": "Active",
    "INACTIVE": "Locked",
    "HOAT_DONG": "Active",
    "HOẠT ĐỘNG": "Active",
    "DA_KHOA": "Locked",
    "ĐÃ KHÓA": "Locked",
    "DANG_KHAM": "In Progress",
    "ĐANG KHÁM": "In Progress",
    "HOAN_TAT": "Completed",
    "HOÀN TẤT": "Completed",
    "CHO_KHAM": "Checked In",
    "CHỜ KHÁM": "Checked In",
    "DA_THANH_TOAN": "Paid",
    "ĐÃ THANH TOÁN": "Paid",
    "CHUA_THANH_TOAN": "Unpaid",
    "CHƯA THANH TOÁN": "Unpaid",
    "PATIENT": "Patient",
    "DOCTOR": "Doctor",
    "STAFF": "Staff",
    "ADMIN": "Admin",
    "CASH": "Cash",
    "CARD": "Card",
    "TRANSFER": "Transfer",
}


def _current_lang() -> str:
    try:
        from frontend.core.i18n import get_i18n

        return get_i18n().current_language
    except Exception:
        return "vi"


def normalize_status(value: object) -> str:
    """Convert API- or display-style status values to a stable lookup key."""

    if value is None:
        return ""
    return str(value).strip().upper().replace("-", "_").replace(" ", "_")


def display_status(value: object, lang: str | None = None) -> str:
    """Return a compact human-readable label for a status value."""

    if value is None or str(value).strip() == "":
        return "—"
    normalized = normalize_status(value)
    if not normalized:
        return "—"

    target_lang = lang or _current_lang()
    if target_lang == "en":
        if normalized in STATUS_LABELS_EN:
            return STATUS_LABELS_EN[normalized]
        return normalized.replace("_", " ").title()
    else:
        if normalized in STATUS_LABELS_VN:
            return STATUS_LABELS_VN[normalized]
        return str(value).strip()


def status_colors(value: object) -> StatusColors:
    """Return semantic colors, falling back to a neutral pill."""

    return STATUS_COLORS.get(normalize_status(value), _NEUTRAL)


def _with_enabled_alpha(color: str, enabled: bool) -> QColor:
    resolved = QColor(color)
    if not enabled:
        resolved.setAlpha(112)
    return resolved


def _badge_font(source: QFont) -> QFont:
    font = QFont(source)
    font.setWeight(QFont.Weight.DemiBold)
    return font


def _paint_badge(
    painter: QPainter,
    rect: QRectF,
    text: str,
    font: QFont,
    colors: StatusColors,
    *,
    enabled: bool,
) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setFont(font)
    painter.setPen(_with_enabled_alpha(colors.border, enabled))
    painter.setBrush(_with_enabled_alpha(colors.background, enabled))
    radius = min(11.0, rect.height() / 2.0)
    painter.drawRoundedRect(rect, radius, radius)
    painter.setPen(_with_enabled_alpha(colors.foreground, enabled))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    painter.restore()


class StatusBadge(QLabel):
    """A compact, accessible status label painted as a rounded pill."""

    _horizontal_padding = 20
    _vertical_padding = 8
    _minimum_height = 26

    def __init__(self, status: object = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self._status = ""
        self._colors = _NEUTRAL
        self.set_status(status)

    @property
    def status(self) -> str:
        return self._status

    def set_status(self, status: object) -> None:
        """Set the value, accessible label, palette, and styling property."""

        self._status = normalize_status(status)
        self._colors = status_colors(status)
        text = display_status(status)
        super().setText(text)
        self.setAccessibleName(f"Status: {text}")
        self.setProperty("status", self._status.lower())
        self.updateGeometry()
        self.update()

    def set_colors(self, colors: StatusColors) -> None:
        """Override colors for this badge without changing its status value."""

        self._colors = colors
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        metrics = QFontMetrics(_badge_font(self.font()))
        return QSize(
            metrics.horizontalAdvance(self.text()) + self._horizontal_padding,
            max(self._minimum_height, metrics.height() + self._vertical_padding),
        )

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return self.sizeHint()

    def paintEvent(self, event: object) -> None:  # noqa: N802, ARG002
        painter = QPainter(self)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        _paint_badge(
            painter,
            rect,
            self.text(),
            _badge_font(self.font()),
            self._colors,
            enabled=self.isEnabled(),
        )


class StatusBadgeDelegate(QStyledItemDelegate):
    """Paint a status pill without allocating a QWidget for every table cell."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        status_role: int = int(Qt.ItemDataRole.DisplayRole),
        horizontal_margin: int = 8,
    ) -> None:
        super().__init__(parent)
        self.status_role = status_role
        self.horizontal_margin = max(0, horizontal_margin)

    def _value(self, index: QModelIndex) -> object:
        value = index.data(self.status_role)
        if value is None and self.status_role != int(Qt.ItemDataRole.DisplayRole):
            return index.data(Qt.ItemDataRole.DisplayRole)
        return value

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        background_option = QStyleOptionViewItem(option)
        self.initStyleOption(background_option, index)
        background_option.text = ""
        background_option.icon = QIcon()
        style = option.widget.style() if option.widget is not None else QApplication.style()
        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            background_option,
            painter,
            option.widget,
        )

        raw_status = self._value(index)
        text = display_status(raw_status)
        font = _badge_font(option.font)
        metrics = QFontMetrics(font)
        available = option.rect.adjusted(
            self.horizontal_margin,
            4,
            -self.horizontal_margin,
            -4,
        )
        max_text_width = max(0, available.width() - 20)
        text = metrics.elidedText(text, Qt.TextElideMode.ElideRight, max_text_width)
        badge_width = min(available.width(), metrics.horizontalAdvance(text) + 20)
        badge_height = min(26, available.height())
        badge_rect = QRectF(
            available.center().x() - badge_width / 2,
            available.center().y() - badge_height / 2,
            badge_width,
            badge_height,
        )
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        _paint_badge(
            painter,
            badge_rect,
            text,
            font,
            status_colors(raw_status),
            enabled=enabled,
        )

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:  # noqa: N802
        base = super().sizeHint(option, index)
        metrics = QFontMetrics(_badge_font(option.font))
        width = metrics.horizontalAdvance(display_status(self._value(index))) + 36
        return QSize(max(base.width(), width), max(base.height(), 42))


__all__ = [
    "STATUS_COLORS",
    "StatusBadge",
    "StatusBadgeDelegate",
    "StatusColors",
    "display_status",
    "normalize_status",
    "status_colors",
]
