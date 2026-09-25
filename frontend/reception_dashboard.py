"""Modern, clean Reception & Cashier Dashboard for Clinic Staff."""

from __future__ import annotations

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

from frontend.api.api_client import ApiClient
from frontend.core.config import get_frontend_settings
from frontend.core.session import session_state
from frontend.views.appointment_management_view import AppointmentManagementView
from frontend.views.book_for_patient_view import BookForPatientView
from frontend.views.check_in_view import CheckInView
from frontend.views.invoice_view import InvoiceManagementView
from frontend.views.payment_history_view import PaymentHistoryView
from frontend.views.payment_view import PaymentView
from frontend.views.reception_dashboard_view import ReceptionDashboardView


class ReceptionDashboard(QMainWindow):
    """Container shell for reception, patient intake, appointment booking, and cashier desks."""

    logout_requested = Signal()

    def __init__(self, api_client: ApiClient | None = None) -> None:
        super().__init__()
        settings = get_frontend_settings()
        self.api_client = api_client or ApiClient(
            base_url=settings.api_base_url,
            timeout=settings.api_timeout_seconds,
        )
        if not self.api_client.token:
            if session_state.access_token:
                self.api_client.set_access_token(session_state.access_token)
            else:
                from frontend.api_client import api_client as legacy_client
                if legacy_client.token:
                    self.api_client.set_access_token(legacy_client.token)
                    session_state.set_authenticated(
                        access_token=legacy_client.token,
                        current_user={"username": legacy_client.username, "role": legacy_client.role or "STAFF"},
                    )

        self.setWindowTitle("ClinicCare - Quầy Tiếp Đón & Thu Ngân")
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
        brand_row = QWidget()
        brand_layout = QHBoxLayout(brand_row)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(10)

        brand_mark = QLabel("C")
        brand_mark.setAlignment(Qt.AlignCenter)
        brand_mark.setFixedSize(36, 36)
        brand_mark.setStyleSheet(
            "background-color: #0f766e; color: #ffffff; border-radius: 8px; font-size: 18px; font-weight: 800;"
        )
        brand_layout.addWidget(brand_mark)

        brand_text = QWidget()
        brand_text_layout = QVBoxLayout(brand_text)
        brand_text_layout.setContentsMargins(0, 0, 0, 0)
        brand_text_layout.setSpacing(1)
        brand_title = QLabel("ClinicCare")
        brand_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 700;")
        brand_sub = QLabel("Tiếp đón & Thu ngân")
        brand_sub.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500;")
        brand_text_layout.addWidget(brand_title)
        brand_text_layout.addWidget(brand_sub)
        brand_layout.addWidget(brand_text, 1)

        sidebar_layout.addWidget(brand_row)
        sidebar_layout.addSpacing(16)

        nav_title = QLabel("Nghiệp vụ")
        nav_title.setObjectName("sidebarSectionLabel")
        sidebar_layout.addWidget(nav_title)

        # Menu List
        self.menu = QListWidget()
        self.menu.setObjectName("adminSidebar")
        self._menu_routes = [
            ("dashboard", "Tiếp đón"),
            ("check_in", "Check-in"),
            ("book_for_patient", "Đặt lịch"),
            ("appointment_management", "Lịch hẹn"),
            ("invoice_management", "Hóa đơn"),
            ("payment", "Thu phí"),
            ("payment_history", "Lịch sử thu"),
        ]
        for _, label in self._menu_routes:
            self.menu.addItem(label)
        sidebar_layout.addWidget(self.menu, 1)

        # User Info & Logout
        user_card = QFrame()
        user_card.setObjectName("sidebarUser")
        user_card.setStyleSheet("background-color: #1e293b; border-radius: 8px; border: 1px solid #334155;")
        user_card_layout = QHBoxLayout(user_card)
        user_card_layout.setContentsMargins(10, 8, 10, 8)
        user_card_layout.setSpacing(10)

        avatar = QLabel("NV")
        avatar.setFixedSize(34, 34)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            "background-color: #0369a1; color: #ffffff; border-radius: 6px; font-size: 12px; font-weight: 700;"
        )
        user_card_layout.addWidget(avatar)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(1)
        user_name = QLabel(session_state.username or "Nhân viên")
        user_name.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 600;")
        user_role = QLabel("Tiếp đón & Thu ngân")
        user_role.setStyleSheet("color: #94a3b8; font-size: 11px;")
        info_layout.addWidget(user_name)
        info_layout.addWidget(user_role)
        user_card_layout.addLayout(info_layout, 1)
        sidebar_layout.addWidget(user_card)

        self.logout_btn = QPushButton("Đăng xuất")
        self.logout_btn.setObjectName("logoutButton")
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(self.logout_btn)

        # ------------------- Right Content Stack -------------------
        self.pages = QStackedWidget()
        self.view_dashboard = ReceptionDashboardView(self.api_client)
        self.view_check_in = CheckInView(self.api_client)
        self.view_book = BookForPatientView(self.api_client)
        self.view_appts = AppointmentManagementView(self.api_client)
        self.view_invoices = InvoiceManagementView(self.api_client)
        self.view_payment = PaymentView(self.api_client)
        self.view_payment_history = PaymentHistoryView(self.api_client)

        self.pages.addWidget(self.view_dashboard)        # index 0
        self.pages.addWidget(self.view_check_in)         # index 1
        self.pages.addWidget(self.view_book)             # index 2
        self.pages.addWidget(self.view_appts)            # index 3
        self.pages.addWidget(self.view_invoices)         # index 4
        self.pages.addWidget(self.view_payment)          # index 5
        self.pages.addWidget(self.view_payment_history)  # index 6

        self._connect_signals()

        self.menu.currentRowChanged.connect(self.on_menu_changed)
        self.menu.setCurrentRow(0)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages, 1)

        self.setCentralWidget(container)

    def _connect_signals(self) -> None:
        self.view_dashboard.navigate_requested.connect(self.navigate_by_route)
        self.view_dashboard.check_in_requested.connect(self._handle_check_in_requested)
        self.view_dashboard.create_invoice_requested.connect(self._handle_create_invoice_requested)
        self.view_invoices.pay_invoice_requested.connect(self._handle_pay_invoice_requested)

    def navigate_by_route(self, route: str) -> None:
        route_map = {
            "dashboard": 0,
            "check_in": 1,
            "book_for_patient": 2,
            "appointment_management": 3,
            "invoice_management": 4,
            "payment": 5,
            "payment_history": 6,
        }
        if route in route_map:
            self.menu.setCurrentRow(route_map[route])

    def _handle_check_in_requested(self, appt_id: int) -> None:
        self.navigate_by_route("check_in")
        self.view_check_in.search_input.setText(str(appt_id))
        self.view_check_in.search_and_load()

    def _handle_create_invoice_requested(self, appt_id: int) -> None:
        self.navigate_by_route("invoice_management")

    def _handle_pay_invoice_requested(self, inv_id: int) -> None:
        self.navigate_by_route("payment")
        self.view_payment.inv_input.setText(str(inv_id))
        self.view_payment._fetch_invoice()

    def on_menu_changed(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        current_page = self.pages.currentWidget()
        if hasattr(current_page, "refresh"):
            current_page.refresh()
        elif hasattr(current_page, "_fetch_today_queue"):
            current_page._fetch_today_queue()

    def handle_logout(self) -> None:
        self.logout_requested.emit()
        self.close()
