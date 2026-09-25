"""Modern, clean Schedule Management page for Admin."""

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.api_client import api_client
from frontend.widgets.page_header import PageHeader

DAYS_VN = {
    1: "Thứ Hai",
    2: "Thứ Ba",
    3: "Thứ Tư",
    4: "Thứ Năm",
    5: "Thứ Sáu",
    6: "Thứ Bảy",
    7: "Chủ Nhật",
}


class ScheduleManagementPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # ------------------- Header -------------------
        self.header = PageHeader(
            "Lịch trực",
            "Phân ca làm việc của bác sĩ",
        )
        layout.addWidget(self.header)

        # ------------------- Create Form Card -------------------
        form_card = QFrame()
        form_card.setObjectName("contentCard")
        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(20, 16, 20, 18)
        form_card_layout.setSpacing(12)

        form_title = QLabel("Thêm ca trực")
        form_title.setObjectName("sectionTitle")
        form_card_layout.addWidget(form_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        # Doctor
        col_doc = QVBoxLayout()
        col_doc.setSpacing(4)
        lbl_doc = QLabel("Bác sĩ")
        lbl_doc.setObjectName("fieldLabel")
        self.doctor_combo = QComboBox()
        col_doc.addWidget(lbl_doc)
        col_doc.addWidget(self.doctor_combo)
        grid.addLayout(col_doc, 0, 0, 1, 2)

        # Day of week
        col_day = QVBoxLayout()
        col_day.setSpacing(4)
        lbl_day = QLabel("Ngày trong tuần")
        lbl_day.setObjectName("fieldLabel")
        self.day_combo = QComboBox()
        for day_id, day_name in DAYS_VN.items():
            self.day_combo.addItem(day_name, day_id)
        col_day.addWidget(lbl_day)
        col_day.addWidget(self.day_combo)
        grid.addLayout(col_day, 0, 2)

        # Start Time
        col_st = QVBoxLayout()
        col_st.setSpacing(4)
        lbl_st = QLabel("Giờ bắt đầu")
        lbl_st.setObjectName("fieldLabel")
        self.start_time = QTimeEdit(QTime(8, 0))
        self.start_time.setDisplayFormat("HH:mm")
        col_st.addWidget(lbl_st)
        col_st.addWidget(self.start_time)
        grid.addLayout(col_st, 1, 0)

        # End Time
        col_et = QVBoxLayout()
        col_et.setSpacing(4)
        lbl_et = QLabel("Giờ kết thúc")
        lbl_et.setObjectName("fieldLabel")
        self.end_time = QTimeEdit(QTime(17, 0))
        self.end_time.setDisplayFormat("HH:mm")
        col_et.addWidget(lbl_et)
        col_et.addWidget(self.end_time)
        grid.addLayout(col_et, 1, 1)

        # Slot duration
        col_dur = QVBoxLayout()
        col_dur.setSpacing(4)
        lbl_dur = QLabel("Thời lượng ca (phút)")
        lbl_dur.setObjectName("fieldLabel")
        self.slot_duration = QSpinBox()
        self.slot_duration.setRange(5, 240)
        self.slot_duration.setValue(30)
        col_dur.addWidget(lbl_dur)
        col_dur.addWidget(self.slot_duration)
        grid.addLayout(col_dur, 1, 2)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        add_btn = QPushButton("Thêm mới")
        add_btn.setObjectName("primaryButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setMinimumHeight(36)
        add_btn.setMinimumWidth(120)
        add_btn.clicked.connect(self.add_schedule)
        btn_layout.addWidget(add_btn)

        form_card_layout.addLayout(grid)
        form_card_layout.addLayout(btn_layout)
        layout.addWidget(form_card)

        # ------------------- Table Card -------------------
        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(16, 16, 16, 16)
        table_card_layout.setSpacing(10)

        table_title = QLabel("Danh sách lịch làm việc hiện tại")
        table_title.setObjectName("sectionTitle")
        table_card_layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Bác sĩ",
            "Ngày",
            "Giờ bắt đầu",
            "Giờ kết thúc",
            "Thao tác",
        ])
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        header = self.table.horizontalHeader()
        header.setFixedHeight(38)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        table_card_layout.addWidget(self.table)
        layout.addWidget(table_card, 1)

        self.load_doctors()
        self.load_data()

    def load_doctors(self):
        self.doctor_combo.clear()
        self.doctor_map = {}
        r = api_client.get("/doctors/")
        if r.status_code == 200:
            for d in r.json():
                if d["IsActive"]:
                    label = f"{d['FullName']} ({d.get('SpecialtyName') or 'Chưa phân khoa'})"
                    self.doctor_combo.addItem(label)
                    self.doctor_map[label] = d["DoctorID"]

    def load_data(self):
        r = api_client.get("/schedules/")
        if r.status_code != 200:
            return
        items = r.json()
        self.table.clearContents()

        doctors_map = {}
        rd = api_client.get("/doctors/")
        if rd.status_code == 200:
            doctors_map = {d["DoctorID"]: d["FullName"] for d in rd.json()}

        self.table.setRowCount(len(items))
        for row, s in enumerate(items):
            item_id = QTableWidgetItem(str(s["ScheduleID"]))
            item_id.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            self.table.setItem(row, 1, QTableWidgetItem(doctors_map.get(s["DoctorID"], "—")))

            item_day = QTableWidgetItem(DAYS_VN.get(s["DayOfWeek"], "—"))
            item_day.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, item_day)

            st_item = QTableWidgetItem(str(s["StartTime"])[:5] if len(str(s["StartTime"])) >= 5 else str(s["StartTime"]))
            st_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, st_item)

            et_item = QTableWidgetItem(str(s["EndTime"])[:5] if len(str(s["EndTime"])) >= 5 else str(s["EndTime"]))
            et_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, et_item)

            # Delete button
            del_btn = QPushButton("Xóa")
            del_btn.setObjectName("actionDeleteBtn")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedSize(54, 28)
            del_btn.clicked.connect(lambda _, sid=s["ScheduleID"]: self.delete_item(sid))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(6, 0, 6, 0)
            actions_layout.setAlignment(Qt.AlignCenter)
            actions_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 5, actions_widget)
            self.table.setRowHeight(row, 44)

    def add_schedule(self):
        self.load_doctors()
        doctor_label = self.doctor_combo.currentText()
        if not doctor_label:
            QMessageBox.warning(self, "Lỗi", "Chưa có bác sĩ nào — hãy tạo bác sĩ trước.")
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
            QMessageBox.warning(self, "Lỗi", r.json().get("detail", "Không thể thêm lịch làm việc."))

    def delete_item(self, schedule_id):
        if QMessageBox.question(self, "Xác nhận", "Bạn có chắc muốn xóa lịch làm việc này?") == QMessageBox.Yes:
            api_client.delete(f"/schedules/{schedule_id}")
            self.load_data()