"""Primary authenticated navigation and signed-in patient context."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from frontend.core.i18n import get_i18n, t
from frontend.widgets.app_sidebar import AppSidebar, NavigationItem


class Sidebar(AppSidebar):
    """Persistent navigation that can collapse without losing accessibility."""

    navigation_requested = Signal(str)
    logout_requested = Signal()

    EXPANDED_WIDTH = 232
    COMPACT_WIDTH = 78

    _ITEMS = (
        ("dashboard", "Dashboard"),
        ("booking", "Book Appointment"),
        ("appointments", "Appointments"),
        ("profile", "My Profile"),
        ("medical_history", "Medical History"),
        ("invoice_history", "Invoice History"),
    )
    _ICONS = {
        "dashboard": "dashboard",
        "booking": "calendar",
        "profile": "user",
        "appointments": "calendar",
        "medical_history": "medical",
        "invoice_history": "invoice",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        self._user_name = "Patient"
        self._role_value = "PATIENT"
        self._user_role = t("nav_patient_account")
        super().__init__(
            (
                NavigationItem("dashboard", "Dashboard", "dashboard", "OVERVIEW"),
                NavigationItem("booking", "Book Appointment", "calendar", "MY CARE"),
                NavigationItem("appointments", "Appointments", "calendar"),
                NavigationItem("profile", "My Profile", "user"),
                NavigationItem("medical_history", "Medical History", "medical"),
                NavigationItem("invoice_history", "Invoice History", "invoice"),
            ),
            parent,
            brand_subtitle="Cổng bệnh nhân",
            logout_text="Logout",
            show_language_selector=True,
        )
        self._overview_label = self._section_labels[0]
        self._care_label = self._section_labels[1]
        self.setAccessibleName(t("a11y_patient_navigation"))
        get_i18n().language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    _ROUTE_TO_KEY = {
        "dashboard": "nav_dashboard",
        "booking": "nav_booking",
        "appointments": "nav_appointments",
        "profile": "nav_profile",
        "medical_history": "nav_medical_history",
        "invoice_history": "nav_invoice_history",
    }

    def retranslate_ui(self) -> None:
        """Update navigation labels based on active language."""
        self.setAccessibleName(t("a11y_patient_navigation"))
        self._overview_label.setText(t("nav_overview"))
        self._care_label.setText(t("nav_my_care"))
        for route, key in self._ROUTE_TO_KEY.items():
            if route in self._buttons:
                label = t(key)
                button = self._buttons[route]
                button.setAccessibleName(label)
                button.setToolTip(label)
                button.setText("" if self._compact else label)
        self.logout_button.setText("" if self._compact else t("nav_logout"))
        self.logout_button.setToolTip(t("nav_logout"))
        self.logout_button.setAccessibleName(
            "Log out" if get_i18n().current_language == "en" else t("nav_logout")
        )
        if self._role_value == "PATIENT":
            self._user_role = t("nav_patient_account")
            self._user_role_label.setText(self._user_role)
        self._update_user_context()

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
        name = str(
            data.get("full_name") or data.get("username") or t("patient_default_name")
        ).strip()
        self._role_value = str(data.get("role") or "PATIENT").strip().upper()
        role = self._role_value.replace("_", " ").title()
        self._user_name = name or t("patient_default_name")
        self._user_role = (
            t("nav_patient_account")
            if self._role_value == "PATIENT"
            else (f"{role} account" if role else t("nav_patient_account"))
        )
        self._user_name_label.setText(self._user_name)
        self._user_role_label.setText(self._user_role)
        self._avatar_text.setText(self._initials(self._user_name))
        self._update_user_context()

    def _update_user_context(self) -> None:
        context = t(
            "a11y_signed_in_as",
            name=self._user_name,
            role=self._user_role,
        )
        self._user_row.setAccessibleName(context)
        self._user_row.setToolTip(context)

    def clear_user(self) -> None:
        """Remove the previous patient's identity from the reusable shell."""

        self.set_user(None)

    def set_active(self, route: str) -> None:
        self._active_route = route
        for key, button in self._buttons.items():
            button.setChecked(key == route)
