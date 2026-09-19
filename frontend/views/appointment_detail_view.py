"""Read-only appointment details."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
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


class AppointmentDetailView(BaseApiView):
    back_requested = Signal()
    medical_record_requested = Signal(int)
    invoice_requested = Signal(int)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._appointment_id: int | None = None
        self._medical_record_id: int | None = None
        self._invoice_id: int | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        header = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("secondaryButton")
        title = QLabel("Appointment Detail")
        title.setObjectName("pageTitle")
        header.addWidget(self.back_button)
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)
        root.addWidget(self.loading)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(16)
        self.values: dict[str, QLabel] = {}
        content_layout.addWidget(
            self._section(
                "Appointment",
                [
                    ("Appointment ID", "appointment_id"),
                    ("Date", "date"),
                    ("Start Time", "start_time"),
                    ("End Time", "end_time"),
                    ("Status", "status"),
                    ("Reason", "reason"),
                ],
            )
        )
        content_layout.addWidget(
            self._section(
                "Doctor",
                [
                    ("Doctor Name", "doctor_name"),
                    ("Specialty", "specialty"),
                    ("License Number", "license"),
                    ("Doctor Phone", "doctor_phone"),
                    ("Doctor Email", "doctor_email"),
                ],
            )
        )
        content_layout.addWidget(
            self._section(
                "Clinic",
                [
                    ("Clinic Name", "clinic_name"),
                    ("Clinic Address", "clinic_address"),
                    ("Clinic Phone", "clinic_phone"),
                ],
            )
        )

        actions = QHBoxLayout()
        actions.addStretch()
        self.medical_button = QPushButton("View Medical Result")
        self.medical_button.setObjectName("secondaryButton")
        self.invoice_button = QPushButton("View Invoice")
        self.invoice_button.setObjectName("primaryButton")
        actions.addWidget(self.medical_button)
        actions.addWidget(self.invoice_button)
        content_layout.addLayout(actions)
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self.back_button.clicked.connect(self.back_requested)
        self.medical_button.clicked.connect(self._open_medical)
        self.invoice_button.clicked.connect(self._open_invoice)
        self.clear_data()

    def _section(self, title: str, fields: list[tuple[str, str]]) -> QFrame:
        card = QFrame()
        card.setObjectName("contentCard")
        layout = QGridLayout(card)
        layout.setContentsMargins(22, 18, 22, 18)
        section_title = QLabel(title)
        section_title.setObjectName("sectionTitle")
        layout.addWidget(section_title, 0, 0, 1, 4)
        for index, (label, key) in enumerate(fields):
            row, pair = divmod(index, 2)
            label_widget = QLabel(label)
            label_widget.setObjectName("fieldLabel")
            value = QLabel("—")
            value.setWordWrap(True)
            if key in {"reason", "clinic_address"}:
                value.setMinimumHeight(42)
            layout.addWidget(label_widget, row + 1, pair * 2)
            layout.addWidget(value, row + 1, pair * 2 + 1)
            self.values[key] = value
        return card

    def activate(self, appointment_id: int) -> None:
        # A previous detail request may still be running if the user navigated
        # away quickly.  Move to a new generation so its response cannot render
        # over the newly selected appointment.
        self.invalidate_pending()
        self.clear_data()
        self._appointment_id = appointment_id
        self.load()

    def load(self) -> None:
        if self._appointment_id is None:
            return
        appointment_id = self._appointment_id
        self.run_api_task(
            "appointment-detail",
            lambda: self.api_client.get(f"/api/v1/appointments/me/{appointment_id}"),
            self._render,
            controls=(self.back_button, self.medical_button, self.invoice_button),
            loading_text="Loading appointment…",
        )

    def _render(self, payload: object) -> None:
        data = require_dict(payload)
        doctor = data.get("doctor") or {}
        clinic = data.get("clinic") or {}
        values: dict[str, Any] = {
            "appointment_id": data.get("appointment_id"),
            "date": format_date(data.get("appointment_date")),
            "start_time": format_time(data.get("start_time")),
            "end_time": format_time(data.get("end_time")),
            "status": data.get("status"),
            "reason": data.get("reason"),
            "doctor_name": doctor.get("full_name"),
            "specialty": doctor.get("specialty"),
            "license": doctor.get("license_number"),
            "doctor_phone": doctor.get("phone"),
            "doctor_email": doctor.get("email"),
            "clinic_name": clinic.get("clinic_name"),
            "clinic_address": clinic.get("address"),
            "clinic_phone": clinic.get("phone"),
        }
        for key, value in values.items():
            self.values[key].setText(display_text(value))
        medical_id = data.get("medical_record_id")
        invoice_id = data.get("invoice_id")
        self._medical_record_id = int(medical_id) if medical_id is not None else None
        self._invoice_id = int(invoice_id) if invoice_id is not None else None
        self.medical_button.setVisible(self._medical_record_id is not None)
        self.invoice_button.setVisible(self._invoice_id is not None)

    def _open_medical(self) -> None:
        if self._medical_record_id is not None:
            self.medical_record_requested.emit(self._medical_record_id)

    def _open_invoice(self) -> None:
        if self._invoice_id is not None:
            self.invoice_requested.emit(self._invoice_id)

    def clear_data(self) -> None:
        self._appointment_id = None
        self._medical_record_id = None
        self._invoice_id = None
        for value in self.values.values():
            value.setText("—")
        self.medical_button.hide()
        self.invoice_button.hide()
