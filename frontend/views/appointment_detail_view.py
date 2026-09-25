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
from frontend.core.i18n import get_i18n, t
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
            t("appointment_detail_title"),
            t("appointment_detail_subtitle"),
            show_back=True,
        )
        self.back_button = self.header.back_button
        self.title = self.header.title_label
        self.medical_button = QPushButton(t("btn_medical_result"))
        self.medical_button.setObjectName("secondaryButton")
        self.invoice_button = QPushButton(t("btn_invoice"))
        self.invoice_button.setObjectName("primaryButton")

        self.reschedule_button = QPushButton(t("btn_reschedule"))
        self.reschedule_button.setObjectName("secondaryButton")
        self.cancel_button = QPushButton(t("btn_cancel"))
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.setStyleSheet("color: #dc2626; border-color: #fecaca;")

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
        self._field_labels: dict[str, QLabel] = {}
        self._section_title_labels: dict[str, QLabel] = {}

        content_layout.addWidget(
            self._section(
                "sec_appointment_summary",
                [
                    ("field_date", "date"),
                    ("field_start_time", "start_time"),
                    ("field_end_time", "end_time"),
                    ("field_status", "status"),
                    ("field_reason", "reason"),
                ],
            )
        )
        content_layout.addWidget(
            self._section(
                "field_doctor",
                [
                    ("field_doctor", "doctor_name"),
                    ("field_specialty", "specialty"),
                    ("license_number", "license"),
                    ("phone", "doctor_phone"),
                    ("email", "doctor_email"),
                ],
            )
        )
        content_layout.addWidget(
            self._section(
                "field_clinic",
                [
                    ("field_clinic", "clinic_name"),
                    ("address", "clinic_address"),
                    ("phone", "clinic_phone"),
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

        get_i18n().language_changed.connect(self.retranslate_ui)
        self.clear_data()

    def retranslate_ui(self) -> None:
        """Update all text in AppointmentDetailView according to current language."""
        self.header.set_title(t("appointment_detail_title"))
        if self._appointment_id is not None:
            self.header.set_subtitle(f"#{self._appointment_id:06d}")
        else:
            self.header.set_subtitle(t("appointment_detail_subtitle"))
        self.reschedule_button.setText(t("btn_reschedule"))
        self.cancel_button.setText(t("btn_cancel"))
        self.medical_button.setText(t("btn_medical_result"))
        self.invoice_button.setText(t("btn_invoice"))

        for sec_key, lbl in self._section_title_labels.items():
            lbl.setText(t(sec_key))

        field_key_map = {
            "date": "field_date",
            "start_time": "field_start_time",
            "end_time": "field_end_time",
            "status": "field_status",
            "reason": "field_reason",
            "doctor_name": "field_doctor",
            "specialty": "field_specialty",
            "license": "license_number",
            "doctor_phone": "phone",
            "doctor_email": "email",
            "clinic_name": "field_clinic",
            "clinic_address": "address",
            "clinic_phone": "phone",
        }
        for key, lbl in self._field_labels.items():
            if key in field_key_map:
                lbl.setText(t(field_key_map[key]))

    def _section(self, title_key: str, fields: list[tuple[str, str]]) -> QFrame:
        card = QFrame()
        card.setObjectName("infoCard")
        layout = QGridLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setHorizontalSpacing(28)
        layout.setVerticalSpacing(12)
        section_title = QLabel(t(title_key))
        section_title.setObjectName("sectionTitle")
        self._section_title_labels[title_key] = section_title
        layout.addWidget(section_title, 0, 0, 1, 2)
        for row, (label_key, key) in enumerate(fields, start=1):
            label_widget = QLabel(t(label_key))
            label_widget.setObjectName("fieldLabel")
            label_widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self._field_labels[key] = label_widget
            value: QLabel
            if key == "status":
                value = StatusBadge()
                value.setMaximumWidth(180)
            else:
                value = QLabel("—")
                value.setObjectName("fieldValue")
                value.setWordWrap(True)
                value.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                    | Qt.TextInteractionFlag.TextSelectableByKeyboard
                )
                value.setAccessibleName(t(label_key))
            layout.addWidget(label_widget, row, 0, Qt.AlignmentFlag.AlignTop)
            layout.addWidget(value, row, 1, Qt.AlignmentFlag.AlignTop)
            self.values[key] = value
        layout.setColumnMinimumWidth(0, 142)
        layout.setColumnStretch(1, 1)
        return card

    def activate(self, appointment_id: int) -> None:
        self.invalidate_pending()
        self.clear_data()
        self._appointment_id = appointment_id
        self.header.set_subtitle(f"#{appointment_id:06d}")
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
            loading_text=t("loading"),
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
        self.header.set_subtitle(t("appointment_detail_subtitle"))
        for value in self.values.values():
            if isinstance(value, StatusBadge):
                value.set_status(None)
            else:
                value.setText("—")
        self.medical_button.hide()
        self.invoice_button.hide()
        self.reschedule_button.hide()
        self.cancel_button.hide()
