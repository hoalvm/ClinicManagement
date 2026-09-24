from PySide6.QtWidgets import QMainWindow, QListWidget, QStackedWidget, QHBoxLayout, QWidget, QLabel, QVBoxLayout
from frontend.pages.user_management import UserManagementPage
from frontend.pages.doctor_management import DoctorManagementPage
from frontend.pages.specialty_management import SpecialtyManagementPage
from frontend.pages.clinic_management import ClinicManagementPage
from frontend.pages.schedule_management import ScheduleManagementPage
from frontend.pages.statistics_page import StatisticsPage

class AdminDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ADMIN - Clinic Management System")
        self.resize(1200, 700)

        self.menu = QListWidget()
        self.menu.addItems([
            "Quản lý tài khoản",
            "Quản lý bác sĩ",
            "Quản lý chuyên khoa",
            "Quản lý phòng khám",
            "Quản lý lịch làm việc",
            "Thống kê",
        ])
        self.menu.setFixedWidth(220)

        self.pages = QStackedWidget()
        self.pages.addWidget(UserManagementPage())
        self.pages.addWidget(DoctorManagementPage())
        self.pages.addWidget(SpecialtyManagementPage())
        self.pages.addWidget(ClinicManagementPage())
        self.pages.addWidget(ScheduleManagementPage())
        self.pages.addWidget(StatisticsPage())

        self.menu.currentRowChanged.connect(self.on_menu_changed)
        self.menu.setCurrentRow(0)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(self.menu)
        layout.addWidget(self.pages)
        self.setCentralWidget(container)

    def on_menu_changed(self, index):
        self.pages.setCurrentIndex(index)
        # Reload dữ liệu mỗi khi chuyển tab, để luôn hiện dữ liệu mới nhất
        current_page = self.pages.currentWidget()
        if hasattr(current_page, "load_data"):
            current_page.load_data()
        if hasattr(current_page, "load_lookups"):
            current_page.load_lookups()
        if hasattr(current_page, "load_doctors"):
            current_page.load_doctors()