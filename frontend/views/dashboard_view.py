"""Patient dashboard screen."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from frontend.api.api_client import ApiClient
from frontend.core.i18n import get_i18n, t
from frontend.views.common import (
    BaseApiView,
    display_text,
    format_date,
    format_time,
    require_dict,
)
from frontend.widgets.empty_state import EmptyState
from frontend.widgets.page_header import PageHeader
from frontend.widgets.stat_card import StatCard
from frontend.widgets.status_badge import StatusBadge


class DashboardView(BaseApiView):
    appointment_requested = Signal(int)
    route_requested = Signal(str)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._appointment_id: int | None = None
        self._stat_columns = 0
        self._patient_name = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        self.header = PageHeader(
            "Hello",
            "Here is an overview of your care and your next visit.",
        )
        self.greeting = self.header.title_label
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.setAccessibleName("Refresh dashboard")
        self.header.add_action(self.refresh_button)
        root.addWidget(self.header)
        root.addWidget(self.feedback)
        root.addWidget(self.loading)

        self.overview_title = QLabel("Care overview")
        self.overview_title.setObjectName("sectionTitle")
        root.addWidget(self.overview_title)

        self.cards = QGridLayout()
        self.cards.setHorizontalSpacing(14)
        self.cards.setVerticalSpacing(14)
        self.appointments_card = StatCard("Appointments", tone="blue")
        self.records_card = StatCard("Medical Records", tone="violet")
        self.invoices_card = StatCard("Invoices")
        self.unpaid_card = StatCard("Unpaid Invoices", tone="amber")
        self._stat_cards = (
            self.appointments_card,
            self.records_card,
            self.invoices_card,
            self.unpaid_card,
        )
        root.addLayout(self.cards)

        self.upcoming_title = QLabel("Upcoming appointment")
        self.upcoming_title.setObjectName("sectionTitle")
        root.addWidget(self.upcoming_title)

        self.upcoming_card = QFrame()
        self.upcoming_card.setObjectName("appointmentCard")
        upcoming_layout = QGridLayout(self.upcoming_card)
        upcoming_layout.setContentsMargins(22, 20, 22, 20)
        upcoming_layout.setHorizontalSpacing(20)
        upcoming_layout.setVerticalSpacing(10)
        upcoming_layout.setColumnStretch(1, 1)
        upcoming_layout.setColumnStretch(3, 1)

        self.card_title = QLabel("Your next visit")
        self.card_title.setObjectName("sectionTitle")
        upcoming_layout.addWidget(self.card_title, 0, 0, 1, 3)
        self.status_badge = StatusBadge()
        upcoming_layout.addWidget(
            self.status_badge,
            0,
            3,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.upcoming_values: dict[str, QLabel] = {"status": self.status_badge}
        self._field_labels: dict[str, QLabel] = {}
        fields = (
            ("field_doctor", "doctor"),
            ("field_specialty", "specialty"),
            ("field_clinic", "clinic"),
            ("field_date", "date"),
            ("field_start_time", "start"),
            ("field_end_time", "end"),
            ("field_reason", "reason"),
        )
        for index, (label_key, key) in enumerate(fields):
            row, pair = divmod(index, 2)
            column = pair * 2
            label_widget = QLabel(t(label_key))
            label_widget.setObjectName("fieldLabel")
            self._field_labels[key] = label_widget
            value = QLabel("—")
            value.setObjectName("fieldValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            upcoming_layout.addWidget(label_widget, row + 1, column)
            upcoming_layout.addWidget(value, row + 1, column + 1)
            self.upcoming_values[key] = value

        self.details_button = QPushButton("View details")
        self.details_button.setObjectName("primaryButton")
        self.details_button.setAccessibleName("View upcoming appointment details")
        upcoming_layout.addWidget(
            self.details_button,
            5,
            3,
            alignment=Qt.AlignmentFlag.AlignRight,
        )

        self.no_upcoming = EmptyState(
            "No upcoming appointments",
            "Your next confirmed visit will appear here when one is scheduled.",
            action_text="Refresh",
        )
        self.no_upcoming.setMinimumHeight(178)
        root.addWidget(self.upcoming_card)
        root.addWidget(self.no_upcoming)
        root.addStretch()

        self.refresh_button.clicked.connect(self.load)
        self.details_button.clicked.connect(self._open_appointment)
        self.no_upcoming.action_requested.connect(self.load)
        self.appointments_card.clicked.connect(lambda: self.route_requested.emit("appointments"))
        self.records_card.clicked.connect(lambda: self.route_requested.emit("medical_history"))
        self.invoices_card.clicked.connect(lambda: self.route_requested.emit("invoice_history"))
        self.unpaid_card.clicked.connect(lambda: self.route_requested.emit("invoice_history"))
        self._reflow_stats(force=True)

        get_i18n().language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()
        self.clear_data()

    def retranslate_ui(self) -> None:
        """Update all text in DashboardView according to current language."""
        if self._patient_name:
            self.header.set_title(t("dashboard_greeting", name=self._patient_name))
        else:
            self.header.set_title(t("dashboard_greeting_default"))
        self.header.set_subtitle(t("dashboard_subtitle"))
        self.refresh_button.setText(t("btn_refresh"))
        self.overview_title.setText(t("care_overview"))
        self.appointments_card.set_title(t("stat_appointments"))
        self.records_card.set_title(t("stat_medical_records"))
        self.invoices_card.set_title(t("stat_invoices"))
        self.unpaid_card.set_title(t("stat_unpaid_invoices"))
        self.upcoming_title.setText(t("upcoming_appointment"))
        self.card_title.setText(t("next_visit"))
        self.details_button.setText(t("btn_view_details"))
        self.no_upcoming.set_title(t("no_upcoming_title"))
        self.no_upcoming.set_description(t("no_upcoming_desc"))
        self.no_upcoming.set_action(t("btn_refresh"))

        field_key_map = {
            "doctor": "field_doctor",
            "specialty": "field_specialty",
            "clinic": "field_clinic",
            "date": "field_date",
            "start": "field_start_time",
            "end": "field_end_time",
            "reason": "field_reason",
        }
        for key, lbl in self._field_labels.items():
            if key in field_key_map:
                lbl.setText(t(field_key_map[key]))

    def activate(self) -> None:
        self.load()

    def load(self) -> None:
        self.run_api_task(
            "dashboard",
            lambda: self.api_client.get("/api/v1/dashboard/me"),
            self._render,
            controls=(self.refresh_button,),
            loading_text=t("loading"),
        )

    def _render(self, payload: object) -> None:
        data = require_dict(payload)
        self._patient_name = display_text(data.get("patient_name"), "")
        self.header.set_title(
            t("dashboard_greeting", name=self._patient_name)
            if self._patient_name
            else t("dashboard_greeting_default")
        )
        self.appointments_card.set_value(data.get("total_appointments", 0))
        self.records_card.set_value(data.get("total_medical_records", 0))
        self.invoices_card.set_value(data.get("total_invoices", 0))
        self.unpaid_card.set_value(data.get("unpaid_invoices", 0))

        upcoming = data.get("upcoming_appointment")
        if not isinstance(upcoming, dict):
            self._appointment_id = None
            self.upcoming_card.hide()
            self.no_upcoming.show()
            return

        doctor = upcoming.get("doctor") or {}
        clinic = upcoming.get("clinic") or {}
        self._appointment_id = int(upcoming["appointment_id"])
        values: dict[str, Any] = {
            "doctor": doctor.get("full_name"),
            "specialty": doctor.get("specialty"),
            "clinic": clinic.get("clinic_name"),
            "date": format_date(upcoming.get("appointment_date")),
            "start": format_time(upcoming.get("start_time")),
            "end": format_time(upcoming.get("end_time")),
            "reason": upcoming.get("reason"),
        }
        for key, value in values.items():
            self.upcoming_values[key].setText(display_text(value))
        self.status_badge.set_status(upcoming.get("status"))
        self.no_upcoming.hide()
        self.upcoming_card.show()

    def _open_appointment(self) -> None:
        if self._appointment_id is not None:
            self.appointment_requested.emit(self._appointment_id)

    def _reflow_stats(self, *, force: bool = False) -> None:
        columns = 4 if self.width() >= 1000 else 2
        if not force and columns == self._stat_columns:
            return
        self._stat_columns = columns
        for card in self._stat_cards:
            self.cards.removeWidget(card)
        for index, card in enumerate(self._stat_cards):
            self.cards.addWidget(card, index // columns, index % columns)
        for column in range(4):
            self.cards.setColumnStretch(column, 1 if column < columns else 0)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reflow_stats()

    def clear_data(self) -> None:
        self._appointment_id = None
        self._patient_name = ""
        self.header.set_title(t("dashboard_greeting_default"))
        self.feedback.clear()
        for card in self._stat_cards:
            card.set_value("—")
        for key, value in self.upcoming_values.items():
            if key == "status":
                self.status_badge.set_status(None)
            else:
                value.setText("—")
        self.upcoming_card.hide()
        self.no_upcoming.hide()
