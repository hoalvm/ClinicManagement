from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
                                 QTableWidget, QTableWidgetItem, QHeaderView)
from api_client import api_client

class StatCard(QFrame):
    def __init__(self, title, value, color):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border-left: 5px solid {color};
            }}
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 14, 18, 14)

        value_label = QLabel(str(value))
        value_label.setStyleSheet("font-size: 28px; font-weight: 700; color: #1e293b; border: none;")
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13px; color: #64748b; border: none;")

        layout.addWidget(value_label)
        layout.addWidget(title_label)
        self.setLayout(layout)


class StatisticsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(24, 20, 24, 20)
        self.layout.setSpacing(18)

        title_label = QLabel("THỐNG KÊ TỔNG QUAN")
        title_label.setStyleSheet("font-size: 20px; font-weight: 700; color: #1e293b;")
        self.layout.addWidget(title_label)

        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(16)
        self.layout.addLayout(self.cards_layout)

        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(16)

        # Bảng bác sĩ theo chuyên khoa
        self.specialty_table = QTableWidget()
        self.specialty_table.setColumnCount(2)
        self.specialty_table.setHorizontalHeaderLabels(["Chuyên khoa", "Số bác sĩ"])
        header1 = self.specialty_table.horizontalHeader()
        header1.setFixedHeight(30)
        header1.setStretchLastSection(False)
        header1.setSectionResizeMode(0, QHeaderView.Stretch)
        header1.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        # Bảng bác sĩ theo phòng khám
        self.clinic_table = QTableWidget()
        self.clinic_table.setColumnCount(2)
        self.clinic_table.setHorizontalHeaderLabels(["Phòng khám", "Số bác sĩ"])
        header2 = self.clinic_table.horizontalHeader()
        header2.setFixedHeight(30)
        header2.setStretchLastSection(False)
        header2.setSectionResizeMode(0, QHeaderView.Stretch)
        header2.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        left_box = QVBoxLayout()
        left_label = QLabel("Bác sĩ theo chuyên khoa")
        left_label.setStyleSheet("font-weight: 600; color: #334155;")
        left_box.addWidget(left_label)
        left_box.addWidget(self.specialty_table)

        right_box = QVBoxLayout()
        right_label = QLabel("Bác sĩ theo phòng khám")
        right_label.setStyleSheet("font-weight: 600; color: #334155;")
        right_box.addWidget(right_label)
        right_box.addWidget(self.clinic_table)

        sub_layout.addLayout(left_box)
        sub_layout.addLayout(right_box)
        self.layout.addLayout(sub_layout)

        self.setLayout(self.layout)
        self.load_data()

    def load_data(self):
        r = api_client.get("/statistics/overview")
        if r.status_code != 200:
            return
        d = r.json()

        # Xóa card cũ trước khi vẽ lại (tránh chồng khi load lại nhiều lần)
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        cards_data = [
            ("Tổng tài khoản", d["total_users"], "#2563eb"),
            ("Bác sĩ", d["total_doctors"], "#16a34a"),
            ("Phòng khám", d["total_clinics"], "#f59e0b"),
            ("Chuyên khoa", d["total_specialties"], "#8b5cf6"),
            ("Lịch làm việc", d["total_schedules"], "#ef4444"),
        ]
        for i, (title, value, color) in enumerate(cards_data):
            card = StatCard(title, value, color)
            self.cards_layout.addWidget(card, 0, i)

        self.specialty_table.setRowCount(len(d["doctors_by_specialty"]))
        for row, item in enumerate(d["doctors_by_specialty"]):
            self.specialty_table.setItem(row, 0, QTableWidgetItem(item["name"]))
            self.specialty_table.setItem(row, 1, QTableWidgetItem(str(item["count"])))

        self.clinic_table.setRowCount(len(d["doctors_by_clinic"]))
        for row, item in enumerate(d["doctors_by_clinic"]):
            self.clinic_table.setItem(row, 0, QTableWidgetItem(item["name"]))
            self.clinic_table.setItem(row, 1, QTableWidgetItem(str(item["count"])))