"""Read-only appointment details."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.ui.icons import apply_line_icon
from frontend.views.common import (
    BaseApiView,
    display_text,
    format_date,
    format_time,
    require_dict,
)
from frontend.widgets.page_header import PageHeader
from frontend.widgets.status_badge import StatusBadge


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
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(14)

        self.header = PageHeader(
            "Appointment Detail",
            "Review the visit, care provider, and clinic information.",
            show_back=True,
        )
        self.back_button = self.header.back_button
        self.title = self.header.title_label
        self.medical_button = QPushButton("Medical result")
        self.medical_button.setObjectName("secondaryButton")
        apply_line_icon(
            self.medical_button,
            "medical",
            active_color="#0F766E",
            accessible_name="View medical result",
        )
        self.invoice_button = QPushButton("Invoice")
        self.invoice_button.setObjectName("primaryButton")
        apply_line_icon(
            self.invoice_button,
            "invoice",
            "#FFFFFF",
            active_color="#FFFFFF",
            accessible_name="View invoice",
        )
        from frontend.core.i18n import get_i18n, t

        self.reschedule_button = QPushButton(t("btn_reschedule"))
        self.reschedule_button.setObjectName("secondaryButton")
        self.cancel_button = QPushButton(t("btn_cancel"))
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.setStyleSheet("color: #dc2626; border-color: #fecaca;")
        get_i18n().language_changed.connect(
            lambda _: (
                self.reschedule_button.setText(t("btn_reschedule")),
                self.cancel_button.setText(t("btn_cancel")),
            )
        )

        self.header.add_action(self.reschedule_button)
        self.header.add_action(self.cancel_button)
        self.header.add_action(self.medical_button)
        self.header.add_action(self.invoice_button)
        root.addWidget(self.header)
        root.addWidget(self.feedback)
        root.addWidget(self.loading)

        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAccessibleName("Appointment information")
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 2, 8, 4)
        content_layout.setSpacing(16)
        self.values: dict[str, QLabel] = {}
        content_layout.addWidget(
            self._section(
                "Appointment",
                [
                    ("Appointment ID", "appointment_id"),
                    ("Date", "date"),
                    ("Start time", "start_time"),
                    ("End time", "end_time"),
                    ("Status", "status"),
                    ("Reason for visit", "reason"),
                ],
            )
        )
        content_layout.addWidget(
            self._section(
                "Care provider",
                [
                    ("Doctor", "doctor_name"),
                    ("Specialty", "specialty"),
                    ("License number", "license"),
                    ("Phone", "doctor_phone"),
                    ("Email", "doctor_email"),
                ],
            )
        )
        content_layout.addWidget(
            self._section(
                "Clinic",
                [
                    ("Clinic", "clinic_name"),
                    ("Address", "clinic_address"),
                    ("Phone", "clinic_phone"),
                ],
            )
        )
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self.header.back_requested.connect(self.back_requested.emit)
        self.medical_button.clicked.connect(self._open_medical)
        self.invoice_button.clicked.connect(self._open_invoice)
        self.reschedule_button.clicked.connect(self._open_reschedule)
        self.cancel_button.clicked.connect(self._open_cancel)
        self._current_appointment_data: dict[str, Any] | None = None
        self.clear_data()

    def _section(self, title: str, fields: list[tuple[str, str]]) -> QFrame:
        card = QFrame()
        card.setObjectName("infoCard")
        layout = QGridLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setHorizontalSpacing(28)
        layout.setVerticalSpacing(12)
        section_title = QLabel(title)
        section_title.setObjectName("sectionTitle")
        layout.addWidget(section_title, 0, 0, 1, 2)
        for row, (label, key) in enumerate(fields, start=1):
            label_widget = QLabel(label)
            label_widget.setObjectName("fieldLabel")
            label_widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            value: QLabel
            if key == "status":
                value = StatusBadge()
                value.setAccessibleName(f"{label}: not available")
                value.setMaximumWidth(180)
            else:
                value = QLabel("—")
                value.setObjectName("fieldValue")
                value.setWordWrap(True)
                value.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                    | Qt.TextInteractionFlag.TextSelectableByKeyboard
                )
                value.setAccessibleName(label)
            layout.addWidget(label_widget, row, 0, Qt.AlignmentFlag.AlignTop)
            layout.addWidget(value, row, 1, Qt.AlignmentFlag.AlignTop)
            self.values[key] = value
        layout.setColumnMinimumWidth(0, 142)
        layout.setColumnStretch(1, 1)
        return card

    def activate(self, appointment_id: int) -> None:
        # A previous detail request may still be running if the user navigated
        # away quickly. Move to a new generation so its response cannot render
        # over the newly selected appointment.
        self.invalidate_pending()
        self.clear_data()
        self._appointment_id = appointment_id
        self.header.set_subtitle(f"Appointment #{appointment_id:06d}")
        self.load()

    def load(self) -> None:
        if self._appointment_id is None:
            return
        appointment_id = self._appointment_id
        self.run_api_task(
            "appointment-detail",
            lambda: self.api_client.get(f"/api/v1/appointments/me/{appointment_id}"),
            self._render,
            controls=(
                self.medical_button,
                self.invoice_button,
                self.reschedule_button,
                self.cancel_button,
            ),
            loading_text="Loading appointment…",
        )

    def _render(self, payload: object) -> None:
        data = require_dict(payload)
        self._current_appointment_data = data
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
            label = self.values[key]
            if isinstance(label, StatusBadge):
                label.set_status(value)
            else:
                label.setText(display_text(value))
        medical_id = data.get("medical_record_id")
        invoice_id = data.get("invoice_id")
        self._medical_record_id = int(medical_id) if medical_id is not None else None
        self._invoice_id = int(invoice_id) if invoice_id is not None else None
        self.medical_button.setVisible(self._medical_record_id is not None)
        self.invoice_button.setVisible(self._invoice_id is not None)

        status_val = data.get("status")
        can_modify = status_val in ("PENDING", "CONFIRMED")
        self.reschedule_button.setVisible(can_modify)
        self.cancel_button.setVisible(can_modify)

    def _open_medical(self) -> None:
        if self._medical_record_id is not None:
            self.medical_record_requested.emit(self._medical_record_id)

    def _open_invoice(self) -> None:
        if self._invoice_id is not None:
            self.invoice_requested.emit(self._invoice_id)

    def _open_reschedule(self) -> None:
        if not self._current_appointment_data:
            return
        from frontend.views.reschedule_dialog import RescheduleAppointmentDialog

        dialog = RescheduleAppointmentDialog(self.api_client, self._current_appointment_data, self)
        dialog.appointment_rescheduled.connect(lambda _: self.load())
        dialog.exec()

    def _open_cancel(self) -> None:
        if not self._current_appointment_data:
            return
        from frontend.views.cancel_dialog import CancelAppointmentDialog

        dialog = CancelAppointmentDialog(self.api_client, self._current_appointment_data, self)
        dialog.appointment_canceled.connect(lambda _: self.load())
        dialog.exec()

    def clear_data(self) -> None:
        self._appointment_id = None
        self._medical_record_id = None
        self._invoice_id = None
        self._current_appointment_data = None
        self.header.set_subtitle("Review the visit, care provider, and clinic information.")
        for value in self.values.values():
            if isinstance(value, StatusBadge):
                value.set_status(None)
            else:
                value.setText("—")
        self.medical_button.hide()
        self.invoice_button.hide()
        self.reschedule_button.hide()
        self.cancel_button.hide()
