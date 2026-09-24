import sys
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from frontend.admin_dashboard import AdminDashboard
from frontend.api.api_client import ApiClient
from frontend.api_client import api_client
from frontend.core.config import get_frontend_settings
from frontend.core.session import SessionState
from frontend.login_window import LoginWindow
from frontend.main_window import MainWindow
from frontend.style import APP_STYLE

app = QApplication(sys.argv)
app.setFont(QFont("Segoe UI", 10))
app.setStyleSheet(APP_STYLE)

dashboard = None
login = None


def show_login():
    global login, dashboard
    if dashboard:
        dashboard.close()
        dashboard = None
    if not login:
        login = LoginWindow(on_success=open_dashboard)
    login.show()


def open_dashboard():
    global dashboard, login
    role = api_client.role

    if role == "ADMIN":
        dashboard = AdminDashboard()
        dashboard.logout_requested.connect(show_login)
        dashboard.show()
        if login:
            login.close()

    elif role in ("PATIENT", "DOCTOR"):
        settings = get_frontend_settings()
        portal_client = ApiClient(
            base_url=settings.api_base_url,
            timeout=settings.api_timeout_seconds,
        )
        portal_client.set_access_token(api_client.token)

        session = SessionState()
        session.set_authenticated(
            access_token=api_client.token,
            current_user={
                "username": api_client.username,
                "role": role,
            },
        )

        dashboard = MainWindow(api_client=portal_client, session=session)
        dashboard.login_as(
            token=api_client.token,
            current_user={"username": api_client.username, "role": role},
        )
        dashboard.show()
        if login:
            login.close()

    else:
        QMessageBox.critical(
            login,
            "Không có quyền truy cập",
            f"Tài khoản '{api_client.username}' (role: {role or 'không xác định'}) "
            f"không được hỗ trợ trong hệ thống này.",
        )


login = LoginWindow(on_success=open_dashboard)
login.show()

sys.exit(app.exec())