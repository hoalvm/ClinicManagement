"""Single-window navigation shell for the patient application."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QResizeEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.core.session import SessionState
from frontend.views.appointment_detail_view import AppointmentDetailView
from frontend.views.appointment_history_view import AppointmentHistoryView
from frontend.views.booking_view import BookingView
from frontend.views.common import BaseApiView
from frontend.views.dashboard_view import DashboardView
from frontend.views.invoice_detail_view import InvoiceDetailView
from frontend.views.invoice_history_view import InvoiceHistoryView
from frontend.views.login_view import LoginView
from frontend.views.medical_history_view import MedicalHistoryView
from frontend.views.medical_result_view import MedicalResultView
from frontend.views.patient_profile_view import PatientProfileView
from frontend.views.register_view import RegisterView
from frontend.widgets.sidebar import Sidebar


class MainWindow(QMainWindow):
    """Own authentication screens and one authenticated QStackedWidget."""

    def __init__(
        self,
        api_client: ApiClient,
        session: SessionState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self.session = session
        self._history: list[str] = []
        self._handling_expiry = False
        self.setWindowTitle("ClinicCare Patient Portal")
        self.setMinimumSize(1024, 680)
        self.resize(1240, 800)

        self.root_stack = QStackedWidget()
        self.root_stack.setObjectName("rootStack")
        self.setCentralWidget(self.root_stack)
        self.login_view = LoginView(api_client)
        self.register_view = RegisterView(api_client)
        self.root_stack.addWidget(self.login_view)
        self.root_stack.addWidget(self.register_view)

        self.shell = QWidget()
        shell_layout = QHBoxLayout(self.shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        self.sidebar = Sidebar()
        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("pageStack")
        shell_layout.addWidget(self.sidebar)
        shell_layout.addWidget(self.page_stack, 1)
        self.root_stack.addWidget(self.shell)

        self.dashboard_view = DashboardView(api_client)
        self.profile_view = PatientProfileView(api_client, session)
        self.appointments_view = AppointmentHistoryView(api_client)
        self.appointment_detail_view = AppointmentDetailView(api_client)
        self.booking_view = BookingView(api_client)
        self.medical_history_view = MedicalHistoryView(api_client)
        self.medical_result_view = MedicalResultView(api_client)
        self.invoice_history_view = InvoiceHistoryView(api_client)
        self.invoice_detail_view = InvoiceDetailView(api_client)
        self.pages: dict[str, BaseApiView] = {
            "dashboard": self.dashboard_view,
            "profile": self.profile_view,
            "appointments": self.appointments_view,
            "appointment_detail": self.appointment_detail_view,
            "booking": self.booking_view,
            "medical_history": self.medical_history_view,
            "medical_result": self.medical_result_view,
            "invoice_history": self.invoice_history_view,
            "invoice_detail": self.invoice_detail_view,
        }
        for page in self.pages.values():
            self.page_stack.addWidget(page)
            page.session_expired.connect(self._session_expired)

        self._connect_navigation()
        self.root_stack.setCurrentWidget(self.login_view)
        self._sync_sidebar_mode()

    def _connect_navigation(self) -> None:
        self.login_view.register_requested.connect(
            lambda: self.root_stack.setCurrentWidget(self.register_view)
        )
        self.login_view.login_succeeded.connect(self._login_succeeded)
        self.register_view.back_requested.connect(self._show_login)
        self.register_view.registration_succeeded.connect(self._registration_succeeded)
        self.sidebar.navigation_requested.connect(self._sidebar_navigation)
        self.sidebar.logout_requested.connect(self._logout)

        self.dashboard_view.appointment_requested.connect(self.show_appointment)
        self.dashboard_view.route_requested.connect(self._sidebar_navigation)
        self.profile_view.profile_updated.connect(self.sidebar.set_user)
        self.appointments_view.appointment_requested.connect(self.show_appointment)
        self.appointments_view.book_requested.connect(self.show_booking)
        self.booking_view.back_requested.connect(lambda: self.navigate("appointments", push=True))
        self.booking_view.appointment_booked.connect(self.show_appointment)
        self.appointment_detail_view.back_requested.connect(self.go_back)
        self.appointment_detail_view.medical_record_requested.connect(self.show_medical_result)
        self.appointment_detail_view.invoice_requested.connect(self.show_invoice)
        self.medical_history_view.medical_record_requested.connect(self.show_medical_result)
        self.medical_result_view.back_requested.connect(self.go_back)
        self.medical_result_view.appointment_requested.connect(self.show_appointment)
        self.invoice_history_view.invoice_requested.connect(self.show_invoice)
        self.invoice_detail_view.back_requested.connect(self.go_back)
        self.invoice_detail_view.appointment_requested.connect(self.show_appointment)

    def _login_succeeded(self, token: str, user: object) -> None:
        current_user = user if isinstance(user, dict) else {}
        self.api_client.set_access_token(token)
        self.session.set_authenticated(token, current_user)
        self.sidebar.set_user(current_user)
        self._handling_expiry = False
        self._history.clear()
        self.root_stack.setCurrentWidget(self.shell)
        self.navigate("dashboard", push=True)

    def login_as(self, token: str, current_user: dict) -> None:
        """Bỏ qua màn hình login và đi thẳng vào dashboard (dùng khi đã xác thực từ bên ngoài)."""
        self.api_client.set_access_token(token)
        self.session.set_authenticated(token, current_user)
        self.sidebar.set_user(current_user)
        self._handling_expiry = False
        self._history.clear()
        self.root_stack.setCurrentWidget(self.shell)
        self.navigate("dashboard", push=True)

    def _registration_succeeded(self, username: str) -> None:
        self._show_login()
        self.login_view.set_username(username)
        self.login_view.feedback.show_message(
            "Account created",
            "Your patient account is ready. Enter your password to sign in.",
            severity="success",
        )

    def _show_login(self) -> None:
        self.register_view.invalidate_pending()
        self.register_view.clear_data()
        self.root_stack.setCurrentWidget(self.login_view)
        self.login_view.username.setFocus(Qt.FocusReason.OtherFocusReason)

    def _show_patient_page(self, page: BaseApiView) -> None:
        """Switch pages while silencing responses from the page being left."""

        current = self.page_stack.currentWidget()
        if isinstance(current, BaseApiView) and current is not page:
            current.invalidate_pending()
        self.page_stack.setCurrentWidget(page)

    def _sidebar_navigation(self, route: str) -> None:
        self._history.clear()
        self.navigate(route, push=True)

    def navigate(self, route: str, *, push: bool = True) -> None:
        page = self.pages.get(route)
        if page is None:
            return
        if push and (not self._history or self._history[-1] != route):
            self._history.append(route)
        self._show_patient_page(page)
        sidebar_route = {
            "appointment_detail": "appointments",
            "medical_result": "medical_history",
            "invoice_detail": "invoice_history",
        }.get(route, route)
        self.sidebar.set_active(sidebar_route)
        activate = getattr(page, "activate", None)
        if callable(activate) and route in {
            "dashboard",
            "profile",
            "appointments",
            "medical_history",
            "invoice_history",
        }:
            activate()
        elif route == "booking":
            self.booking_view.reset_flow()

    def show_booking(self) -> None:
        self._history.append("booking")
        self.booking_view.reset_flow()
        self._show_patient_page(self.booking_view)
        self.sidebar.set_active("booking")

    def show_appointment(self, appointment_id: int) -> None:
        self._history.append("appointment_detail")
        self._show_patient_page(self.appointment_detail_view)
        self.sidebar.set_active("appointments")
        self.appointment_detail_view.activate(appointment_id)

    def show_medical_result(self, medical_record_id: int) -> None:
        self._history.append("medical_result")
        self._show_patient_page(self.medical_result_view)
        self.sidebar.set_active("medical_history")
        self.medical_result_view.activate(medical_record_id)

    def show_invoice(self, invoice_id: int) -> None:
        self._history.append("invoice_detail")
        self._show_patient_page(self.invoice_detail_view)
        self.sidebar.set_active("invoice_history")
        self.invoice_detail_view.activate(invoice_id)

    def go_back(self) -> None:
        if self._history:
            self._history.pop()
        route = self._history[-1] if self._history else "dashboard"
        self.navigate(route, push=False)

    def _logout(self) -> None:
        self._clear_session()
        self.login_view.reset()
        self._show_login()

    def _session_expired(self) -> None:
        if self._handling_expiry or not self.session.is_authenticated:
            return
        self._handling_expiry = True
        self._clear_session()
        self.login_view.reset()
        self._show_login()
        QMessageBox.warning(
            self,
            "Session expired",
            "Session expired. Please login again.",
        )

    def _clear_session(self) -> None:
        self.api_client.clear_access_token()
        self.session.clear()
        self._history.clear()
        for page in self.pages.values():
            page.invalidate_pending()
            page.clear_data()
        self.page_stack.setCurrentWidget(self.dashboard_view)
        self.sidebar.set_active("")
        self.sidebar.clear_user()

    def _sync_sidebar_mode(self) -> None:
        if hasattr(self, "sidebar"):
            self.sidebar.set_compact(self.width() < 1100)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._sync_sidebar_mode()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.api_client.close()
        super().closeEvent(event)


if __name__ == "__main__":
    import sys

    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    from frontend.core.config import get_frontend_settings
    from frontend.core.session import SessionState
    from frontend.style import APP_STYLE

    settings = get_frontend_settings()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(APP_STYLE)

    portal_client = ApiClient(
        base_url=settings.api_base_url,
        timeout=settings.api_timeout_seconds,
    )
    portal_session = SessionState()
    portal_window = MainWindow(api_client=portal_client, session=portal_session)
    portal_window.show()
    sys.exit(app.exec())

