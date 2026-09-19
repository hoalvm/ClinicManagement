"""Primary authenticated navigation and signed-in patient context."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from frontend.ui.icons import apply_line_icon


class Sidebar(QFrame):
    """Persistent navigation that can collapse without losing accessibility."""

    navigation_requested = Signal(str)
    logout_requested = Signal()

    EXPANDED_WIDTH = 232
    COMPACT_WIDTH = 78

    _ITEMS = (
        ("dashboard", "Dashboard"),
        ("profile", "My Profile"),
        ("appointments", "Appointments"),
        ("medical_history", "Medical History"),
        ("invoice_history", "Invoice History"),
    )
    _ICONS = {
        "dashboard": "dashboard",
        "profile": "user",
        "appointments": "calendar",
        "medical_history": "medical",
        "invoice_history": "invoice",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("Patient portal navigation")
        self._compact = False
        self._active_route = ""
        self._user_name = "Patient"
        self._user_role = "Patient account"

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 20, 14, 16)
        self._layout.setSpacing(7)

        self._build_brand()
        self._layout.addSpacing(22)

        self._overview_label = self._section_label("OVERVIEW")
        self._layout.addWidget(self._overview_label)
        self._buttons: dict[str, QPushButton] = {}
        self._add_navigation_button("dashboard", "Dashboard")

        self._layout.addSpacing(8)
        self._care_label = self._section_label("MY CARE")
        self._layout.addWidget(self._care_label)
        for route, label in self._ITEMS[1:]:
            self._add_navigation_button(route, label)

        self._layout.addStretch(1)
        self._build_user_context()
        self._layout.addSpacing(8)

        self.logout_button = QPushButton("Logout")
        self.logout_button.setObjectName("logoutButton")
        self.logout_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_button.setToolTip("Sign out of ClinicCare")
        apply_line_icon(
            self.logout_button,
            "logout",
            "#a8c5d2",
            size=19,
            active_color="#ffffff",
            accessible_name="Log out",
        )
        self.logout_button.clicked.connect(self.logout_requested)
        self._layout.addWidget(self.logout_button)

        self.set_compact(False)

    @property
    def is_compact(self) -> bool:
        return self._compact

    def _build_brand(self) -> None:
        self._brand_row = QWidget()
        brand_layout = QHBoxLayout(self._brand_row)
        brand_layout.setContentsMargins(4, 0, 2, 0)
        brand_layout.setSpacing(11)

        self._brand_mark = QLabel("C")
        self._brand_mark.setObjectName("sidebarBrandMark")
        self._brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._brand_mark.setFixedSize(40, 40)
        self._brand_mark.setAccessibleName("ClinicCare")
        brand_layout.addWidget(self._brand_mark)

        self._brand_text = QWidget()
        brand_text_layout = QVBoxLayout(self._brand_text)
        brand_text_layout.setContentsMargins(0, 1, 0, 0)
        brand_text_layout.setSpacing(0)
        self._brand_label = QLabel("ClinicCare")
        self._brand_label.setObjectName("brandLabel")
        self._brand_subtitle = QLabel("Patient Portal")
        self._brand_subtitle.setObjectName("sidebarSubtitle")
        brand_text_layout.addWidget(self._brand_label)
        brand_text_layout.addWidget(self._brand_subtitle)
        brand_layout.addWidget(self._brand_text, 1)
        self._layout.addWidget(self._brand_row)

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sidebarSectionLabel")
        return label

    def _add_navigation_button(self, route: str, label: str) -> None:
        button = QPushButton(label)
        button.setObjectName("navButton")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAccessibleName(label)
        button.setToolTip(label)
        button.setIconSize(QSize(19, 19))
        apply_line_icon(
            button,
            self._ICONS[route],
            "#a8c5d2",
            size=19,
            active_color="#ffffff",
            selected_color="#ffffff",
        )
        button.clicked.connect(
            lambda _checked=False, key=route: self.navigation_requested.emit(key)
        )
        self._layout.addWidget(button)
        self._buttons[route] = button

    def _build_user_context(self) -> None:
        self._user_row = QFrame()
        self._user_row.setObjectName("sidebarUser")
        self._user_row.setAccessibleName("Signed-in patient")
        user_layout = QHBoxLayout(self._user_row)
        user_layout.setContentsMargins(5, 8, 3, 7)
        user_layout.setSpacing(10)

        self._avatar = QFrame()
        self._avatar.setObjectName("userAvatar")
        self._avatar.setFixedSize(38, 38)
        avatar_layout = QVBoxLayout(self._avatar)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        self._avatar_text = QLabel("P")
        self._avatar_text.setObjectName("userAvatarText")
        self._avatar_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_layout.addWidget(self._avatar_text)
        user_layout.addWidget(self._avatar)

        self._user_text = QWidget()
        user_text_layout = QVBoxLayout(self._user_text)
        user_text_layout.setContentsMargins(0, 0, 0, 0)
        user_text_layout.setSpacing(1)
        self._user_name_label = QLabel(self._user_name)
        self._user_name_label.setObjectName("sidebarUserName")
        self._user_name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._user_role_label = QLabel(self._user_role)
        self._user_role_label.setObjectName("sidebarUserRole")
        user_text_layout.addWidget(self._user_name_label)
        user_text_layout.addWidget(self._user_role_label)
        user_layout.addWidget(self._user_text, 1)
        self._layout.addWidget(self._user_row)

    @staticmethod
    def _initials(name: str) -> str:
        words = [word for word in name.strip().split() if word]
        if not words:
            return "P"
        if len(words) == 1:
            return words[0][0].upper()
        return f"{words[0][0]}{words[-1][0]}".upper()

    def set_user(self, user: Mapping[str, Any] | None) -> None:
        """Show the authenticated patient's identity in the sidebar footer."""

        data = user or {}
        name = str(data.get("full_name") or data.get("username") or "Patient").strip()
        role_value = str(data.get("role") or "PATIENT").strip()
        role = role_value.replace("_", " ").title()
        self._user_name = name or "Patient"
        self._user_role = f"{role} account" if role else "Patient account"
        self._user_name_label.setText(self._user_name)
        self._user_role_label.setText(self._user_role)
        self._avatar_text.setText(self._initials(self._user_name))
        context = f"Signed in as {self._user_name}, {self._user_role}"
        self._user_row.setAccessibleName(context)
        self._user_row.setToolTip(context)

    def clear_user(self) -> None:
        """Remove the previous patient's identity from the reusable shell."""

        self.set_user(None)

    def set_compact(self, compact: bool) -> None:
        """Collapse labels while retaining icons, tooltips, and accessible names."""

        compact = bool(compact)
        self._compact = compact
        self.setProperty("compact", compact)
        self.setFixedWidth(self.COMPACT_WIDTH if compact else self.EXPANDED_WIDTH)
        horizontal_margin = 10 if compact else 14
        self._layout.setContentsMargins(horizontal_margin, 20, horizontal_margin, 16)

        self._brand_text.setVisible(not compact)
        self._overview_label.setVisible(not compact)
        self._care_label.setVisible(not compact)
        self._user_text.setVisible(not compact)

        for route, label in self._ITEMS:
            button = self._buttons[route]
            button.setText("" if compact else label)
            button.setToolTip(label)
            button.setProperty("compact", compact)
            button.style().unpolish(button)
            button.style().polish(button)

        self.logout_button.setText("" if compact else "Logout")
        self.logout_button.setProperty("compact", compact)
        self.logout_button.style().unpolish(self.logout_button)
        self.logout_button.style().polish(self.logout_button)

        self.style().unpolish(self)
        self.style().polish(self)
        self.updateGeometry()

    def set_active(self, route: str) -> None:
        self._active_route = route
        for key, button in self._buttons.items():
            active = key == route
            button.setChecked(active)
            apply_line_icon(
                button,
                self._ICONS[key],
                "#ffffff" if active else "#a8c5d2",
                size=19,
                active_color="#ffffff",
                selected_color="#ffffff",
            )
