from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                                 QPushButton, QComboBox, QTimeEdit, QSpinBox, QMessageBox, QLabel, QHeaderView)
from PySide6.QtCore import QTime
from frontend.api_client import api_client

DAYS_VN = {1: "Thứ 2", 2: "Thứ 3", 3: "Thứ 4", 4: "Thứ 5", 5: "Thứ 6", 6: "Thứ 7", 7: "Chủ nhật"}

class ScheduleManagementPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title_label = QLabel("QUẢN LÝ LỊCH LÀM VIỆC")
        title_label.setStyleSheet("font-size: 20px; font-weight: 700; color: #1e293b;")
        layout.addWidget(title_label)

        form_layout = QHBoxLayout()
        self.doctor_combo = QComboBox()
        self.day_combo = QComboBox()
        for day_id, day_name in DAYS_VN.items():
            self.day_combo.addItem(day_name, day_id)
        self.start_time = QTimeEdit(QTime(8, 0))
        self.end_time = QTimeEdit(QTime(17, 0))
        self.slot_duration = QSpinBox(); self.slot_duration.setRange(5, 240); self.slot_duration.setValue(30)
        add_btn = QPushButton("Thêm"); add_btn.clicked.connect(self.add_schedule)

        for w in [self.doctor_combo, self.day_combo, self.start_time, self.end_time, self.slot_duration, add_btn]:
            form_layout.addWidget(w)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Bác sĩ", "Thứ", "Giờ bắt đầu", "Giờ kết thúc", "Xóa"])
        header = self.table.horizontalHeader()
        header.setFixedHeight(30)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        layout.addLayout(form_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.load_doctors()
        self.load_data()

    def load_doctors(self):
        self.doctor_combo.clear()
        self.doctor_map = {}
        r = api_client.get("/doctors/")
        if r.status_code == 200:
            for d in r.json():
                if d["IsActive"]:
                    label = f'{d["FullName"]} ({d.get("SpecialtyName") or ""})'
                    self.doctor_combo.addItem(label)
                    self.doctor_map[label] = d["DoctorID"]

    def load_data(self):
        r = api_client.get("/schedules/")
        if r.status_code != 200:
            return
        items = r.json()

        doctors_map = {}
        rd = api_client.get("/doctors/")
        if rd.status_code == 200:
            doctors_map = {d["DoctorID"]: d["FullName"] for d in rd.json()}

        self.table.setRowCount(len(items))
        for row, s in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(str(s["ScheduleID"])))
            self.table.setItem(row, 1, QTableWidgetItem(doctors_map.get(s["DoctorID"], "")))
            self.table.setItem(row, 2, QTableWidgetItem(DAYS_VN.get(s["DayOfWeek"], "")))
            self.table.setItem(row, 3, QTableWidgetItem(str(s["StartTime"])))
            self.table.setItem(row, 4, QTableWidgetItem(str(s["EndTime"])))
            del_btn = QPushButton("Xóa")
            del_btn.clicked.connect(lambda _, sid=s["ScheduleID"]: self.delete_item(sid))
            self.table.setCellWidget(row, 5, del_btn)

    def add_schedule(self):
        self.load_doctors()
        doctor_label = self.doctor_combo.currentText()
        if not doctor_label:
            QMessageBox.warning(self, "Lỗi", "Chưa có bác sĩ nào — hãy tạo bác sĩ trước")
            return

        payload = {
            "DoctorID": self.doctor_map[doctor_label],
            "DayOfWeek": self.day_combo.currentData(),
            "StartTime": self.start_time.time().toString("HH:mm:ss"),
            "EndTime": self.end_time.time().toString("HH:mm:ss"),
            "SlotDuration": self.slot_duration.value(),
        }
        r = api_client.post("/schedules/", json=payload)
        if r.status_code == 200:
            self.load_data()
        else:
            QMessageBox.warning(self, "Lỗi", r.json().get("detail", "Có lỗi xảy ra"))

    def delete_item(self, schedule_id):
        if QMessageBox.question(self, "Xác nhận", "Xóa lịch làm việc này?") == QMessageBox.Yes:
            api_client.delete(f"/schedules/{schedule_id}")
            self.load_data()