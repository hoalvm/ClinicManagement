"""Admin application shell built on the shared role-aware sidebar."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from frontend.pages.clinic_management import ClinicManagementPage
from frontend.pages.doctor_management import DoctorManagementPage
from frontend.pages.schedule_management import ScheduleManagementPage
from frontend.pages.specialty_management import SpecialtyManagementPage
from frontend.pages.statistics_page import StatisticsPage
from frontend.pages.user_management import UserManagementPage
from frontend.widgets.app_sidebar import AppSidebar, NavigationItem
from frontend.widgets.application_shell import ApplicationShell


class AdminDashboard(QMainWindow):
    """Shared-shell container for every system-administration destination."""

    logout_requested = Signal()

    EXPANDED_SIDEBAR_WIDTH = AppSidebar.EXPANDED_WIDTH
    COMPACT_SIDEBAR_WIDTH = AppSidebar.COMPACT_WIDTH
    COMPACT_BREAKPOINT = 1280
    _NAVIGATION = (
        NavigationItem("users", "Tài khoản", "user", "CHỨC NĂNG"),
        NavigationItem("doctors", "Bác sĩ", "medical", "CHỨC NĂNG"),
        NavigationItem("specialties", "Chuyên khoa", "medical", "CHỨC NĂNG"),
        NavigationItem("clinics", "Phòng khám", "dashboard", "CHỨC NĂNG"),
        NavigationItem("schedules", "Lịch trực", "calendar", "CHỨC NĂNG"),
        NavigationItem("statistics", "Thống kê", "dashboard", "CHỨC NĂNG"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ClinicCare - Quản trị hệ thống")
        self.resize(1280, 800)
        self.setMinimumSize(1100, 680)

        self.sidebar = AppSidebar(
            self._NAVIGATION,
            brand_subtitle="Quản trị hệ thống",
            logout_text="Đăng xuất",
        )
        self.sidebar.setAccessibleName("Điều hướng quản trị")
        self.sidebar.set_user(
            {"full_name": "Quản trị viên"},
            role_label="Toàn quyền hệ thống",
        )
        self.sidebar.navigation_requested.connect(self._navigate)
        self.sidebar.logout_requested.connect(self.handle_logout)

        self.pages = QStackedWidget()
        self._routes: dict[str, int] = {}
        admin_pages = (
            ("users", UserManagementPage()),
            ("doctors", DoctorManagementPage()),
            ("specialties", SpecialtyManagementPage()),
            ("clinics", ClinicManagementPage()),
            ("schedules", ScheduleManagementPage()),
            ("statistics", StatisticsPage()),
        )
        for route, page in admin_pages:
            page.session_expired.connect(self.handle_logout)
            self._routes[route] = self.pages.addWidget(page)

        self._sidebar_compact = False
        self.shell = ApplicationShell(
            self.sidebar,
            self.pages,
            compact_handler=self._set_sidebar_compact,
        )
        self.setCentralWidget(self.shell)
        self._navigate("users")
        self.shell.set_sidebar_compact(self.width() < self.COMPACT_BREAKPOINT)

    def _set_sidebar_compact(self, compact: bool) -> None:
        self._sidebar_compact = bool(compact)
        self.sidebar.set_compact(self._sidebar_compact)

    def resizeEvent(self, event) -> None:  # noqa: N802
        if hasattr(self, "shell"):
            self.shell.set_sidebar_compact(
                event.size().width() < self.COMPACT_BREAKPOINT
            )
        super().resizeEvent(event)

    def _navigate(self, route: str) -> None:
        index = self._routes.get(route)
        if index is None:
            return
        self.sidebar.set_active(route)
        self.pages.setCurrentIndex(index)
        page = self.pages.currentWidget()
        if hasattr(page, "load_data"):
            page.load_data()
        if hasattr(page, "load_lookups"):
            page.load_lookups()
        if hasattr(page, "load_doctors"):
            page.load_doctors()

    def handle_logout(self) -> None:
        self.logout_requested.emit()
        self.close()
