"""Modern, clean Admin Dashboard container for ClinicManagement."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from frontend.pages.clinic_management import ClinicManagementPage
from frontend.pages.doctor_management import DoctorManagementPage
from frontend.pages.schedule_management import ScheduleManagementPage
from frontend.pages.specialty_management import SpecialtyManagementPage
from frontend.pages.statistics_page import StatisticsPage
from frontend.pages.user_management import UserManagementPage


class AdminDashboard(QMainWindow):
    logout_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ClinicCare - Quản trị hệ thống")
        self.resize(1280, 800)
        self.setMinimumSize(1100, 680)

        container = QWidget()
        main_layout = QHBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ------------------- Left Sidebar -------------------
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 20)
        sidebar_layout.setSpacing(12)

        # Brand header
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(2)
        brand_title = QLabel("CLINICCARE")
        brand_title.setStyleSheet(
            "color: #ffffff; font-size: 18px; font-weight: 800; letter-spacing: 1px;"
        )
        brand_sub = QLabel("HỆ THỐNG QUẢN TRỊ")
        brand_sub.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        brand_layout.addWidget(brand_title)
        brand_layout.addWidget(brand_sub)
        sidebar_layout.addLayout(brand_layout)

        sidebar_layout.addSpacing(16)

        nav_title = QLabel("Chức năng")
        nav_title.setObjectName("sidebarSectionLabel")
        sidebar_layout.addWidget(nav_title)

        # Menu List
        self.menu = QListWidget()
        self.menu.setObjectName("adminSidebar")
        self.menu.addItems(
            [
                "Tài khoản",
                "Bác sĩ",
                "Chuyên khoa",
                "Phòng khám",
                "Lịch trực",
                "Thống kê",
            ]
        )
        sidebar_layout.addWidget(self.menu, 1)

        # Bottom User Info & Logout
        user_card = QFrame()
        user_card.setStyleSheet(
            "background-color: #1e293b; border-radius: 8px; padding: 6px;"
        )
        user_layout = QVBoxLayout(user_card)
        user_layout.setContentsMargins(10, 10, 10, 10)
        user_layout.setSpacing(2)

        user_role = QLabel("QUẢN TRỊ VIÊN")
        user_role.setStyleSheet("color: #2dd4bf; font-size: 10px; font-weight: 700;")
        user_layout.addWidget(user_role)
        sidebar_layout.addWidget(user_card)

        self.logout_btn = QPushButton("Đăng xuất")
        self.logout_btn.setObjectName("logoutButton")
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(self.logout_btn)

        # ------------------- Right Content Pages -------------------
        self.pages = QStackedWidget()
        self.pages.addWidget(UserManagementPage())
        self.pages.addWidget(DoctorManagementPage())
        self.pages.addWidget(SpecialtyManagementPage())
        self.pages.addWidget(ClinicManagementPage())
        self.pages.addWidget(ScheduleManagementPage())
        self.pages.addWidget(StatisticsPage())

        self.menu.currentRowChanged.connect(self.on_menu_changed)
        self.menu.setCurrentRow(0)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages, 1)

        self.setCentralWidget(container)

    def on_menu_changed(self, index):
        self.pages.setCurrentIndex(index)
        current_page = self.pages.currentWidget()
        if hasattr(current_page, "load_data"):
            current_page.load_data()
        if hasattr(current_page, "load_lookups"):
            current_page.load_lookups()
        if hasattr(current_page, "load_doctors"):
            current_page.load_doctors()

    def handle_logout(self):
        self.logout_requested.emit()
        self.close()
