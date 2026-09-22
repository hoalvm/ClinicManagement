import sys
import httpx
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QStackedWidget, QLineEdit, QTextEdit, QSpinBox, QMessageBox,
    QGroupBox, QFormLayout, QDialog
)
from PySide6.QtCore import Qt, QThread, Signal

API_URL = "http://127.0.0.1:8000/api/v1/doctor"

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
                    json={"username": self.username, "password": self.password}
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
                res = client.get(f"{API_URL}/schedule?doctor_id={self.doctor_id}", headers=headers)
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
                    headers=headers
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
                    headers=headers
                )
                if res.status_code == 200:
                    self.finished.emit(True, "Hoàn tất ca khám thành công!")
                else:
                    self.finished.emit(False, res.json().get("detail", "Lỗi lưu dữ liệu"))
        except Exception as e:
            self.finished.emit(False, f"Lỗi kết nối máy chủ: {str(e)}")


# ==========================================
# 2. UI 1: LOGIN DIALOG
# ==========================================
class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Đăng Nhập - Phân Hệ Bác Sĩ")
        self.setFixedSize(380, 240)
        self.session_data = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("HỆ THỐNG PHÒNG KHÁM\nĐĂNG NHẬP BÁC SĨ")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e3a8a;")
        layout.addWidget(title)

        form = QFormLayout()
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Tài khoản (VD: bsduy)")
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Mật khẩu (VD: 123456)")

        form.addRow("Tài khoản:", self.txt_username)
        form.addRow("Mật khẩu:", self.txt_password)
        layout.addLayout(form)

        self.btn_login = QPushButton("ĐĂNG NHẬP")
        self.btn_login.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 10px; border-radius: 4px;")
        self.btn_login.clicked.connect(self.handle_login)
        layout.addWidget(self.btn_login)

        self.txt_password.returnPressed.connect(self.handle_login)

    def handle_login(self):
        user = self.txt_username.text().strip()
        pwd = self.txt_password.text().strip()
        if not user or not pwd:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng điền đầy đủ tài khoản và mật khẩu!")
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("Đang xác thực...")

        self.worker = LoginWorker(user, pwd)
        self.worker.login_success.connect(self.on_success)
        self.worker.login_error.connect(self.on_error)
        self.worker.start()

    def on_success(self, data):
        self.session_data = data
        self.accept()

    def on_error(self, err_msg):
        self.btn_login.setEnabled(True)
        self.btn_login.setText("ĐĂNG NHẬP")
        QMessageBox.critical(self, "Lỗi đăng nhập", err_msg)


# ==========================================
# 3. UI 2: DOCTOR SCHEDULE (LỊCH KHÁM & TIẾP NHẬN)
# ==========================================
class DoctorScheduleView(QWidget):
    open_examination = Signal(dict)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout(self)

        title = QLabel("DANH SÁCH BỆNH NHÂN ĐANG CHỜ KHÁM (CHECKED-IN)")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e3a8a;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Mã hẹn", "Thời gian", "Bệnh nhân", "Lý do khám", "Trạng thái", "Thao tác"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_refresh = QPushButton("Làm mới danh sách")
        btn_refresh.setStyleSheet("padding: 8px; font-weight: bold; background-color: #f1f5f9;")
        btn_refresh.clicked.connect(self.load_schedule)
        layout.addWidget(btn_refresh)

    def load_schedule(self):
        self.worker = FetchScheduleWorker(self.main_window.doctor_id, self.main_window.token)
        self.worker.success.connect(self.render_table)
        self.worker.error.connect(lambda err: QMessageBox.warning(self, "Thông báo", err))
        self.worker.start()

    def render_table(self, items):
        self.table.setRowCount(len(items))
        for row, appt in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(f"#{appt['AppointmentID']}"))
            time_str = f"{appt['StartTime']} - {appt['EndTime']}"
            self.table.setItem(row, 1, QTableWidgetItem(time_str))
            self.table.setItem(row, 2, QTableWidgetItem(appt['Patient']['FullName']))
            self.table.setItem(row, 3, QTableWidgetItem(appt.get('Reason') or "Không có"))
            self.table.setItem(row, 4, QTableWidgetItem(appt['Status']))

            btn_accept = QPushButton("Tiếp nhận khám")
            btn_accept.setStyleSheet("background-color: #2563eb; color: white; padding: 5px; font-weight: bold; border-radius: 3px;")
            btn_accept.clicked.connect(lambda _, a=appt: self.accept_patient(a))
            self.table.setCellWidget(row, 5, btn_accept)

    def accept_patient(self, appt):
        self.worker = AcceptPatientWorker(appt['AppointmentID'], self.main_window.doctor_id, self.main_window.token)
        # Khi tiếp nhận thành công, chuyển dữ liệu appt sang trang khám
        self.worker.success.connect(lambda _: self.open_examination.emit(appt))
        self.worker.error.connect(lambda err: QMessageBox.critical(self, "Lỗi", err))
        self.worker.start()


# ==========================================
# 4. UI 3, 4, 5, 6: PATIENT INFO, EXAMINATION, PRESCRIPTION, RESULT
# ==========================================
class MedicalExamView(QWidget):
    examination_done = Signal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.current_appt = None
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)

        # Cột trái: UI 3 (PatientInformation) & UI 4 (MedicalExamination)
        left_col = QVBoxLayout()
        
        # UI 3: PatientInformation
        self.pat_box = QGroupBox("Thông tin Bệnh nhân (PatientInformation)")
        pat_layout = QFormLayout(self.pat_box)
        self.lb_name = QLabel("--")
        self.lb_phone = QLabel("--")
        self.lb_gender_dob = QLabel("--")
        self.lb_address = QLabel("--")
        self.lb_address.setWordWrap(True)
        pat_layout.addRow("Họ tên:", self.lb_name)
        pat_layout.addRow("Số điện thoại:", self.lb_phone)
        pat_layout.addRow("Giới tính / Ngày sinh:", self.lb_gender_dob)
        pat_layout.addRow("Địa chỉ:", self.lb_address)
        left_col.addWidget(self.pat_box)

        # UI 4: MedicalExamination
        self.exam_box = QGroupBox("Ghi nhận Chẩn đoán Lâm sàng (MedicalExamination)")
        exam_layout = QFormLayout(self.exam_box)
        self.txt_symptoms = QTextEdit()
        self.txt_symptoms.setFixedHeight(75)
        self.txt_diagnosis = QTextEdit()
        self.txt_diagnosis.setFixedHeight(75)
        self.txt_notes = QTextEdit()
        self.txt_notes.setFixedHeight(60)

        exam_layout.addRow("Triệu chứng (*):", self.txt_symptoms)
        exam_layout.addRow("Chẩn đoán (*):", self.txt_diagnosis)
        exam_layout.addRow("Ghi chú / Lời dặn:", self.txt_notes)
        left_col.addWidget(self.exam_box)

        layout.addLayout(left_col, 1)

        # Cột phải: UI 5 (Prescription) & UI 6 (ExaminationResult)
        right_col = QVBoxLayout()
        
        # UI 5: Prescription
        pres_box = QGroupBox("Kê đơn thuốc (Prescription)")
        pres_layout = QVBoxLayout(pres_box)

        form_med = QHBoxLayout()
        self.in_med = QLineEdit()
        self.in_med.setPlaceholderText("Tên thuốc")
        self.in_dosage = QLineEdit()
        self.in_dosage.setPlaceholderText("Hàm lượng")
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 200)
        self.in_instructions = QLineEdit()
        self.in_instructions.setPlaceholderText("Cách dùng")
        btn_add = QPushButton("+ Thêm")
        btn_add.setStyleSheet("background-color: #16a34a; color: white; font-weight: bold;")
        btn_add.clicked.connect(self.add_medicine)

        form_med.addWidget(self.in_med, 2)
        form_med.addWidget(self.in_dosage, 1)
        form_med.addWidget(self.spin_qty, 1)
        form_med.addWidget(self.in_instructions, 2)
        form_med.addWidget(btn_add, 1)
        pres_layout.addLayout(form_med)

        self.table_med = QTableWidget(0, 4)
        self.table_med.setHorizontalHeaderLabels(["Tên thuốc", "Hàm lượng", "SL", "Cách dùng"])
        self.table_med.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        pres_layout.addWidget(self.table_med)
        right_col.addWidget(pres_box)

        # UI 6: ExaminationResult (Nút hoàn tất ca khám)
        self.btn_finish = QPushButton("HOÀN TẤT BUỔI KHÁM (COMPLETED)")
        self.btn_finish.setStyleSheet("background-color: #059669; color: white; font-size: 14px; font-weight: bold; padding: 12px; border-radius: 6px;")
        self.btn_finish.clicked.connect(self.submit_examination)
        right_col.addWidget(self.btn_finish)

        layout.addLayout(right_col, 1)

    def load_patient_data(self, appt):
        self.current_appt = appt
        pat = appt['Patient']
        self.lb_name.setText(pat['FullName'])
        self.lb_phone.setText(pat.get('Phone') or "Chưa có")
        
        gender = pat.get('Gender') or "N/A"
        dob = pat.get('DateOfBirth') or "N/A"
        self.lb_gender_dob.setText(f"{gender} | {dob}")
        self.lb_address.setText(pat.get('Address') or "Chưa cập nhật")

        # Điền lý do khám ban đầu vào ô triệu chứng để bác sĩ tiện theo dõi
        self.txt_symptoms.setText(appt.get('Reason') or "")
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
        self.table_med.setItem(row, 1, QTableWidgetItem(dosage or "-"))
        self.table_med.setItem(row, 2, QTableWidgetItem(str(qty)))
        self.table_med.setItem(row, 3, QTableWidgetItem(instructions))

        self.in_med.clear()
        self.in_dosage.clear()
        self.in_instructions.clear()
        self.spin_qty.setValue(1)

    def submit_examination(self):
        symptoms = self.txt_symptoms.toPlainText().strip()
        diagnosis = self.txt_diagnosis.toPlainText().strip()

        if not symptoms or not diagnosis:
            QMessageBox.warning(self, "Thiếu thông tin", "Bắt buộc điền Triệu chứng lâm sàng và Chẩn đoán bệnh!")
            return

        med_items = []
        for r in range(self.table_med.rowCount()):
            med_items.append({
                "medicine_name": self.table_med.item(r, 0).text(),
                "dosage": self.table_med.item(r, 1).text(),
                "quantity": int(self.table_med.item(r, 2).text()),
                "instructions": self.table_med.item(r, 3).text()
            })

        payload = {
            "symptoms": symptoms,
            "diagnosis": diagnosis,
            "notes": self.txt_notes.toPlainText().strip() or None,
            "prescription_items": med_items
        }

        self.btn_finish.setEnabled(False)
        self.worker = CompleteExamWorker(self.current_appt['AppointmentID'], payload, self.main_window.token)
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
# 5. KHUNG CHÍNH: DOCTORDASHBOARD (MAIN CONTAINER)
# ==========================================
class DoctorDashboard(QMainWindow):
    def __init__(self, session_data):
        super().__init__()
        self.token = session_data["access_token"]
        self.doctor_id = session_data["doctor_id"]
        self.doctor_name = session_data["doctor_name"]
        self.license_number = session_data.get("license_number") or "N/A"

        self.setWindowTitle(f"HỆ THỐNG BÁC SĨ - {self.doctor_name} (CCHN: {self.license_number})")
        self.resize(1100, 640)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.schedule_view = DoctorScheduleView(self)
        self.exam_view = MedicalExamView(self)

        self.stack.addWidget(self.schedule_view)
        self.stack.addWidget(self.exam_view)

        # Chuyển đổi qua lại giữa Lịch khám và Phòng khám
        self.schedule_view.open_examination.connect(self.go_to_exam)
        self.exam_view.examination_done.connect(self.go_to_schedule)

        # Nạp dữ liệu ca khám ban đầu
        self.schedule_view.load_schedule()

    def go_to_exam(self, appt):
        self.exam_view.load_patient_data(appt)
        self.stack.setCurrentIndex(1)

    def go_to_schedule(self):
        self.stack.setCurrentIndex(0)
        self.schedule_view.load_schedule()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    app.setStyleSheet("""
        QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; color: #1e293b; }
        QGroupBox { font-weight: bold; border: 1px solid #cbd5e1; border-radius: 6px; margin-top: 8px; padding-top: 14px; background-color: #ffffff; }
        QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; color: #0284c7; }
        QLineEdit, QTextEdit, QSpinBox { border: 1px solid #cbd5e1; border-radius: 4px; padding: 6px; background: #f8fafc; }
        QLineEdit:focus, QTextEdit:focus { border: 1px solid #0284c7; background: #ffffff; }
        QTableWidget { gridline-color: #e2e8f0; border: 1px solid #cbd5e1; border-radius: 4px; background: white; }
        QHeaderView::section { background-color: #f1f5f9; font-weight: bold; padding: 6px; border: none; border-bottom: 1px solid #cbd5e1; }
    """)

    login_diag = LoginDialog()
    if login_diag.exec() == QDialog.Accepted and login_diag.session_data:
        dashboard = DoctorDashboard(login_diag.session_data)
        dashboard.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)