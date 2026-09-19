"""Patient dashboard screen."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.views.common import (
    BaseApiView,
    display_text,
    format_date,
    format_time,
    require_dict,
)
from frontend.widgets.stat_card import StatCard


class DashboardView(BaseApiView):
    appointment_requested = Signal(int)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._appointment_id: int | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        header = QHBoxLayout()
        self.greeting = QLabel("Hello")
        self.greeting.setObjectName("pageTitle")
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("secondaryButton")
        header.addWidget(self.greeting)
        header.addStretch()
        header.addWidget(self.refresh_button)
        root.addLayout(header)
        root.addWidget(self.loading)

        cards = QGridLayout()
        cards.setSpacing(14)
        self.appointments_card = StatCard("Appointments")
        self.records_card = StatCard("Medical Records")
        self.invoices_card = StatCard("Invoices")
        self.unpaid_card = StatCard("Unpaid Invoices")
        cards.addWidget(self.appointments_card, 0, 0)
        cards.addWidget(self.records_card, 0, 1)
        cards.addWidget(self.invoices_card, 0, 2)
        cards.addWidget(self.unpaid_card, 0, 3)
        root.addLayout(cards)

        title = QLabel("Upcoming Appointment")
        title.setObjectName("sectionTitle")
        root.addWidget(title)
        self.upcoming_card = QFrame()
        self.upcoming_card.setObjectName("contentCard")
        upcoming_layout = QGridLayout(self.upcoming_card)
        upcoming_layout.setContentsMargins(20, 18, 20, 18)
        upcoming_layout.setHorizontalSpacing(28)
        upcoming_layout.setVerticalSpacing(10)
        self.upcoming_values: dict[str, QLabel] = {}
        fields = (
            ("Doctor", "doctor"),
            ("Specialty", "specialty"),
            ("Clinic", "clinic"),
            ("Date", "date"),
            ("Start Time", "start"),
            ("End Time", "end"),
            ("Reason", "reason"),
            ("Status", "status"),
        )
        for index, (label, key) in enumerate(fields):
            label_widget = QLabel(label)
            label_widget.setObjectName("fieldLabel")
            value = QLabel("—")
            value.setWordWrap(True)
            row, pair = divmod(index, 2)
            column = pair * 2
            upcoming_layout.addWidget(label_widget, row, column)
            upcoming_layout.addWidget(value, row, column + 1)
            self.upcoming_values[key] = value
        self.details_button = QPushButton("View Details")
        self.details_button.setObjectName("primaryButton")
        upcoming_layout.addWidget(self.details_button, 4, 3)
        self.no_upcoming = QLabel("No upcoming appointments.")
        self.no_upcoming.setObjectName("emptyState")
        root.addWidget(self.upcoming_card)
        root.addWidget(self.no_upcoming)
        root.addStretch()

        self.refresh_button.clicked.connect(self.load)
        self.details_button.clicked.connect(self._open_appointment)
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
        self.greeting.setText(f"Hello, {display_text(data.get('patient_name'), 'Patient')}")
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
            "status": upcoming.get("status"),
        }
        for key, value in values.items():
            self.upcoming_values[key].setText(display_text(value))
        self.no_upcoming.hide()
        self.upcoming_card.show()

    def _open_appointment(self) -> None:
        if self._appointment_id is not None:
            self.appointment_requested.emit(self._appointment_id)

    def clear_data(self) -> None:
        self._appointment_id = None
        self.greeting.setText("Hello")
        for card in (
            self.appointments_card,
            self.records_card,
            self.invoices_card,
            self.unpaid_card,
        ):
            card.set_value("—")
        self.upcoming_card.hide()
        self.no_upcoming.show()
