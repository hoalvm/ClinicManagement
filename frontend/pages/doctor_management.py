from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                                 QPushButton, QLineEdit, QComboBox, QMessageBox, QLabel, QHeaderView)
from api_client import api_client

class DoctorManagementPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title_label = QLabel("QUẢN LÝ BÁC SĨ")
        title_label.setStyleSheet("font-size: 20px; font-weight: 700; color: #1e293b;")
        layout.addWidget(title_label)

        form_layout = QHBoxLayout()
        self.username_input = QLineEdit(); self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit(); self.password_input.setPlaceholderText("Mật khẩu")
        self.fullname_input = QLineEdit(); self.fullname_input.setPlaceholderText("Họ tên")
        self.specialty_combo = QComboBox()
        self.clinic_combo = QComboBox()
        self.license_input = QLineEdit(); self.license_input.setPlaceholderText("Số giấy phép")
        add_btn = QPushButton("Thêm"); add_btn.clicked.connect(self.add_doctor)

        for w in [self.username_input, self.password_input, self.fullname_input,
                  self.specialty_combo, self.clinic_combo, self.license_input, add_btn]:
            form_layout.addWidget(w)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Họ tên", "Chuyên khoa", "Phòng khám", "Giấy phép", "Trạng thái", "Xóa"]
        )
        header = self.table.horizontalHeader()
        header.setFixedHeight(30)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        layout.addLayout(form_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.load_lookups()
        self.load_data()

    def load_lookups(self):
        self.specialty_combo.clear()
        self.specialty_map = {}
        r = api_client.get("/specialties/")
        if r.status_code == 200:
            for s in r.json():
                if s["IsActive"]:
                    self.specialty_combo.addItem(s["SpecialtyName"])
                    self.specialty_map[s["SpecialtyName"]] = s["SpecialtyID"]

        self.clinic_combo.clear()
        self.clinic_map = {}
        r = api_client.get("/clinics/")
        if r.status_code == 200:
            for c in r.json():
                if c["IsActive"]:
                    self.clinic_combo.addItem(c["ClinicName"])
                    self.clinic_map[c["ClinicName"]] = c["ClinicID"]

    def load_data(self):
        r = api_client.get("/doctors/")
        if r.status_code != 200:
            return
        items = r.json()
        self.table.setRowCount(len(items))
        for row, d in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(str(d["DoctorID"])))
            self.table.setItem(row, 1, QTableWidgetItem(d["FullName"]))
            self.table.setItem(row, 2, QTableWidgetItem(d.get("SpecialtyName") or ""))
            self.table.setItem(row, 3, QTableWidgetItem(d.get("ClinicName") or ""))
            self.table.setItem(row, 4, QTableWidgetItem(d.get("LicenseNumber") or ""))
            self.table.setItem(row, 5, QTableWidgetItem("Hoạt động" if d["IsActive"] else "Đã khóa"))
            del_btn = QPushButton("Xóa")
            del_btn.clicked.connect(lambda _, did=d["DoctorID"]: self.delete_item(did))
            self.table.setCellWidget(row, 6, del_btn)

    def add_doctor(self):
        self.load_lookups()
        specialty_name = self.specialty_combo.currentText()
        clinic_name = self.clinic_combo.currentText()

        if not specialty_name:
            QMessageBox.warning(self, "Lỗi", "Chưa có chuyên khoa nào — hãy tạo chuyên khoa trước")
            return
        if not self.username_input.text().strip() or not self.password_input.text():
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập Username và mật khẩu")
            return

        payload = {
            "Username": self.username_input.text().strip(),
            "Password": self.password_input.text(),
            "FullName": self.fullname_input.text(),
            "SpecialtyID": self.specialty_map[specialty_name],
            "ClinicID": self.clinic_map.get(clinic_name),
            "LicenseNumber": self.license_input.text(),
        }
        r = api_client.post("/doctors/", json=payload)
        if r.status_code == 200:
            self.load_data()
            self.username_input.clear(); self.password_input.clear()
            self.fullname_input.clear(); self.license_input.clear()
        else:
            QMessageBox.warning(self, "Lỗi", r.json().get("detail", "Có lỗi xảy ra"))

    def delete_item(self, doctor_id):
        if QMessageBox.question(self, "Xác nhận", "Vô hiệu hóa bác sĩ này?") == QMessageBox.Yes:
            api_client.delete(f"/doctors/{doctor_id}")
            self.load_data()