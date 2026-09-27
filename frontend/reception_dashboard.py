"""Shared-shell workspace for reception and cashier staff."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent, QResizeEvent
from PySide6.QtWidgets import QMainWindow, QStackedWidget

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
from frontend.widgets.app_sidebar import AppSidebar, NavigationItem
from frontend.widgets.application_shell import ApplicationShell


class ReceptionDashboard(QMainWindow):
    """Reception, patient intake, appointment booking, and cashier shell."""

    logout_requested = Signal()
    # Keep the content-side breakpoints stable while the sidebar changes width.
    # At 1320 px the expanded sidebar still leaves enough room for the widest
    # two-column reception page.
    SIDEBAR_COMPACT_BREAKPOINT = 1320

    _NAVIGATION = (
        NavigationItem("dashboard", "Tổng quan", "dashboard", "NGHIỆP VỤ"),
        NavigationItem("check_in", "Tiếp nhận bệnh nhân", "medical"),
        NavigationItem("book_for_patient", "Đặt lịch hộ", "calendar"),
        NavigationItem("appointment_management", "Lịch hẹn", "calendar"),
        NavigationItem("invoice_management", "Hóa đơn", "invoice", "THU NGÂN"),
        NavigationItem("payment", "Thu phí", "invoice"),
        NavigationItem("payment_history", "Lịch sử thanh toán", "invoice"),
    )

    def __init__(self, api_client: ApiClient | None = None) -> None:
        super().__init__()
        self._logout_in_progress = False
        self._client_disposed = False
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
                        current_user={
                            "username": legacy_client.username,
                            "role": legacy_client.role or "STAFF",
                        },
                    )

        self.setWindowTitle("ClinicCare - Quầy Tiếp đón & Thu ngân")
        self.resize(1280, 800)
        self.setMinimumSize(1100, 680)

        self.sidebar = AppSidebar(
            self._NAVIGATION,
            brand_subtitle="Tiếp đón & Thu ngân",
            logout_text="Đăng xuất",
        )
        self.sidebar.set_user(
            {
                "username": session_state.username or "Nhân viên",
                "role": "STAFF",
            },
            role_label="Tiếp đón & Thu ngân",
        )
        self.sidebar.navigation_requested.connect(self.navigate_by_route)
        self.sidebar.logout_requested.connect(self.handle_logout)
        # Compatibility alias for callers targeting the shell's logout control.
        self.logout_btn = self.sidebar.logout_button
        self.pages = QStackedWidget()
        self.view_dashboard = ReceptionDashboardView(self.api_client)
        self.view_check_in = CheckInView(self.api_client)
        self.view_book = BookForPatientView(self.api_client)
        self.view_appts = AppointmentManagementView(self.api_client)
        self.view_invoices = InvoiceManagementView(self.api_client)
        self.view_payment = PaymentView(self.api_client)
        self.view_payment_history = PaymentHistoryView(self.api_client)

        self._route_to_page = {
            "dashboard": self.view_dashboard,
            "check_in": self.view_check_in,
            "book_for_patient": self.view_book,
            "appointment_management": self.view_appts,
            "invoice_management": self.view_invoices,
            "payment": self.view_payment,
            "payment_history": self.view_payment_history,
        }
        for page in self._route_to_page.values():
            self.pages.addWidget(page)

        self._connect_signals()
        self.shell = ApplicationShell(self.sidebar, self.pages)
        self.setCentralWidget(self.shell)
        self.shell.set_sidebar_compact(
            self.width() < self.SIDEBAR_COMPACT_BREAKPOINT
        )
        self.navigate_by_route("dashboard")

    def _connect_signals(self) -> None:
        for page in self._route_to_page.values():
            page.session_expired.connect(self.handle_logout)
        self.view_dashboard.navigate_requested.connect(self.navigate_by_route)
        self.view_dashboard.check_in_requested.connect(self._handle_check_in_requested)
        self.view_dashboard.create_invoice_requested.connect(
            self._handle_create_invoice_requested
        )
        self.view_invoices.pay_invoice_requested.connect(
            self._handle_pay_invoice_requested
        )

    def navigate_by_route(self, route: str) -> None:
        page = self._route_to_page.get(route)
        if page is None:
            return
        current = self.pages.currentWidget()
        if current is not page and hasattr(current, "invalidate_pending"):
            current.invalidate_pending()
        self.pages.setCurrentWidget(page)
        self.sidebar.set_active(route)
        if hasattr(page, "refresh"):
            page.refresh()
        elif hasattr(page, "_fetch_today_queue"):
            page._fetch_today_queue()

    def on_menu_changed(self, index: int) -> None:
        """Compatibility entry point for legacy callers using numeric navigation."""

        routes = tuple(self._route_to_page)
        if 0 <= index < len(routes):
            self.navigate_by_route(routes[index])

    def _handle_check_in_requested(self, appointment_id: int) -> None:
        self.view_check_in.search_input.setText(str(appointment_id))
        self.navigate_by_route("check_in")

    def _handle_create_invoice_requested(self, _appointment_id: int) -> None:
        self.navigate_by_route("invoice_management")

    def _handle_pay_invoice_requested(self, invoice_id: int) -> None:
        self.navigate_by_route("payment")
        self.view_payment.set_invoice_id(invoice_id)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "shell"):
            self.shell.set_sidebar_compact(
                event.size().width() < self.SIDEBAR_COMPACT_BREAKPOINT
            )

    def handle_logout(self) -> None:
        if self._logout_in_progress:
            return
        self._logout_in_progress = True
        self._dispose_session()
        self.logout_requested.emit()
        self.close()

    def _dispose_session(self) -> None:
        """Invalidate stale callbacks and release this shell's private client."""

        if self._client_disposed:
            return
        self._client_disposed = True
        for page in self._route_to_page.values():
            page.invalidate_pending()
            page.clear_data()
        self.api_client.clear_access_token()
        session_state.clear()
        self.api_client.close()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._dispose_session()
        super().closeEvent(event)
