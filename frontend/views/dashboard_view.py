"""Patient dashboard screen."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from frontend.api.api_client import ApiClient
from frontend.ui.icons import apply_line_icon
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
        apply_line_icon(
            self.refresh_button,
            "refresh",
            active_color="#0F766E",
            accessible_name="Refresh dashboard",
        )
        self.header.add_action(self.refresh_button)
        root.addWidget(self.header)
        root.addWidget(self.feedback)
        root.addWidget(self.loading)

        overview_title = QLabel("Care overview")
        overview_title.setObjectName("sectionTitle")
        root.addWidget(overview_title)

        self.cards = QGridLayout()
        self.cards.setHorizontalSpacing(14)
        self.cards.setVerticalSpacing(14)
        self.appointments_card = StatCard("Appointments", icon_name="calendar", tone="blue")
        self.records_card = StatCard("Medical Records", icon_name="medical", tone="violet")
        self.invoices_card = StatCard("Invoices", icon_name="invoice")
        self.unpaid_card = StatCard("Unpaid Invoices", icon_name="invoice", tone="amber")
        self._stat_cards = (
            self.appointments_card,
            self.records_card,
            self.invoices_card,
            self.unpaid_card,
        )
        root.addLayout(self.cards)

        upcoming_title = QLabel("Upcoming appointment")
        upcoming_title.setObjectName("sectionTitle")
        root.addWidget(upcoming_title)

        self.upcoming_card = QFrame()
        self.upcoming_card.setObjectName("appointmentCard")
        upcoming_layout = QGridLayout(self.upcoming_card)
        upcoming_layout.setContentsMargins(22, 20, 22, 20)
        upcoming_layout.setHorizontalSpacing(20)
        upcoming_layout.setVerticalSpacing(10)
        upcoming_layout.setColumnStretch(1, 1)
        upcoming_layout.setColumnStretch(3, 1)

        card_title = QLabel("Your next visit")
        card_title.setObjectName("sectionTitle")
        upcoming_layout.addWidget(card_title, 0, 0, 1, 3)
        self.status_badge = StatusBadge()
        upcoming_layout.addWidget(
            self.status_badge,
            0,
            3,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.upcoming_values: dict[str, QLabel] = {"status": self.status_badge}
        fields = (
            ("Doctor", "doctor"),
            ("Specialty", "specialty"),
            ("Clinic", "clinic"),
            ("Date", "date"),
            ("Start time", "start"),
            ("End time", "end"),
            ("Reason", "reason"),
        )
        for index, (label, key) in enumerate(fields):
            row, pair = divmod(index, 2)
            column = pair * 2
            label_widget = QLabel(label)
            label_widget.setObjectName("fieldLabel")
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
            icon="calendar",
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
        self.clear_data()

    def activate(self) -> None:
        self.load()

    def load(self) -> None:
        self.run_api_task(
            "dashboard",
            lambda: self.api_client.get("/api/v1/dashboard/me"),
            self._render,
            controls=(self.refresh_button,),
            loading_text="Loading dashboard…",
        )

    def _render(self, payload: object) -> None:
        data = require_dict(payload)
        patient_name = display_text(data.get("patient_name"), "Patient")
        self.header.set_title(f"Hello, {patient_name}")
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
        self.header.set_title("Hello")
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
