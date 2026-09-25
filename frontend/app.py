"""Modern, clean Doctor Dashboard and clinical examination view."""

import httpx
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.core.config import get_frontend_settings
from frontend.widgets.feedback_banner import FeedbackBanner
from frontend.widgets.page_header import PageHeader
from frontend.widgets.status_badge import STATUS_LABELS_VN, StatusBadgeDelegate

API_URL = f"{get_frontend_settings().api_base_url.rstrip('/')}/api/v1/doctor"


# ==========================================
# 1. CÁC LUỒNG NỀN (WORKERS - CHỐNG ĐƠ UI)
# ==========================================
class LoginWorker(QThread):
    login_success = Signal(dict)
    login_error = Signal(str)

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password

    def run(self):
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.post(
                    f"{API_URL}/login",
                    json={"username": self.username, "password": self.password},
                )
                if res.status_code == 200:
                    self.login_success.emit(res.json())
                else:
                    detail = res.json().get("detail", "Sai tài khoản hoặc mật khẩu!")
                    self.login_error.emit(detail)
        except Exception as e:
            self.login_error.emit(f"Không thể kết nối Backend: {str(e)}")


class FetchScheduleWorker(QThread):
    success = Signal(list)
    error = Signal(str)

    def __init__(self, doctor_id, token):
        super().__init__()
        self.doctor_id = doctor_id
        self.token = token

    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            with httpx.Client(timeout=5.0) as client:
                res = client.get(
                    f"{API_URL}/schedule?doctor_id={self.doctor_id}", headers=headers
                )
                if res.status_code == 200:
                    self.success.emit(res.json())
                else:
                    self.error.emit(res.json().get("detail", "Lỗi tải lịch khám"))
        except Exception as e:
            self.error.emit(f"Lỗi kết nối: {str(e)}")


class AcceptPatientWorker(QThread):
    success = Signal(dict)
    error = Signal(str)

    def __init__(self, appt_id, doctor_id, token):
        super().__init__()
        self.appt_id = appt_id
        self.doctor_id = doctor_id
        self.token = token

    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            with httpx.Client(timeout=5.0) as client:
                res = client.put(
                    f"{API_URL}/appointments/{self.appt_id}/accept?doctor_id={self.doctor_id}",
                    headers=headers,
                )
                if res.status_code == 200:
                    self.success.emit(res.json())
                else:
                    self.error.emit(res.json().get("detail", "Lỗi tiếp nhận bệnh nhân"))
        except Exception as e:
            self.error.emit(f"Lỗi kết nối: {str(e)}")


class CompleteExamWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, appt_id, payload, token):
        super().__init__()
        self.appt_id = appt_id
        self.payload = payload
        self.token = token

    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            with httpx.Client(timeout=8.0) as client:
                res = client.post(
                    f"{API_URL}/appointments/{self.appt_id}/complete",
                    json=self.payload,
                    headers=headers,
                )
                if res.status_code == 200:
                    self.finished.emit(True, "Hoàn tất ca khám thành công!")
                else:
                    self.finished.emit(
                        False, res.json().get("detail", "Lỗi lưu dữ liệu")
                    )
        except Exception as e:
            self.finished.emit(False, f"Lỗi kết nối máy chủ: {str(e)}")


# ==========================================
# 2. UI: DOCTOR SCHEDULE VIEW
# ==========================================
class DoctorScheduleView(QWidget):
    open_examination = Signal(dict)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # Header
        self.header = PageHeader(
            "Lịch tiếp nhận khám bệnh",
            "Hàng đợi khám hôm nay",
        )
        btn_refresh = QPushButton("Làm mới")
        btn_refresh.setObjectName("secondaryButton")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.load_schedule)
        self.header.add_action(btn_refresh)
        layout.addWidget(self.header)

        # Table Card
        table_card = QFrame()
        table_card.setObjectName("contentCard")
        card_layout = QVBoxLayout(table_card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        card_title = QLabel("Hàng đợi khám hôm nay")
        card_title.setObjectName("sectionTitle")
        card_layout.addWidget(card_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Mã hẹn", "Thời gian", "Bệnh nhân", "Lý do khám", "Trạng thái", "Thao tác"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        h = self.table.horizontalHeader()
        h.setFixedHeight(38)
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setItemDelegateForColumn(4, StatusBadgeDelegate(self.table))

        card_layout.addWidget(self.table)
        layout.addWidget(table_card, 1)

    def load_schedule(self):
        self.worker = FetchScheduleWorker(
            self.main_window.doctor_id, self.main_window.token
        )
        self.worker.success.connect(self.render_table)
        self.worker.error.connect(
            lambda err: QMessageBox.warning(self, "Thông báo", err)
        )
        self.worker.start()

    def render_table(self, items):
        self.table.clearContents()
        self.table.setRowCount(len(items))
        for row, appt in enumerate(items):
            item_id = QTableWidgetItem(f"#{appt['AppointmentID']}")
            item_id.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            time_str = f"{appt.get('StartTime', '')} - {appt.get('EndTime', '')}"
            item_time = QTableWidgetItem(time_str)
            item_time.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, item_time)

            pat_name = appt.get("Patient", {}).get("FullName", "—")
            self.table.setItem(row, 2, QTableWidgetItem(pat_name))

            self.table.setItem(
                row, 3, QTableWidgetItem(appt.get("Reason") or "Khám bệnh")
            )

            # Status pill (rendered via delegate)
            status_text = appt.get("Status", "CHECKED_IN")
            item_status = QTableWidgetItem(STATUS_LABELS_VN.get(status_text, status_text))
            item_status.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, item_status)

            btn_accept = QPushButton(
                "Đang khám" if status_text == "IN_PROGRESS" else "Tiếp nhận khám"
            )
            btn_accept.setObjectName("primaryButton")
            btn_accept.setCursor(Qt.PointingHandCursor)
            btn_accept.setFixedSize(120, 28)
            btn_accept.clicked.connect(lambda _, a=appt: self.accept_patient(a))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            actions_layout.setAlignment(Qt.AlignCenter)
            actions_layout.addWidget(btn_accept)

            self.table.setCellWidget(row, 5, actions_widget)
            self.table.setRowHeight(row, 44)

    def accept_patient(self, appt):
        if appt.get("Status") == "IN_PROGRESS":
            self.open_examination.emit(appt)
            return

        self.worker = AcceptPatientWorker(
            appt["AppointmentID"],
            self.main_window.doctor_id,
            self.main_window.token,
        )
        self.worker.success.connect(lambda _: self.open_examination.emit(appt))
        self.worker.error.connect(lambda err: QMessageBox.critical(self, "Lỗi", err))
        self.worker.start()


# ==========================================
# 3. UI: MEDICAL EXAMINATION VIEW
# ==========================================
class MedicalExamView(QWidget):
    examination_done = Signal()
    back_to_schedule = Signal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.current_appt = None
        self.setup_ui()

    def setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(28, 20, 28, 20)
        root_layout.setSpacing(14)

        # Header Bar
        self.header = PageHeader(
            "Phòng khám bệnh & Chẩn đoán",
            "Bệnh nhân: —",
            show_back=True,
            back_text="Quay lại lịch khám",
        )
        self.header.back_requested.connect(self.back_to_schedule)
        self.sub_title = self.header.subtitle_label
        root_layout.addWidget(self.header)

        self.feedback = FeedbackBanner(self)
        root_layout.addWidget(self.feedback)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(18)

        # ---------------- Left Column ----------------
        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        # Patient Info Card
        card_pat = QFrame()
        card_pat.setObjectName("contentCard")
        pat_card_layout = QVBoxLayout(card_pat)
        pat_card_layout.setContentsMargins(18, 16, 18, 16)
        pat_card_layout.setSpacing(10)

        lbl_pat_title = QLabel("Thông tin bệnh nhân")
        lbl_pat_title.setObjectName("sectionTitle")
        pat_card_layout.addWidget(lbl_pat_title)

        form_pat = QFormLayout()
        form_pat.setSpacing(8)
        self.lb_name = QLabel("—")
        self.lb_name.setStyleSheet("font-weight: 600; color: #0f172a;")
        self.lb_phone = QLabel("—")
        self.lb_gender_dob = QLabel("—")
        self.lb_address = QLabel("—")
        self.lb_address.setWordWrap(True)

        form_pat.addRow("Họ và tên:", self.lb_name)
        form_pat.addRow("Số điện thoại:", self.lb_phone)
        form_pat.addRow("Giới tính / Ngày sinh:", self.lb_gender_dob)
        form_pat.addRow("Địa chỉ:", self.lb_address)
        pat_card_layout.addLayout(form_pat)
        left_col.addWidget(card_pat)

        # Exam Diagnosis Card
        card_exam = QFrame()
        card_exam.setObjectName("contentCard")
        exam_card_layout = QVBoxLayout(card_exam)
        exam_card_layout.setContentsMargins(18, 16, 18, 16)
        exam_card_layout.setSpacing(10)

        lbl_exam_title = QLabel("Ghi nhận chẩn đoán lâm sàng")
        lbl_exam_title.setObjectName("sectionTitle")
        exam_card_layout.addWidget(lbl_exam_title)

        lbl_sym = QLabel("Triệu chứng lâm sàng (*)")
        lbl_sym.setObjectName("fieldLabel")
        self.txt_symptoms = QTextEdit()
        self.txt_symptoms.setPlaceholderText("Ghi nhận triệu chứng của bệnh nhân...")
        self.txt_symptoms.setFixedHeight(65)
        exam_card_layout.addWidget(lbl_sym)
        exam_card_layout.addWidget(self.txt_symptoms)

        lbl_diag = QLabel("Chẩn đoán y khoa (*)")
        lbl_diag.setObjectName("fieldLabel")
        self.txt_diagnosis = QTextEdit()
        self.txt_diagnosis.setPlaceholderText("Nhập kết luận chẩn đoán...")
        self.txt_diagnosis.setFixedHeight(65)
        exam_card_layout.addWidget(lbl_diag)
        exam_card_layout.addWidget(self.txt_diagnosis)

        lbl_note = QLabel("Ghi chú / Lời dặn của bác sĩ")
        lbl_note.setObjectName("fieldLabel")
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Chế độ ăn uống, sinh hoạt, tái khám...")
        self.txt_notes.setFixedHeight(55)
        exam_card_layout.addWidget(lbl_note)
        exam_card_layout.addWidget(self.txt_notes)

        left_col.addWidget(card_exam, 1)
        content_layout.addLayout(left_col, 5)

        # ---------------- Right Column ----------------
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        # Prescription Card
        card_pres = QFrame()
        card_pres.setObjectName("contentCard")
        pres_card_layout = QVBoxLayout(card_pres)
        pres_card_layout.setContentsMargins(18, 16, 18, 16)
        pres_card_layout.setSpacing(10)

        lbl_pres_title = QLabel("Kê đơn thuốc điện tử")
        lbl_pres_title.setObjectName("sectionTitle")
        pres_card_layout.addWidget(lbl_pres_title)

        form_med = QHBoxLayout()
        form_med.setSpacing(8)
        self.in_med = QLineEdit()
        self.in_med.setPlaceholderText("Tên thuốc (VD: Paracetamol)")
        self.in_dosage = QLineEdit()
        self.in_dosage.setPlaceholderText("Hàm lượng (500mg)")
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 200)
        self.spin_qty.setValue(10)
        self.in_instructions = QLineEdit()
        self.in_instructions.setPlaceholderText("Cách dùng (Uống ngày 2 lần)")
        btn_add = QPushButton("+ Thêm")
        btn_add.setObjectName("primaryButton")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self.add_medicine)

        form_med.addWidget(self.in_med, 3)
        form_med.addWidget(self.in_dosage, 2)
        form_med.addWidget(self.spin_qty, 1)
        form_med.addWidget(self.in_instructions, 3)
        form_med.addWidget(btn_add, 1)
        pres_card_layout.addLayout(form_med)

        self.table_med = QTableWidget()
        self.table_med.setColumnCount(4)
        self.table_med.setHorizontalHeaderLabels(
            ["Tên thuốc", "Hàm lượng", "Số lượng", "Hướng dẫn sử dụng"]
        )
        self.table_med.setAlternatingRowColors(True)
        self.table_med.verticalHeader().setVisible(False)
        self.table_med.setShowGrid(False)

        h_med = self.table_med.horizontalHeader()
        h_med.setFixedHeight(34)
        h_med.setSectionResizeMode(0, QHeaderView.Stretch)
        h_med.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h_med.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h_med.setSectionResizeMode(3, QHeaderView.Stretch)

        pres_card_layout.addWidget(self.table_med)
        right_col.addWidget(card_pres, 1)

        # Finish Button
        self.btn_finish = QPushButton("Hoàn tất khám")
        self.btn_finish.setObjectName("primaryButton")
        self.btn_finish.setCursor(Qt.PointingHandCursor)
        self.btn_finish.setMinimumHeight(44)
        self.btn_finish.setStyleSheet(
            "font-size: 14px; font-weight: 700; letter-spacing: 0.5px;"
        )
        self.btn_finish.clicked.connect(self.submit_examination)
        right_col.addWidget(self.btn_finish)

        content_layout.addLayout(right_col, 6)
        root_layout.addLayout(content_layout, 1)

    def load_patient_data(self, appt):
        self.current_appt = appt
        pat = appt.get("Patient", {})
        full_name = pat.get("FullName", "—")
        self.sub_title.setText(f"Bệnh nhân: {full_name} | Mã hẹn: #{appt['AppointmentID']}")
        self.lb_name.setText(full_name)
        self.lb_phone.setText(pat.get("Phone") or "—")

        gender = pat.get("Gender") or "N/A"
        dob = pat.get("DateOfBirth") or "N/A"
        self.lb_gender_dob.setText(f"{gender} | Ngày sinh: {dob}")
        self.lb_address.setText(pat.get("Address") or "Chưa cập nhật")

        self.txt_symptoms.setText(appt.get("Reason") or "")
        self.txt_diagnosis.clear()
        self.txt_notes.clear()
        self.table_med.setRowCount(0)

    def add_medicine(self):
        med = self.in_med.text().strip()
        dosage = self.in_dosage.text().strip()
        qty = self.spin_qty.value()
        instructions = self.in_instructions.text().strip()

        if not med or not instructions:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập tên thuốc và cách dùng!")
            return

        row = self.table_med.rowCount()
        self.table_med.insertRow(row)
        self.table_med.setItem(row, 0, QTableWidgetItem(med))
        self.table_med.setItem(row, 1, QTableWidgetItem(dosage or "—"))
        self.table_med.setItem(row, 2, QTableWidgetItem(str(qty)))
        self.table_med.setItem(row, 3, QTableWidgetItem(instructions))
        self.table_med.setRowHeight(row, 36)

        self.in_med.clear()
        self.in_dosage.clear()
        self.in_instructions.clear()
        self.spin_qty.setValue(10)

    def submit_examination(self):
        symptoms = self.txt_symptoms.toPlainText().strip()
        diagnosis = self.txt_diagnosis.toPlainText().strip()

        if not symptoms or not diagnosis:
            QMessageBox.warning(
                self,
                "Thiếu thông tin",
                "Bắt buộc điền Triệu chứng lâm sàng và Chẩn đoán bệnh!",
            )
            return

        med_items = []
        for r in range(self.table_med.rowCount()):
            med_items.append(
                {
                    "medicine_name": self.table_med.item(r, 0).text(),
                    "dosage": self.table_med.item(r, 1).text(),
                    "quantity": int(self.table_med.item(r, 2).text()),
                    "instructions": self.table_med.item(r, 3).text(),
                }
            )

        payload = {
            "symptoms": symptoms,
            "diagnosis": diagnosis,
            "notes": self.txt_notes.toPlainText().strip() or None,
            "prescription_items": med_items,
        }

        self.btn_finish.setEnabled(False)
        self.worker = CompleteExamWorker(
            self.current_appt["AppointmentID"], payload, self.main_window.token
        )
        self.worker.finished.connect(self.on_submit_finished)
        self.worker.start()

    def on_submit_finished(self, ok, msg):
        self.btn_finish.setEnabled(True)
        if ok:
            QMessageBox.information(self, "Thành công", msg)
            self.examination_done.emit()
        else:
            QMessageBox.critical(self, "Lỗi hoàn tất", msg)


# ==========================================
# 4. KHUNG CHÍNH: DOCTORDASHBOARD (MAIN CONTAINER)
# ==========================================
class DoctorDashboard(QMainWindow):
    logout_requested = Signal()

    def __init__(self, session_data):
        super().__init__()
        self.token = session_data["access_token"]
        self.doctor_id = session_data["doctor_id"]
        self.doctor_name = session_data["doctor_name"]
        self.license_number = session_data.get("license_number") or "N/A"

        self.setWindowTitle(
            f"ClinicCare - Bác sĩ: {self.doctor_name} (CCHN: {self.license_number})"
        )
        self.resize(1240, 780)
        self.setMinimumSize(1080, 660)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Bar
        top_bar = QFrame()
        top_bar.setStyleSheet(
            "background-color: #0f172a; border-bottom: 1px solid #1e293b; padding: 4px 16px;"
        )
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(12, 10, 12, 10)

        brand_lbl = QLabel("CLINICCARE")
        brand_lbl.setStyleSheet(
            "color: #ffffff; font-size: 16px; font-weight: 800; letter-spacing: 1px;"
        )
        sub_lbl = QLabel(
            f"Phân hệ Bác sĩ • {self.doctor_name} (CCHN: {self.license_number})"
        )
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 500;")

        top_bar_layout.addWidget(brand_lbl)
        top_bar_layout.addSpacing(8)
        top_bar_layout.addWidget(sub_lbl)
        top_bar_layout.addStretch(1)

        self.btn_schedule_tab = QPushButton("Lịch khám")
        self.btn_schedule_tab.setObjectName("secondaryButton")
        self.btn_schedule_tab.setCursor(Qt.PointingHandCursor)
        self.btn_schedule_tab.clicked.connect(self.go_to_schedule)
        top_bar_layout.addWidget(self.btn_schedule_tab)

        btn_logout = QPushButton("Đăng xuất")
        btn_logout.setObjectName("logoutButton")
        btn_logout.setCursor(Qt.PointingHandCursor)
        btn_logout.clicked.connect(self.handle_logout)
        top_bar_layout.addWidget(btn_logout)

        main_layout.addWidget(top_bar)

        # Stack views
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)

        self.schedule_view = DoctorScheduleView(self)
        self.exam_view = MedicalExamView(self)

        self.stack.addWidget(self.schedule_view)
        self.stack.addWidget(self.exam_view)

        # Switch signals
        self.schedule_view.open_examination.connect(self.go_to_exam)
        self.exam_view.examination_done.connect(self.go_to_schedule)
        self.exam_view.back_to_schedule.connect(self.go_to_schedule)

        self.setCentralWidget(container)
        self.schedule_view.load_schedule()

    def go_to_exam(self, appt):
        self.exam_view.load_patient_data(appt)
        self.stack.setCurrentIndex(1)

    def go_to_schedule(self):
        self.stack.setCurrentIndex(0)
        self.schedule_view.load_schedule()

    def handle_logout(self):
        self.logout_requested.emit()
        self.close()