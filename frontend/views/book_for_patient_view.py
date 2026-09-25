"""Book Appointment for Patient (Walk-in or Phone Call) View."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.views.common import BaseApiView
from frontend.widgets.page_header import PageHeader


class BookForPatientView(BaseApiView):
    """View allowing clinic receptionist to book an appointment on behalf of any patient."""

    appointment_booked = Signal(dict)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        self.header = PageHeader(
            "Đặt lịch cho bệnh nhân",
            "Tiếp nhận đặt lịch trực tiếp hoặc qua điện thoại",
            parent=self,
        )
        layout.addWidget(self.header)
        layout.addWidget(self.feedback)
        layout.addWidget(self.loading)

        form_card = QFrame()
        form_card.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 12px; padding: 24px;")
        form_layout = QVBoxLayout(form_card)
        form_layout.setSpacing(16)

        # Section 1: Patient Information
        pt_section = QLabel("1. Thông tin bệnh nhân")
        pt_section.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a; margin-bottom: 4px;")
        form_layout.addWidget(pt_section)

        pt_form = QFormLayout()
        pt_form.setSpacing(12)

        self.pt_search_input = QLineEdit()
        self.pt_search_input.setPlaceholderText("Tìm kiếm theo số điện thoại hoặc họ tên...")
        btn_lookup = QPushButton("Tra cứu")
        btn_lookup.clicked.connect(self._lookup_patient)
        lookup_row = QHBoxLayout()
        lookup_row.addWidget(self.pt_search_input, 3)
        lookup_row.addWidget(btn_lookup, 1)
        pt_form.addRow("Bệnh nhân cũ:", lookup_row)

        self.name_input = QLineEdit()
        pt_form.addRow("Họ và tên (*):", self.name_input)

        self.phone_input = QLineEdit()
        pt_form.addRow("Số điện thoại (*):", self.phone_input)

        self.gender_combo = QComboBox()
        self.gender_combo.addItem("Nam", "MALE")
        self.gender_combo.addItem("Nữ", "FEMALE")
        self.gender_combo.addItem("Khác", "OTHER")
        pt_form.addRow("Giới tính:", self.gender_combo)

        self.dob_edit = QDateEdit()
        self.dob_edit.setCalendarPopup(True)
        self.dob_edit.setDate(QDate.currentDate().addYears(-30))
        self.dob_edit.setDisplayFormat("yyyy-MM-dd")
        pt_form.addRow("Ngày sinh:", self.dob_edit)

        self.address_input = QLineEdit()
        pt_form.addRow("Địa chỉ:", self.address_input)

        form_layout.addLayout(pt_form)

        # Section 2: Appointment Details
        appt_section = QLabel("2. Thông tin lịch khám")
        appt_section.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a; margin-top: 12px; margin-bottom: 4px;")
        form_layout.addWidget(appt_section)

        appt_form = QFormLayout()
        appt_form.setSpacing(12)

        self.doctor_combo = QComboBox()
        self.doctor_combo.addItem("BS. Lê Thị Mai (Nội tổng quát)", 1)
        self.doctor_combo.addItem("BS. Trần Văn Đức (Tim mạch)", 2)
        self.doctor_combo.addItem("BS. Phạm Minh Trí (Nhi khoa)", 3)
        appt_form.addRow("Bác sĩ phụ trách (*):", self.doctor_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        appt_form.addRow("Ngày khám (*):", self.date_edit)

        time_row = QHBoxLayout()
        self.time_combo = QComboBox()
        self.time_combo.addItems([
            "08:00 - 08:30",
            "08:30 - 09:00",
            "09:00 - 09:30",
            "09:30 - 10:00",
            "10:00 - 10:30",
            "10:30 - 11:00",
            "13:30 - 14:00",
            "14:00 - 14:30",
            "14:30 - 15:00",
            "15:00 - 15:30",
            "15:30 - 16:00",
            "16:00 - 16:30",
        ])
        time_row.addWidget(self.time_combo)
        appt_form.addRow("Khung giờ (*):", time_row)

        self.reason_input = QTextEdit()
        self.reason_input.setMaximumHeight(80)
        appt_form.addRow("Lý do khám:", self.reason_input)

        self.chk_autoconfirm = QCheckBox("Tự động xác nhận lịch hẹn (Trạng thái: Đã xác nhận)")
        self.chk_autoconfirm.setChecked(True)
        appt_form.addRow("", self.chk_autoconfirm)

        form_layout.addLayout(appt_form)

        # Submit Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_reset = QPushButton("Làm mới")
        self.btn_reset.clicked.connect(self._clear_form)
        btn_row.addWidget(self.btn_reset)

        self.btn_submit = QPushButton("Tạo lịch khám")
        self.btn_submit.setStyleSheet(
            "background-color: #0f766e; color: white; font-size: 14px; font-weight: 700; padding: 10px 24px; border-radius: 8px;"
        )
        self.btn_submit.clicked.connect(self._submit_booking)
        btn_row.addWidget(self.btn_submit)

        form_layout.addLayout(btn_row)
        layout.addWidget(form_card)
        layout.addStretch(1)

        scroll.setWidget(container)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _lookup_patient(self) -> None:
        q = self.pt_search_input.text().strip()
        if not q:
            self.feedback.show_message("Tìm kiếm", "Vui lòng nhập số điện thoại hoặc tên bệnh nhân.", severity="info")
            return

        self.run_api_task(
            "lookup_patient",
            lambda: self.api_client.get("/api/v1/reception/patients/search", params={"q": q}),
            self._on_patient_found,
            loading_text="Đang tra cứu hồ sơ...",
        )

    def _on_patient_found(self, patients: list[dict[str, Any]]) -> None:
        if not patients:
            self.feedback.show_message("Không tìm thấy", "Chưa có thông tin bệnh nhân. Vui lòng nhập chi tiết bên dưới.", severity="info")
            return
        p = patients[0]
        self.name_input.setText(p.get("full_name", ""))
        self.phone_input.setText(p.get("phone", "") or "")
        self.address_input.setText(p.get("address", "") or "")
        gender = p.get("gender", "MALE")
        for i in range(self.gender_combo.count()):
            if self.gender_combo.itemData(i) == gender or self.gender_combo.itemText(i) == gender:
                self.gender_combo.setCurrentIndex(i)
                break
        self.feedback.show_message("Đã tìm thấy", f"Đã tải thông tin cho {p.get('full_name')}", severity="success")

    def _clear_form(self) -> None:
        self.pt_search_input.clear()
        self.name_input.clear()
        self.phone_input.clear()
        self.address_input.clear()
        self.reason_input.clear()
        self.feedback.clear()

    def _submit_booking(self) -> None:
        full_name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()

        if not full_name or not phone:
            self.feedback.show_message("Thiếu thông tin", "Vui lòng nhập họ và tên cùng số điện thoại người bệnh.", severity="danger")
            return

        time_str = self.time_combo.currentText().split(" - ")[0] + ":00"
        end_str = self.time_combo.currentText().split(" - ")[1] + ":00"
        doctor_id = self.doctor_combo.currentData() or 1
        appt_date = self.date_edit.date().toString("yyyy-MM-dd")
        dob = self.dob_edit.date().toString("yyyy-MM-dd")

        gender_code = self.gender_combo.currentData() or "MALE"
        payload = {
            "full_name": full_name,
            "phone": phone,
            "date_of_birth": dob,
            "gender": gender_code,
            "address": self.address_input.text().strip() or None,
            "doctor_id": doctor_id,
            "appointment_date": appt_date,
            "start_time": time_str,
            "end_time": end_str,
            "reason": self.reason_input.toPlainText().strip() or "Đặt lịch khám tại quầy tiếp đón",
            "auto_confirm": self.chk_autoconfirm.isChecked(),
        }

        self.run_api_task(
            "book_for_patient",
            lambda: self.api_client.post("/api/v1/reception/appointments/book", json=payload),
            self._on_booking_success,
            loading_text="Đang lưu lịch hẹn...",
        )

    def _on_booking_success(self, result: dict[str, Any]) -> None:
        appt_id = result.get("appointment_id", 0)
        self.feedback.show_message(
            "Đặt lịch thành công",
            f"Đã tạo thành công lịch hẹn #{appt_id} cho bệnh nhân {self.name_input.text()}!",
            severity="success",
        )
        self._clear_form()
        self.appointment_booked.emit(result)
