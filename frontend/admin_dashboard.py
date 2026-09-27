"""Modern, clean Admin Dashboard container for ClinicManagement."""

from PySide6.QtCore import QSize, Qt, Signal
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
from frontend.ui.icons import apply_line_icon, line_icon
from frontend.widgets.application_shell import ApplicationShell


class AdminDashboard(QMainWindow):
    logout_requested = Signal()

    EXPANDED_SIDEBAR_WIDTH = 240
    COMPACT_SIDEBAR_WIDTH = 84
    # Expanding at 1240 px reduced the page below its three-card breakpoint.
    # 1280 px preserves the same content layout on both sides of the transition.
    COMPACT_BREAKPOINT = 1280
    _NAVIGATION = (
        ("Tài khoản", "user"),
        ("Bác sĩ", "medical"),
        ("Chuyên khoa", "medical"),
        ("Phòng khám", "dashboard"),
        ("Lịch trực", "calendar"),
        ("Thống kê", "dashboard"),
    )

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ClinicCare - Quản trị hệ thống")
        self.resize(1280, 800)
        self.setMinimumSize(1100, 680)

        # ------------------- Left Sidebar -------------------
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setAccessibleName("Điều hướng quản trị")
        self.sidebar.setFixedWidth(self.EXPANDED_SIDEBAR_WIDTH)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(16, 24, 16, 20)
        self.sidebar_layout.setSpacing(12)

        # Brand header
        brand_row = QWidget()
        brand_layout = QHBoxLayout(brand_row)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(10)

        self.brand_mark = QLabel("C")
        self.brand_mark.setObjectName("sidebarBrandMark")
        self.brand_mark.setAccessibleName("ClinicCare")
        self.brand_mark.setAlignment(Qt.AlignCenter)
        self.brand_mark.setFixedSize(36, 36)
        brand_layout.addWidget(self.brand_mark)

        self.brand_text = QWidget()
        brand_text_layout = QVBoxLayout(self.brand_text)
        brand_text_layout.setContentsMargins(0, 0, 0, 0)
        brand_text_layout.setSpacing(1)
        brand_title = QLabel("ClinicCare")
        brand_title.setObjectName("brandLabel")
        brand_sub = QLabel("Quản trị hệ thống")
        brand_sub.setObjectName("sidebarSubtitle")
        brand_text_layout.addWidget(brand_title)
        brand_text_layout.addWidget(brand_sub)
        brand_layout.addWidget(self.brand_text, 1)

        self.sidebar_layout.addWidget(brand_row)
        self.sidebar_layout.addSpacing(16)

        self.nav_title = QLabel("Chức năng")
        self.nav_title.setObjectName("sidebarSectionLabel")
        self.sidebar_layout.addWidget(self.nav_title)

        # Menu List
        self.menu = QListWidget()
        self.menu.setObjectName("adminSidebar")
        self.menu.setAccessibleName("Các chức năng quản trị")
        self.menu.setIconSize(QSize(20, 20))
        for label, icon_name in self._NAVIGATION:
            self.menu.addItem(label)
            item = self.menu.item(self.menu.count() - 1)
            item.setIcon(
                line_icon(
                    icon_name,
                    "#94A3B8",
                    size=20,
                    active_color="#F8FAFC",
                    selected_color="#FFFFFF",
                )
            )
            item.setToolTip(label)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, label)
            item.setSizeHint(QSize(0, 46))
        self.sidebar_layout.addWidget(self.menu, 1)

        # Bottom User Info & Logout
        self.user_card = QFrame()
        self.user_card.setObjectName("sidebarUser")
        self.user_card.setAccessibleName("Đang đăng nhập với vai trò quản trị viên")
        user_card_layout = QHBoxLayout(self.user_card)
        user_card_layout.setContentsMargins(10, 8, 10, 8)
        user_card_layout.setSpacing(10)

        avatar = QFrame()
        avatar.setObjectName("userAvatar")
        avatar.setFixedSize(38, 38)
        avatar_layout = QVBoxLayout(avatar)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_text = QLabel("AD")
        avatar_text.setObjectName("userAvatarText")
        avatar_text.setAlignment(Qt.AlignCenter)
        avatar_layout.addWidget(avatar_text)
        user_card_layout.addWidget(avatar)

        self.user_info = QWidget()
        info_layout = QVBoxLayout(self.user_info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(1)
        name_lbl = QLabel("Quản trị viên")
        name_lbl.setObjectName("sidebarUserName")
        role_lbl = QLabel("Toàn quyền hệ thống")
        role_lbl.setObjectName("sidebarUserRole")
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(role_lbl)
        user_card_layout.addWidget(self.user_info, 1)
        self.sidebar_layout.addWidget(self.user_card)

        self.logout_btn = QPushButton("Đăng xuất")
        self.logout_btn.setObjectName("logoutButton")
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        apply_line_icon(
            self.logout_btn,
            "logout",
            color="#CBD5E1",
            active_color="#F87171",
            accessible_name="Đăng xuất",
        )
        self.logout_btn.clicked.connect(self.handle_logout)
        self.sidebar_layout.addWidget(self.logout_btn)

        # ------------------- Right Content Pages -------------------
        self.pages = QStackedWidget()
        admin_pages = (
            UserManagementPage(),
            DoctorManagementPage(),
            SpecialtyManagementPage(),
            ClinicManagementPage(),
            ScheduleManagementPage(),
            StatisticsPage(),
        )
        for page in admin_pages:
            page.session_expired.connect(self.handle_logout)
            self.pages.addWidget(page)

        self.menu.currentRowChanged.connect(self.on_menu_changed)
        self.menu.setCurrentRow(0)

        self._sidebar_compact = False
        self.shell = ApplicationShell(
            self.sidebar,
            self.pages,
            compact_handler=self._set_sidebar_compact,
        )
        self.setCentralWidget(self.shell)
        self.shell.set_sidebar_compact(self.width() < self.COMPACT_BREAKPOINT)

    def _set_sidebar_compact(self, compact: bool) -> None:
        compact = bool(compact)
        if compact == self._sidebar_compact and self.sidebar.width() in {
            self.EXPANDED_SIDEBAR_WIDTH,
            self.COMPACT_SIDEBAR_WIDTH,
        }:
            return

        self._sidebar_compact = compact
        self.sidebar.setProperty("compact", compact)
        self.sidebar.setFixedWidth(
            self.COMPACT_SIDEBAR_WIDTH if compact else self.EXPANDED_SIDEBAR_WIDTH
        )
        margin = 10 if compact else 16
        self.sidebar_layout.setContentsMargins(margin, 24, margin, 20)
        self.brand_text.setVisible(not compact)
        self.nav_title.setVisible(not compact)
        self.user_info.setVisible(not compact)

        for index, (label, _icon_name) in enumerate(self._NAVIGATION):
            item = self.menu.item(index)
            item.setText("" if compact else label)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
                if compact
                else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            item.setToolTip(label)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, label)

        self.logout_btn.setText("" if compact else "Đăng xuất")
        self.logout_btn.setToolTip("Đăng xuất")
        self.sidebar.style().unpolish(self.sidebar)
        self.sidebar.style().polish(self.sidebar)
        self.sidebar.updateGeometry()

    def resizeEvent(self, event):  # noqa: N802
        if hasattr(self, "shell"):
            self.shell.set_sidebar_compact(
                event.size().width() < self.COMPACT_BREAKPOINT
            )
        super().resizeEvent(event)

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
