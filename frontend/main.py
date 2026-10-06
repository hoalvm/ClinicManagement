from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

import httpx
from PySide6.QtCore import QObject, QThreadPool, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from frontend.admin_dashboard import AdminDashboard
from frontend.api.api_client import ApiClient, ApiError
from frontend.api.workers import ApiWorker
from frontend.api_client import api_client
from frontend.app import DoctorDashboard
from frontend.core.config import get_frontend_settings
from frontend.core.session import SessionState, session_state
from frontend.login_window import LoginWindow
from frontend.main_window import MainWindow
from frontend.reception_dashboard import ReceptionDashboard
from frontend.style import APP_STYLE
from frontend.widgets.focus_visible import install_focus_visible

app: QApplication | None = None
dashboard = None
login: LoginWindow | None = None
doctor_profile_worker = None
doctor_profile_generation = 0


@dataclass(frozen=True)
class _DoctorRouteSnapshot:
    generation: int
    access_token: str
    username: str | None


class _DoctorProfileHandler(QObject):
    """Marshal the profile worker result back onto Qt's GUI thread."""

    def __init__(self, snapshot: _DoctorRouteSnapshot) -> None:
        super().__init__()
        self.snapshot = snapshot

    @Slot(object)
    def success(self, response: object) -> None:
        _open_doctor_dashboard(response, self.snapshot)

    @Slot(object)
    def error(self, error: Exception) -> None:
        _doctor_profile_failed(error, self.snapshot)

    @Slot()
    def finished(self) -> None:
        _clear_doctor_profile_worker(self.snapshot.generation)


doctor_profile_routes: dict[
    int, tuple[ApiWorker, _DoctorProfileHandler, _DoctorRouteSnapshot]
] = {}


def _revoke_server_session_async(token: str) -> None:
    """Revoke the captured bearer token without delaying the desktop logout."""

    logout_url = f"{get_frontend_settings().api_base_url.rstrip('/')}/auth/logout"

    def revoke() -> None:
        with httpx.Client(timeout=3.0) as client:
            client.post(logout_url, headers={"Authorization": f"Bearer {token}"})

    QThreadPool.globalInstance().start(ApiWorker(revoke))


def _next_route_generation() -> int:
    global doctor_profile_generation, doctor_profile_worker
    doctor_profile_generation += 1
    doctor_profile_worker = None
    return doctor_profile_generation


def show_login() -> None:
    global login, dashboard
    _next_route_generation()
    old_token = api_client.token
    if dashboard:
        dashboard.close()
        dashboard = None
    api_client.clear_session()
    if old_token:
        _revoke_server_session_async(old_token)
    if not login:
        login = LoginWindow(on_success=open_dashboard)
    login.reset_for_login()
    login.show()


def open_dashboard() -> None:
    global dashboard, doctor_profile_worker, login
    route_generation = _next_route_generation()
    role = api_client.role

    if role == "ADMIN":
        dashboard = AdminDashboard()
        dashboard.logout_requested.connect(show_login)
        dashboard.show()
        if login:
            login.close()

    elif role == "DOCTOR":
        # Profile lookup is part of login routing and must never block the GUI.
        access_token = api_client.token
        if not access_token:
            if login:
                login.set_routing_pending(False)
            QMessageBox.warning(
                login,
                "Lỗi phiên đăng nhập",
                "Không tìm thấy phiên đăng nhập hợp lệ. Vui lòng đăng nhập lại.",
            )
            return
        snapshot = _DoctorRouteSnapshot(
            generation=route_generation,
            access_token=access_token,
            username=api_client.username,
        )
        if login:
            login.set_routing_pending(True)
            login.hide()
        doctor_profile_worker = ApiWorker(
            lambda token=access_token: _fetch_doctor_profile(token)
        )
        handler = _DoctorProfileHandler(snapshot)
        doctor_profile_routes[route_generation] = (
            doctor_profile_worker,
            handler,
            snapshot,
        )
        doctor_profile_worker.signals.success.connect(handler.success)
        doctor_profile_worker.signals.error.connect(handler.error)
        doctor_profile_worker.signals.finished.connect(handler.finished)
        QThreadPool.globalInstance().start(doctor_profile_worker)

    elif role == "STAFF":
        settings = get_frontend_settings()
        staff_client = ApiClient(
            base_url=settings.api_base_url,
            timeout=settings.api_timeout_seconds,
        )
        staff_client.set_access_token(api_client.token)
        staff_client.set_user_identity(username=api_client.username or "", role=role)

        session_state.set_authenticated(
            access_token=api_client.token,
            current_user={
                "username": api_client.username,
                "role": role,
            },
        )

        dashboard = ReceptionDashboard(api_client=staff_client)
        dashboard.logout_requested.connect(show_login)
        dashboard.show()
        if login:
            login.close()

    elif role == "PATIENT":
        settings = get_frontend_settings()
        portal_client = ApiClient(
            base_url=settings.api_base_url,
            timeout=settings.api_timeout_seconds,
        )
        portal_client.set_access_token(api_client.token)
        portal_client.set_user_identity(username=api_client.username or "", role=role)

        session = SessionState()
        session.set_authenticated(
            access_token=api_client.token,
            current_user={
                "username": api_client.username,
                "role": role,
            },
        )

        dashboard = MainWindow(
            api_client=portal_client,
            session=session,
            central_auth=True,
        )
        dashboard.logout_requested.connect(show_login)
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


def _fetch_doctor_profile(access_token: str) -> dict[str, Any]:
    """Load one profile with credentials captured for this routing attempt."""

    settings = get_frontend_settings()
    profile_client = ApiClient(
        base_url=settings.api_base_url,
        timeout=settings.api_timeout_seconds,
    )
    profile_client.set_access_token(access_token)
    try:
        response = profile_client.get("/api/v1/doctor/profile")
        if not isinstance(response, dict):
            raise TypeError("Doctor profile response must be an object")
        return response
    finally:
        profile_client.close()


def _is_current_doctor_route(snapshot: _DoctorRouteSnapshot) -> bool:
    return (
        snapshot.generation == doctor_profile_generation
        and api_client.role == "DOCTOR"
        and api_client.token == snapshot.access_token
        and api_client.username == snapshot.username
    )


def _open_doctor_dashboard(
    profile_response: object,
    snapshot: _DoctorRouteSnapshot,
) -> None:
    global dashboard, login
    if not _is_current_doctor_route(snapshot):
        return
    if not isinstance(profile_response, dict) or not {
        "doctor_id",
        "doctor_name",
    }.issubset(profile_response):
        _doctor_profile_failed(
            ValueError("Doctor profile response is missing required fields"),
            snapshot,
        )
        return

    session_data = {
        "access_token": snapshot.access_token,
        "doctor_id": profile_response["doctor_id"],
        "doctor_name": profile_response["doctor_name"],
        "license_number": profile_response.get("license_number") or "—",
    }
    dashboard = DoctorDashboard(session_data)
    dashboard.logout_requested.connect(show_login)
    dashboard.show()
    if login:
        login.set_routing_pending(False)
        login.close()


def _doctor_profile_failed(
    error: Exception,
    snapshot: _DoctorRouteSnapshot,
) -> None:
    if not _is_current_doctor_route(snapshot):
        return
    if login:
        login.set_routing_pending(False)
        login.show()
    message = (
        error.message
        if isinstance(error, ApiError)
        else "Không thể tải hồ sơ bác sĩ. Vui lòng kiểm tra kết nối và thử lại."
    )
    QMessageBox.warning(login, "Lỗi hồ sơ bác sĩ", message)


def _clear_doctor_profile_worker(generation: int) -> None:
    global doctor_profile_worker
    route = doctor_profile_routes.pop(generation, None)
    if route and doctor_profile_worker is route[0]:
        doctor_profile_worker = None


def main() -> int:
    global app, login
    app = QApplication.instance() or QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(APP_STYLE)
    install_focus_visible(app)
    login = LoginWindow(on_success=open_dashboard)
    login.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
