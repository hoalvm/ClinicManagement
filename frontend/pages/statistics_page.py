"""Modern, clean Statistics and Overview page for Admin."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from frontend.api_client import api_client
from frontend.widgets.page_header import PageHeader
from frontend.widgets.stat_card import ModernStatCard


class StatisticsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(28, 24, 28, 24)
        self.main_layout.setSpacing(20)

        # ------------------- Header -------------------
        self.header = PageHeader(
            "Thống kê",
            "Tổng quan số liệu hoạt động",
        )
        self.main_layout.addWidget(self.header)

        # ------------------- Stat Cards Grid -------------------
        self.cards_layout = QGridLayout()
        self.cards_layout.setHorizontalSpacing(14)
        self.cards_layout.setVerticalSpacing(14)
        self.main_layout.addLayout(self.cards_layout)

        # ------------------- 2 Sub Tables -------------------
        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(16)

        # Table 1: Doctors by Specialty
        card_sp = QFrame()
        card_sp.setObjectName("contentCard")
        layout_sp = QVBoxLayout(card_sp)
        layout_sp.setContentsMargins(16, 16, 16, 16)
        layout_sp.setSpacing(10)

        lbl_sp = QLabel("Phân bổ bác sĩ theo chuyên khoa")
        lbl_sp.setObjectName("sectionTitle")
        layout_sp.addWidget(lbl_sp)

        self.specialty_table = QTableWidget()
        self.specialty_table.setColumnCount(2)
        self.specialty_table.setHorizontalHeaderLabels(["Chuyên khoa", "Số lượng bác sĩ"])
        self.specialty_table.setAlternatingRowColors(True)
        self.specialty_table.verticalHeader().setVisible(False)
        self.specialty_table.setShowGrid(False)

        h1 = self.specialty_table.horizontalHeader()
        h1.setFixedHeight(36)
        h1.setSectionResizeMode(0, QHeaderView.Stretch)
        h1.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        layout_sp.addWidget(self.specialty_table)
        sub_layout.addWidget(card_sp)

        # Table 2: Doctors by Clinic
        card_cl = QFrame()
        card_cl.setObjectName("contentCard")
        layout_cl = QVBoxLayout(card_cl)
        layout_cl.setContentsMargins(16, 16, 16, 16)
        layout_cl.setSpacing(10)

        lbl_cl = QLabel("Phân bổ bác sĩ theo phòng khám")
        lbl_cl.setObjectName("sectionTitle")
        layout_cl.addWidget(lbl_cl)

        self.clinic_table = QTableWidget()
        self.clinic_table.setColumnCount(2)
        self.clinic_table.setHorizontalHeaderLabels(["Phòng khám", "Số lượng bác sĩ"])
        self.clinic_table.setAlternatingRowColors(True)
        self.clinic_table.verticalHeader().setVisible(False)
        self.clinic_table.setShowGrid(False)

        h2 = self.clinic_table.horizontalHeader()
        h2.setFixedHeight(36)
        h2.setSectionResizeMode(0, QHeaderView.Stretch)
        h2.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        layout_cl.addWidget(self.clinic_table)
        sub_layout.addWidget(card_cl)

        self.main_layout.addLayout(sub_layout, 1)

        self.load_data()

    def load_data(self):
        r = api_client.get("/statistics/overview")
        if r.status_code != 200:
            return
        d = r.json()

        # Clear old cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        cards_data = [
            ("TỔNG TÀI KHOẢN", d.get("total_users", 0), "#0284c7"),
            ("BÁC SĨ HOẠT ĐỘNG", d.get("total_doctors", 0), "#0f766e"),
            ("PHÒNG KHÁM", d.get("total_clinics", 0), "#d97706"),
            ("CHUYÊN KHOA", d.get("total_specialties", 0), "#7c3aed"),
            ("CA LỊCH TRỰC", d.get("total_schedules", 0), "#059669"),
        ]

        for i, (title, value, color) in enumerate(cards_data):
            card = ModernStatCard(title, value, color)
            self.cards_layout.addWidget(card, 0, i)

        # Populate specialty table
        doc_sp = d.get("doctors_by_specialty", [])
        self.specialty_table.setRowCount(len(doc_sp))
        for row, item in enumerate(doc_sp):
            self.specialty_table.setItem(row, 0, QTableWidgetItem(item.get("name", "—")))
            count_item = QTableWidgetItem(str(item.get("count", 0)))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.specialty_table.setItem(row, 1, count_item)
            self.specialty_table.setRowHeight(row, 40)

        # Populate clinic table
        doc_cl = d.get("doctors_by_clinic", [])
        self.clinic_table.setRowCount(len(doc_cl))
        for row, item in enumerate(doc_cl):
            self.clinic_table.setItem(row, 0, QTableWidgetItem(item.get("name", "—")))
            count_item = QTableWidgetItem(str(item.get("count", 0)))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.clinic_table.setItem(row, 1, count_item)
            self.clinic_table.setRowHeight(row, 40)