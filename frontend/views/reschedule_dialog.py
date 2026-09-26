"""Modal dialog for selecting a new date and available slot to reschedule an appointment."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
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
from frontend.widgets.calendar_dialog import CalendarDialog


class RescheduleAppointmentDialog(QDialog):
    """Accessible reschedule dialog with real-time slot checking."""

    appointment_rescheduled = Signal(dict)

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

        self.setWindowTitle(t("reschedule_dialog_title"))
        self.setModal(True)
        self.setMinimumWidth(500)
        self.resize(540, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
            }
            QLabel {
                color: #0f172a;
                background: transparent;
            }
            QLabel#sectionTitle {
                color: #0f766e;
                font-size: 19px;
                font-weight: 700;
            }
            QLabel#fieldLabel {
                color: #334155;
                font-size: 13px;
                font-weight: 600;
                margin-top: 2px;
            }
            QLabel#helperText {
                color: #0f766e;
                font-size: 12px;
                font-weight: 500;
            }
            QLabel#errorText {
                color: #dc2626;
                font-size: 12px;
                font-weight: 600;
            }
            QComboBox, QDateEdit, QTextEdit {
                background-color: #ffffff;
                border: 1.5px solid #cbd5e1;
                border-radius: 8px;
                color: #0f172a;
                padding: 6px 10px;
                font-size: 13px;
            }
            QComboBox:focus, QDateEdit:focus, QTextEdit:focus {
                border-color: #0f766e;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 32px;
                border-left: 1px solid #cbd5e1;
                border-top-right-radius: 7px;
                border-bottom-right-radius: 7px;
                background: #f1f5f9;
            }
            QComboBox::drop-down:hover {
                background: #e2e8f0;
            }
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #0f766e;
                margin-right: 2px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #0f172a;
                border: 1.5px solid #0f766e;
                border-radius: 8px;
                selection-background-color: #ccfbf1;
                selection-color: #0f766e;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                background-color: #ffffff;
                color: #0f172a;
                padding: 8px 12px;
                min-height: 28px;
            }
            QComboBox QAbstractItemView::item:hover,
            QComboBox QAbstractItemView::item:selected {
                background-color: #e6fffa;
                color: #0f766e;
                font-weight: 700;
            }
        """)
        get_i18n().language_changed.connect(self.retranslate_ui)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel(t("reschedule_dialog_title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        doc_name = doctor_info.get("full_name", "Bác sĩ")
        spec_name = doctor_info.get("specialty", "")
        curr_date = appointment.get("appointment_date", "")
        curr_time = f"{appointment.get('start_time', '')} - {appointment.get('end_time', '')}"

        curr_card = QFrame()
        curr_card.setObjectName("card")
        curr_card.setStyleSheet(
            "QFrame#card { background: #f0fdf4; border: 1.5px solid #86efac; border-radius: 8px; padding: 12px; }"
        )
        card_layout = QVBoxLayout(curr_card)
        card_layout.setSpacing(4)
        lbl_doc_info = QLabel(f"<b>Bác sĩ:</b> {doc_name} ({spec_name})")
        lbl_doc_info.setStyleSheet("color: #065f46; font-size: 13px;")
        card_layout.addWidget(lbl_doc_info)

        lbl_curr_info = QLabel(f"<b>Lịch hẹn hiện tại:</b> {curr_date} ({curr_time})")
        lbl_curr_info.setStyleSheet("color: #047857; font-size: 13px; font-weight: 600;")
        card_layout.addWidget(lbl_curr_info)
        layout.addWidget(curr_card)

        # Doctor selection
        self.lbl_doctor = QLabel(t("reschedule_choose_doctor", default="Bác sĩ khám:"))
        self.lbl_doctor.setObjectName("fieldLabel")
        layout.addWidget(self.lbl_doctor)

        self.doctor_combo = QComboBox()
        self.doctor_combo.setMinimumHeight(38)
        layout.addWidget(self.doctor_combo)

        # New Date selection
        self.lbl_date = QLabel(t("reschedule_new_date", default="Ngày khám mới:"))
        self.lbl_date.setObjectName("fieldLabel")
        layout.addWidget(self.lbl_date)

        date_row = QHBoxLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
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

        self.slot_combo = QComboBox()
        self.slot_combo.setMinimumHeight(38)
        layout.addWidget(self.slot_combo)

        self.slot_status_label = QLabel()
        self.slot_status_label.setObjectName("helperText")
        layout.addWidget(self.slot_status_label)

        # Reason
        lbl_reason = QLabel(t("reschedule_reason_label", default="Lý do đổi lịch:"))
        lbl_reason.setObjectName("fieldLabel")
        layout.addWidget(lbl_reason)

        self.reason_edit = QTextEdit()
        self.reason_edit.setPlaceholderText(t("reschedule_reason_label"))
        self.reason_edit.setMaximumHeight(70)
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
        self.back_button.setMinimumHeight(38)
        self.back_button.clicked.connect(self.reject)
        btn_layout.addWidget(self.back_button)

        self.save_button = QPushButton(t("confirm_reschedule_btn", default="Xác nhận đổi lịch"))
        self.save_button.setObjectName("primaryButton")
        self.save_button.setMinimumHeight(38)
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._submit_reschedule)
        btn_layout.addWidget(self.save_button)

        layout.addLayout(btn_layout)

        # Populate doctors and connect signals after all widgets exist
        self._populate_doctors(spec_name)
        self.doctor_combo.currentIndexChanged.connect(self._fetch_slots)
        self.date_edit.dateChanged.connect(self._fetch_slots)

        # Initial slots fetch
        self._fetch_slots()

    def _populate_doctors(self, spec_name: str) -> None:
        self.doctor_combo.blockSignals(True)
        self.doctor_combo.clear()
        try:
            doctors = self.api_client.get("/api/v1/catalog/doctors")
            matching = [
                d
                for d in doctors
                if d.get("specialty_name") == spec_name or d.get("doctor_id") == self.doctor_id
            ]
            if not matching:
                matching = doctors

            selected_idx = 0
            for i, d in enumerate(matching):
                doc_id = d.get("doctor_id")
                clinic_str = f" ({d.get('clinic_name')})" if d.get("clinic_name") else ""
                label = f"{d.get('full_name')}{clinic_str}"
                self.doctor_combo.addItem(label, userData=doc_id)
                if doc_id == self.doctor_id:
                    selected_idx = i
            self.doctor_combo.setCurrentIndex(selected_idx)
        except Exception:
            self.doctor_combo.addItem(
                self.appointment.get("doctor", {}).get("full_name", "Bác sĩ"),
                userData=self.doctor_id,
            )
        finally:
            self.doctor_combo.blockSignals(False)

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
        self.slot_combo.clear()
        self.save_button.setEnabled(False)
        self.slot_status_label.setText("Đang tải danh sách khung giờ trống…")
        qdate = self.date_edit.date()
        date_str = qdate.toString(Qt.DateFormat.ISODate)

        target_doc_id = (
            self.doctor_combo.currentData()
            if hasattr(self, "doctor_combo") and self.doctor_combo.currentData()
            else self.doctor_id
        )

        curr_date_str = str(self.appointment.get("appointment_date", ""))
        curr_start_t = str(self.appointment.get("start_time", ""))[:5]

        try:
            res = self.api_client.get(
                f"/api/v1/catalog/doctors/{target_doc_id}/available-slots",
                params={
                    "appointment_date": date_str,
                    "exclude_appointment_id": self.appointment_id,
                },
            )
            has_schedule = res.get("has_schedule", False)
            slots = res.get("slots", [])

            # Filter out the appointment's own current slot if rescheduling on the same date with the same doctor
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
                self.slot_status_label.setText("Bác sĩ không có lịch làm việc trong ngày này.")
            elif not available_slots:
                # Check if only the current slot was available
                if any(str(s.get("start_time", ""))[:5] == curr_start_t for s in slots if s.get("is_available")):
                    self.slot_status_label.setText(
                        "Ngày này chỉ còn khung giờ bạn đang đặt. Vui lòng chọn ngày khác hoặc bác sĩ khác."
                    )
                else:
                    self.slot_status_label.setText("Tất cả khung giờ trong ngày này đã kín lịch.")
            else:
                self.slot_status_label.setText(f"Có {len(available_slots)} khung giờ mới còn trống.")
                for s in available_slots:
                    start_t = s["start_time"]
                    end_t = s["end_time"]
                    self.slot_combo.addItem(f"{start_t} - {end_t}", userData=(start_t, end_t))
                self.save_button.setEnabled(True)
        except Exception as exc:
            self.slot_status_label.setText(f"Lỗi tải khung giờ: {exc}")

    def _submit_reschedule(self) -> None:
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
        self.save_button.setEnabled(False)
        self.save_button.setText("Đang lưu…")

        try:
            payload = {
                "new_appointment_date": new_date_str,
                "new_start_time": start_t,
                "new_end_time": end_t,
                "new_doctor_id": target_doc_id,
                "reason": reason or None,
            }
            result = self.api_client.post(
                f"/api/v1/appointments/{self.appointment_id}/reschedule",
                json=payload,
            )
            self.appointment_rescheduled.emit(result)
            self.accept()
        except ApiError as exc:
            self.error_label.setText(exc.message)
            self.error_label.setVisible(True)
            self.save_button.setEnabled(True)
            self.save_button.setText("Xác nhận đổi lịch")
        except Exception as exc:
            self.error_label.setText(str(exc))
            self.error_label.setVisible(True)
            self.save_button.setEnabled(True)
            self.save_button.setText(t("confirm_reschedule_btn", default="Xác nhận đổi lịch"))

    def retranslate_ui(self) -> None:
        self.setWindowTitle(t("reschedule_dialog_title"))
        if hasattr(self, "lbl_doctor"):
            self.lbl_doctor.setText(t("reschedule_choose_doctor", default="Chọn bác sĩ khám:"))
        if hasattr(self, "lbl_date"):
            self.lbl_date.setText(t("reschedule_new_date", default="Ngày khám mới:"))
        if hasattr(self, "open_cal_btn"):
            self.open_cal_btn.setText(t("btn_open_calendar", default="Chọn ngày"))
        if hasattr(self, "lbl_slot"):
            self.lbl_slot.setText(t("reschedule_new_slot", default="Khung giờ mới:"))
        if hasattr(self, "save_button"):
            self.save_button.setText(t("confirm_reschedule_btn"))
        if hasattr(self, "back_button"):
            self.back_button.setText(t("close_btn"))
