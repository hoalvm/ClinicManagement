"""Modal dialog for selecting a new date and available slot to reschedule an appointment."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient, ApiError
from frontend.core.i18n import get_i18n, t
from frontend.views.common import format_date, format_time_range
from frontend.widgets.async_task_controller import AsyncTaskController
from frontend.widgets.calendar_dialog import CalendarDialog
from frontend.widgets.combo_box import ChevronComboBox


class RescheduleAppointmentDialog(QDialog):
    """Accessible reschedule dialog with real-time slot checking."""

    appointment_rescheduled = Signal(dict)
    session_expired = Signal()

    def __init__(
        self,
        api_client: ApiClient,
        appointment: dict[str, Any],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self.appointment = appointment
        self.appointment_id = appointment.get("appointment_id", 0)
        doctor_info = appointment.get("doctor", {})
        self.doctor_id = doctor_info.get("doctor_id", 0)
        self._tasks = AsyncTaskController(self)
        self.finished.connect(lambda _result: self._tasks.invalidate())

        self.setWindowTitle(t("reschedule_dialog_title"))
        self.setModal(True)
        self.setMinimumWidth(500)
        self.resize(540, 560)
        self.setProperty("uiSurface", "dialog")
        get_i18n().language_changed.connect(self.retranslate_ui)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.title_label = QLabel(t("reschedule_dialog_title"))
        self.title_label.setObjectName("sectionTitle")
        layout.addWidget(self.title_label)

        doc_name = doctor_info.get("full_name", "Bác sĩ")
        spec_name = doctor_info.get("specialty", "")
        curr_date = format_date(appointment.get("appointment_date"))
        curr_time = format_time_range(
            appointment.get("start_time"),
            appointment.get("end_time"),
        )

        self._summary_doctor_name = doc_name
        self._summary_specialty_name = spec_name
        self._summary_date = curr_date
        self._summary_time = curr_time

        curr_card = QFrame()
        curr_card.setObjectName("successSummaryCard")
        card_layout = QVBoxLayout(curr_card)
        card_layout.setSpacing(4)
        self.summary_doctor_label = QLabel()
        self.summary_doctor_label.setObjectName("successSummaryText")
        self.summary_doctor_label.setWordWrap(True)
        card_layout.addWidget(self.summary_doctor_label)

        self.summary_current_label = QLabel()
        self.summary_current_label.setObjectName("successSummaryStrongText")
        self.summary_current_label.setWordWrap(True)
        card_layout.addWidget(self.summary_current_label)
        layout.addWidget(curr_card)
        self._update_summary_labels()

        # Doctor selection
        self.lbl_doctor = QLabel(t("reschedule_choose_doctor", default="Bác sĩ khám:"))
        self.lbl_doctor.setObjectName("fieldLabel")
        layout.addWidget(self.lbl_doctor)

        self.doctor_combo = ChevronComboBox()
        self.doctor_combo.setAccessibleName(self.lbl_doctor.text())
        layout.addWidget(self.doctor_combo)

        # New Date selection
        self.lbl_date = QLabel(t("reschedule_new_date", default="Ngày khám mới:"))
        self.lbl_date.setObjectName("fieldLabel")
        layout.addWidget(self.lbl_date)

        date_row = QHBoxLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setDate(QDate.currentDate().addDays(1))
        self.date_edit.setMinimumDate(QDate.currentDate())
        self.date_edit.setMaximumDate(QDate.currentDate().addDays(60))
        date_row.addWidget(self.date_edit, 1)

        self.open_cal_btn = QPushButton(t("btn_open_calendar", default="Chọn ngày"))
        self.open_cal_btn.setObjectName("secondaryButton")
        self.open_cal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_cal_btn.clicked.connect(self._open_calendar_dialog)
        date_row.addWidget(self.open_cal_btn)
        layout.addLayout(date_row)

        # Slot selector
        self.lbl_slot = QLabel(t("reschedule_new_slot", default="Khung giờ mới:"))
        self.lbl_slot.setObjectName("fieldLabel")
        layout.addWidget(self.lbl_slot)

        self.slot_combo = ChevronComboBox()
        self.slot_combo.setAccessibleName(self.lbl_slot.text())
        layout.addWidget(self.slot_combo)

        self.slot_status_label = QLabel()
        self.slot_status_label.setObjectName("helperText")
        layout.addWidget(self.slot_status_label)

        # Reason
        self.reason_label = QLabel(t("reschedule_reason_label", default="Lý do đổi lịch:"))
        self.reason_label.setObjectName("fieldLabel")
        layout.addWidget(self.reason_label)

        self.reason_edit = QTextEdit()
        self.reason_edit.setPlaceholderText(t("reschedule_reason_label"))
        self.reason_edit.setMaximumHeight(70)
        self.reason_edit.setTabChangesFocus(True)
        self.reason_edit.setAccessibleName(self.reason_label.text())
        layout.addWidget(self.reason_edit)

        self.error_label = QLabel()
        self.error_label.setObjectName("errorText")
        self.error_label.setVisible(False)
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        # Actions
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch(1)

        self.back_button = QPushButton(t("close_btn", default="Đóng"))
        self.back_button.setObjectName("secondaryButton")
        self.back_button.clicked.connect(self.reject)
        btn_layout.addWidget(self.back_button)

        self.save_button = QPushButton(t("confirm_reschedule_btn", default="Xác nhận đổi lịch"))
        self.save_button.setObjectName("primaryButton")
        self.save_button.setDefault(True)
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._submit_reschedule)
        btn_layout.addWidget(self.save_button)

        layout.addLayout(btn_layout)

        # Populate asynchronously after every dependent control exists.
        self.doctor_combo.currentIndexChanged.connect(self._fetch_slots)
        self.date_edit.dateChanged.connect(self._fetch_slots)
        self._populate_doctors(spec_name)

    def _populate_doctors(self, spec_name: str) -> None:
        if self._tasks.is_running("doctors"):
            return
        self.doctor_combo.blockSignals(True)
        self.doctor_combo.clear()
        self.doctor_combo.blockSignals(False)
        self.slot_combo.clear()
        self.save_button.setEnabled(False)
        self.slot_status_label.setText(t("reschedule_loading_doctors"))
        should_fetch_slots = False

        def operation() -> list[dict[str, Any]]:
            result = self.api_client.get("/api/v1/catalog/doctors")
            if not isinstance(result, list):
                raise TypeError("Expected a doctor list")
            return [item for item in result if isinstance(item, dict)]

        def succeeded(doctors: list[dict[str, Any]]) -> None:
            nonlocal should_fetch_slots
            matching = [
                d
                for d in doctors
                if d.get("specialty_name") == spec_name or d.get("doctor_id") == self.doctor_id
            ]
            if not matching:
                matching = doctors

            self.doctor_combo.blockSignals(True)
            try:
                selected_idx = 0
                for i, doctor in enumerate(matching):
                    doc_id = doctor.get("doctor_id")
                    clinic_name = doctor.get("clinic_name")
                    clinic_str = f" ({clinic_name})" if clinic_name else ""
                    label = f"{doctor.get('full_name')}{clinic_str}"
                    self.doctor_combo.addItem(label, userData=doc_id)
                    if doc_id == self.doctor_id:
                        selected_idx = i
                self.doctor_combo.setCurrentIndex(selected_idx)
            finally:
                self.doctor_combo.blockSignals(False)
            should_fetch_slots = True

        def failed(error: Exception) -> None:
            nonlocal should_fetch_slots
            if self._handle_session_error(error):
                return
            self.doctor_combo.blockSignals(True)
            self.doctor_combo.addItem(
                self.appointment.get("doctor", {}).get("full_name", "Bác sĩ"),
                userData=self.doctor_id,
            )
            self.doctor_combo.blockSignals(False)
            self.error_label.setText(t("reschedule_load_doctors_error"))
            self.error_label.setVisible(True)
            should_fetch_slots = True

        def finished() -> None:
            if should_fetch_slots:
                self._fetch_slots()

        self._tasks.run(
            "doctors",
            operation,
            succeeded,
            failed,
            controls=(
                self.doctor_combo,
                self.date_edit,
                self.open_cal_btn,
                self.slot_combo,
                self.save_button,
            ),
            on_finished=finished,
        )

    def _open_calendar_dialog(self) -> None:
        dlg = CalendarDialog(
            current_date=self.date_edit.date(),
            min_date=QDate.currentDate(),
            max_date=QDate.currentDate().addDays(60),
            parent=self,
        )
        if dlg.exec():
            self.date_edit.setDate(dlg.selected_date())

    def _fetch_slots(self) -> None:
        if self._tasks.is_running("slots") or self.doctor_combo.count() == 0:
            return
        self.slot_combo.clear()
        self.save_button.setEnabled(False)
        self.error_label.setVisible(False)
        self.slot_status_label.setText(t("reschedule_loading_slots"))
        qdate = self.date_edit.date()
        date_str = qdate.toString(Qt.DateFormat.ISODate)

        target_doc_id = (
            self.doctor_combo.currentData()
            if hasattr(self, "doctor_combo") and self.doctor_combo.currentData()
            else self.doctor_id
        )

        curr_date_str = str(self.appointment.get("appointment_date", ""))
        curr_start_t = str(self.appointment.get("start_time", ""))[:5]

        def operation() -> dict[str, Any]:
            result = self.api_client.get(
                f"/api/v1/catalog/doctors/{target_doc_id}/available-slots",
                params={
                    "appointment_date": date_str,
                    "exclude_appointment_id": self.appointment_id,
                },
            )
            if not isinstance(result, dict):
                raise TypeError("Expected an available-slots response")
            return result

        def succeeded(res: dict[str, Any]) -> None:
            has_schedule = res.get("has_schedule", False)
            raw_slots = res.get("slots", [])
            slots = [item for item in raw_slots if isinstance(item, dict)]

            # The current slot cannot be selected as its own replacement.
            available_slots = [
                s
                for s in slots
                if s.get("is_available")
                and not (
                    date_str == curr_date_str
                    and target_doc_id == self.doctor_id
                    and str(s.get("start_time", ""))[:5] == curr_start_t
                )
            ]

            if not has_schedule:
                self.slot_status_label.setText(t("reschedule_no_workday"))
            elif not available_slots:
                if any(
                    str(slot.get("start_time", ""))[:5] == curr_start_t
                    for slot in slots
                    if slot.get("is_available")
                ):
                    self.slot_status_label.setText(t("reschedule_only_current_slot"))
                else:
                    self.slot_status_label.setText(t("reschedule_slots_full"))
            else:
                self.slot_status_label.setText(
                    t("reschedule_slots_available", count=len(available_slots))
                )
                for slot in available_slots:
                    start_t = slot["start_time"]
                    end_t = slot["end_time"]
                    self.slot_combo.addItem(
                        format_time_range(start_t, end_t),
                        userData=(start_t, end_t),
                    )

        def failed(error: Exception) -> None:
            if self._handle_session_error(error):
                return
            self.slot_status_label.setText(t("reschedule_load_slots_error"))

        def finished() -> None:
            self.save_button.setEnabled(self.slot_combo.count() > 0)

        self._tasks.run(
            "slots",
            operation,
            succeeded,
            failed,
            controls=(
                self.doctor_combo,
                self.date_edit,
                self.open_cal_btn,
                self.slot_combo,
            ),
            on_finished=finished,
        )

    def _submit_reschedule(self) -> None:
        if self._tasks.is_running("reschedule"):
            return
        selected_data = self.slot_combo.currentData()
        if not selected_data:
            return

        start_t, end_t = selected_data
        new_date_str = self.date_edit.date().toString(Qt.DateFormat.ISODate)
        reason = self.reason_edit.toPlainText().strip()

        target_doc_id = (
            self.doctor_combo.currentData()
            if hasattr(self, "doctor_combo") and self.doctor_combo.currentData()
            else self.doctor_id
        )

        self.error_label.setVisible(False)
        self.save_button.setText(t("processing"))

        payload = {
            "new_appointment_date": new_date_str,
            "new_start_time": start_t,
            "new_end_time": end_t,
            "new_doctor_id": target_doc_id,
            "reason": reason or None,
        }

        def operation() -> object:
            return self.api_client.post(
                f"/api/v1/appointments/{self.appointment_id}/reschedule",
                json=payload,
            )

        def succeeded(result: object) -> None:
            if isinstance(result, dict):
                self.appointment_rescheduled.emit(result)
            else:
                self.appointment_rescheduled.emit({})
            self.accept()

        def failed(error: Exception) -> None:
            if self._handle_session_error(error):
                return
            message = (
                error.message if isinstance(error, ApiError) else t("error_unexpected_message")
            )
            self.error_label.setText(message)
            self.error_label.setVisible(True)

        def finished() -> None:
            self.save_button.setText(t("confirm_reschedule_btn", default="Xác nhận đổi lịch"))
            self.save_button.setEnabled(self.slot_combo.count() > 0)

        self._tasks.run(
            "reschedule",
            operation,
            succeeded,
            failed,
            controls=(
                self.doctor_combo,
                self.date_edit,
                self.open_cal_btn,
                self.slot_combo,
                self.reason_edit,
                self.back_button,
                self.save_button,
            ),
            on_finished=finished,
        )

    def _handle_session_error(self, error: Exception) -> bool:
        if isinstance(error, ApiError) and error.status_code == 401:
            self.session_expired.emit()
            self.reject()
            return True
        return False

    def _update_summary_labels(self) -> None:
        doctor_label = t("field_doctor")
        current_label = t("reschedule_current_appointment")
        self.summary_doctor_label.setText(
            f"<b>{doctor_label}:</b> {self._summary_doctor_name} "
            f"({self._summary_specialty_name})"
        )
        self.summary_current_label.setText(
            f"<b>{current_label}:</b> {self._summary_date} ({self._summary_time})"
        )

    def retranslate_ui(self) -> None:
        self.setWindowTitle(t("reschedule_dialog_title"))
        if hasattr(self, "title_label"):
            self.title_label.setText(t("reschedule_dialog_title"))
        if hasattr(self, "summary_doctor_label"):
            self._update_summary_labels()
        if hasattr(self, "lbl_doctor"):
            self.lbl_doctor.setText(t("reschedule_choose_doctor", default="Chọn bác sĩ khám:"))
            self.doctor_combo.setAccessibleName(self.lbl_doctor.text())
        if hasattr(self, "lbl_date"):
            self.lbl_date.setText(t("reschedule_new_date", default="Ngày khám mới:"))
        if hasattr(self, "open_cal_btn"):
            self.open_cal_btn.setText(t("btn_open_calendar", default="Chọn ngày"))
        if hasattr(self, "lbl_slot"):
            self.lbl_slot.setText(t("reschedule_new_slot", default="Khung giờ mới:"))
            self.slot_combo.setAccessibleName(self.lbl_slot.text())
        if hasattr(self, "reason_label"):
            self.reason_label.setText(t("reschedule_reason_label"))
            self.reason_edit.setPlaceholderText(t("reschedule_reason_label"))
            self.reason_edit.setAccessibleName(self.reason_label.text())
        if hasattr(self, "save_button"):
            self.save_button.setText(t("confirm_reschedule_btn"))
        if hasattr(self, "back_button"):
            self.back_button.setText(t("close_btn"))
