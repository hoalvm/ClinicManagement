"""Role-agnostic application sidebar for authenticated desktop shells."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from frontend.ui.icons import IconName, apply_line_icon
from frontend.widgets.language_selector import LanguageSelector


@dataclass(frozen=True, slots=True)
class NavigationItem:
    """One permission-filtered destination shown in :class:`AppSidebar`."""

    route: str
    label: str
    icon: IconName | str = IconName.DASHBOARD
    section: str = ""

    def __post_init__(self) -> None:
        if not self.route.strip():
            raise ValueError("NavigationItem.route must not be blank")
        if not self.label.strip():
            raise ValueError("NavigationItem.label must not be blank")


class AppSidebar(QFrame):
    """Shared sidebar with configurable navigation and preserved accessibility."""

    navigation_requested = Signal(str)
    logout_requested = Signal()
    compact_changed = Signal(bool)

    EXPANDED_WIDTH = 232
    COMPACT_WIDTH = 78

    def __init__(
        self,
        items: Sequence[NavigationItem],
        parent: QWidget | None = None,
        *,
        brand_title: str = "ClinicCare",
        brand_subtitle: str = "Quản lý phòng khám",
        logout_text: str = "Đăng xuất",
        show_language_selector: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("Điều hướng ứng dụng")
        self._items = tuple(items)
        if not self._items:
            raise ValueError("AppSidebar requires at least one navigation item")
        routes = [item.route for item in self._items]
        if len(routes) != len(set(routes)):
            raise ValueError("NavigationItem routes must be unique")
        self._compact = False
        self._active_route = ""
        self._logout_text = logout_text
        self._labels = {item.route: item.label for item in self._items}

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 20, 14, 16)
        self._layout.setSpacing(7)
        self._build_brand(brand_title, brand_subtitle)
        self._layout.addSpacing(18)

        self._buttons: dict[str, QPushButton] = {}
        self._section_labels: list[QLabel] = []
        current_section: str | None = None
        for item in self._items:
            if item.section and item.section != current_section:
                section_label = QLabel(item.section)
                section_label.setObjectName("sidebarSectionLabel")
                section_label.setAccessibleName(item.section)
                self._section_labels.append(section_label)
                self._layout.addWidget(section_label)
                current_section = item.section
            self._add_navigation_button(item)

        self._layout.addStretch(1)
        self._build_user_context()

        self.lang_selector: LanguageSelector | None = None
        if show_language_selector:
            self.lang_selector = LanguageSelector(self, show_label=False)
            self._layout.addSpacing(8)
            self._layout.addWidget(self.lang_selector)

        self._layout.addSpacing(8)
        self.logout_button = QPushButton(logout_text)
        self.logout_button.setObjectName("logoutButton")
        self.logout_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_button.setToolTip(logout_text)
        apply_line_icon(
            self.logout_button,
            IconName.LOGOUT,
            active_color="#DC2626",
            accessible_name=logout_text,
        )
        self.logout_button.clicked.connect(self.logout_requested)
        self._layout.addWidget(self.logout_button)

        self.set_compact(False)

    @property
    def is_compact(self) -> bool:
        return self._compact

    @property
    def active_route(self) -> str:
        return self._active_route

    @property
    def navigation_items(self) -> tuple[NavigationItem, ...]:
        return self._items

    def _build_brand(self, title: str, subtitle: str) -> None:
        self._brand_row = QWidget()
        brand_layout = QHBoxLayout(self._brand_row)
        brand_layout.setContentsMargins(4, 0, 2, 0)
        brand_layout.setSpacing(11)

        self._brand_mark = QLabel((title.strip() or "C")[0].upper())
        self._brand_mark.setObjectName("sidebarBrandMark")
        self._brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._brand_mark.setFixedSize(36, 36)
        self._brand_mark.setAccessibleName(title)
        brand_layout.addWidget(self._brand_mark)

        self._brand_text = QWidget()
        brand_text_layout = QVBoxLayout(self._brand_text)
        brand_text_layout.setContentsMargins(0, 1, 0, 0)
        brand_text_layout.setSpacing(0)
        self._brand_label = QLabel(title)
        self._brand_label.setObjectName("brandLabel")
        self._brand_subtitle = QLabel(subtitle)
        self._brand_subtitle.setObjectName("sidebarSubtitle")
        brand_text_layout.addWidget(self._brand_label)
        brand_text_layout.addWidget(self._brand_subtitle)
        brand_layout.addWidget(self._brand_text, 1)
        self._layout.addWidget(self._brand_row)

    def _add_navigation_button(self, item: NavigationItem) -> None:
        button = QPushButton(item.label)
        button.setObjectName("navButton")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAccessibleName(item.label)
        button.setToolTip(item.label)
        apply_line_icon(
            button,
            item.icon,
            active_color="#2DD4BF",
            selected_color="#2DD4BF",
            accessible_name=item.label,
        )
        button.clicked.connect(
            lambda _checked=False, route=item.route: self.navigation_requested.emit(route)
        )
        self._layout.addWidget(button)
        self._buttons[item.route] = button

    def _build_user_context(self) -> None:
        self._user_row = QFrame()
        self._user_row.setObjectName("sidebarUser")
        user_layout = QHBoxLayout(self._user_row)
        user_layout.setContentsMargins(5, 8, 3, 7)
        user_layout.setSpacing(10)

        self._avatar = QFrame()
        self._avatar.setObjectName("userAvatar")
        self._avatar.setFixedSize(38, 38)
        avatar_layout = QVBoxLayout(self._avatar)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        self._avatar_text = QLabel("U")
        self._avatar_text.setObjectName("userAvatarText")
        self._avatar_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_layout.addWidget(self._avatar_text)
        user_layout.addWidget(self._avatar)

        self._user_text = QWidget()
        user_text_layout = QVBoxLayout(self._user_text)
        user_text_layout.setContentsMargins(0, 0, 0, 0)
        user_text_layout.setSpacing(1)
        self._user_name_label = QLabel("Người dùng")
        self._user_name_label.setObjectName("sidebarUserName")
        self._user_name_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._user_role_label = QLabel("Tài khoản")
        self._user_role_label.setObjectName("sidebarUserRole")
        user_text_layout.addWidget(self._user_name_label)
        user_text_layout.addWidget(self._user_role_label)
        user_layout.addWidget(self._user_text, 1)
        self._layout.addWidget(self._user_row)
        self.set_user(None)

    @staticmethod
    def _initials(name: str) -> str:
        words = [word for word in name.strip().split() if word]
        if not words:
            return "U"
        if len(words) == 1:
            return words[0][0].upper()
        return f"{words[0][0]}{words[-1][0]}".upper()

    def set_user(
        self,
        user: Mapping[str, Any] | None,
        *,
        role_label: str | None = None,
    ) -> None:
        data = user or {}
        name = str(data.get("full_name") or data.get("username") or "Người dùng").strip()
        role = role_label or str(data.get("role_label") or data.get("role") or "Tài khoản")
        self._user_name_label.setText(name)
        self._user_role_label.setText(role)
        self._avatar_text.setText(self._initials(name))
        context = f"Đăng nhập với {name}, {role}"
        self._user_row.setAccessibleName(context)
        self._user_row.setToolTip(context)

    def clear_user(self) -> None:
        self.set_user(None)

    def set_labels(
        self,
        labels: Mapping[str, str],
        *,
        logout_text: str | None = None,
    ) -> None:
        """Update translated route labels without rebuilding navigation state."""

        for item in self._items:
            label = labels.get(item.route, item.label)
            self._labels[item.route] = label
            button = self._buttons[item.route]
            button.setAccessibleName(label)
            button.setToolTip(label)
            button.setText("" if self._compact else label)
        if logout_text is not None:
            self._logout_text = logout_text
        self.logout_button.setText("" if self._compact else self._logout_text)
        self.logout_button.setAccessibleName(self._logout_text)
        self.logout_button.setToolTip(self._logout_text)

    def set_compact(self, compact: bool) -> None:
        compact = bool(compact)
        changed = compact != self._compact
        self._compact = compact
        self.setProperty("compact", compact)
        self.setFixedWidth(self.COMPACT_WIDTH if compact else self.EXPANDED_WIDTH)
        horizontal_margin = 10 if compact else 14
        self._layout.setContentsMargins(horizontal_margin, 20, horizontal_margin, 16)
        self._brand_text.setVisible(not compact)
        self._user_text.setVisible(not compact)
        for label in self._section_labels:
            label.setVisible(not compact)
        if self.lang_selector is not None:
            self.lang_selector.setVisible(not compact)
        for item in self._items:
            button = self._buttons[item.route]
            button.setText("" if compact else self._labels[item.route])
            button.setProperty("compact", compact)
            button.style().unpolish(button)
            button.style().polish(button)
        self.logout_button.setText("" if compact else self._logout_text)
        self.logout_button.setProperty("compact", compact)
        self.logout_button.style().unpolish(self.logout_button)
        self.logout_button.style().polish(self.logout_button)
        self.style().unpolish(self)
        self.style().polish(self)
        self.updateGeometry()
        if changed:
            self.compact_changed.emit(compact)

    def set_active(self, route: str) -> None:
        if route not in self._buttons:
            raise KeyError(f"Unknown sidebar route: {route}")
        self._active_route = route
        for key, button in self._buttons.items():
            button.setChecked(key == route)


# Shorter semantic alias for callers that prefer the plan terminology.
RoleSidebar = AppSidebar


__all__ = ["AppSidebar", "NavigationItem", "RoleSidebar"]
