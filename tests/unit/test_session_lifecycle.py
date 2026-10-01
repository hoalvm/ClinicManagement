"""Regression tests for central-login and staff-session lifecycle boundaries."""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from frontend.api.api_client import ApiClient
from frontend.core.session import session_state
from frontend.login_window import LoginWindow
from frontend.reception_dashboard import ReceptionDashboard
from frontend.views.common import BaseApiView


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    yield application


def test_staff_session_expiry_disposes_client_and_invalidates_every_view(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(BaseApiView, "run_api_task", lambda *_args, **_kwargs: False)
    client = MagicMock(spec=ApiClient)
    client.token = "staff-token"
    session_state.set_authenticated(
        "staff-token",
        {"username": "staff01", "role": "STAFF"},
    )
    window = ReceptionDashboard(client)
    generations = {
        route: page._generation for route, page in window._route_to_page.items()
    }
    logout_events: list[bool] = []
    window.logout_requested.connect(lambda: logout_events.append(True))

    # Use a non-dashboard page to guard the shell-wide session-expired wiring.
    window.view_payment_history.session_expired.emit()

    assert logout_events == [True]
    assert not session_state.is_authenticated
    assert all(
        page._generation == generations[route] + 1
        for route, page in window._route_to_page.items()
    )
    client.clear_access_token.assert_called_once_with()
    client.close.assert_called_once_with()

    # A second late 401 from an already-invalidated worker must be harmless.
    window.view_check_in.session_expired.emit()
    assert logout_events == [True]
    client.clear_access_token.assert_called_once_with()
    client.close.assert_called_once_with()
    window.deleteLater()
    qt_app.processEvents()


def test_login_password_is_cleared_and_routing_lock_survives_worker_cleanup(
    qt_app: QApplication,
) -> None:
    window = LoginWindow(on_success=lambda: None)
    window.username_input.setText("doctor01")
    window.password_input.setText("Secret123!")
    window.set_routing_pending(True)

    # LoginWorker.finished arrives after LoginWorker.success starts Doctor routing.
    window._login_worker = MagicMock()
    window._login_cleanup()

    assert window.password_input.text() == ""
    assert not window.username_input.isEnabled()
    assert not window.password_input.isEnabled()
    assert not window.login_btn.isEnabled()

    window.password_input.setText("NeverPersistThis")
    window.reset_for_login()
    assert window.password_input.text() == ""
    assert window.username_input.isEnabled()
    assert window.password_input.isEnabled()
    assert window.login_btn.isEnabled()
    window.close()
    window.deleteLater()
    qt_app.processEvents()


def test_central_login_exposes_patient_registration_entry_point(
    qt_app: QApplication,
) -> None:
    window = LoginWindow(on_success=lambda: None)

    assert window.register_btn.text() == "Đăng ký tài khoản bệnh nhân"
    assert window.register_btn.isEnabled()

    window.close()
    window.deleteLater()
    qt_app.processEvents()


def test_doctor_routing_uses_token_snapshot_and_ignores_stale_result(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import frontend.main as frontend_main

    class _Pool:
        def __init__(self) -> None:
            self.started: list[object] = []

        def start(self, worker: object) -> None:
            self.started.append(worker)

    class _ThreadPoolProxy:
        @staticmethod
        def globalInstance() -> _Pool:  # noqa: N802
            return pool

    class _SignalStub:
        def connect(self, _callback: object) -> None:
            return

    class _DashboardStub:
        def __init__(self, session_data: dict[str, object]) -> None:
            self.session_data = session_data
            self.logout_requested = _SignalStub()
            self.shown = False

        def show(self) -> None:
            self.shown = True

        def close(self) -> None:
            return

    pool = _Pool()
    fetched_tokens: list[str] = []

    def fetch_profile(token: str) -> dict[str, object]:
        fetched_tokens.append(token)
        return {"doctor_id": 7, "doctor_name": "Bác sĩ An"}

    login = LoginWindow(on_success=lambda: None)
    login.show()
    monkeypatch.setattr(frontend_main, "login", login)
    monkeypatch.setattr(frontend_main, "dashboard", None)
    monkeypatch.setattr(frontend_main, "doctor_profile_worker", None)
    monkeypatch.setattr(frontend_main, "doctor_profile_generation", 0)
    monkeypatch.setattr(frontend_main, "doctor_profile_routes", {})
    monkeypatch.setattr(frontend_main, "QThreadPool", _ThreadPoolProxy)
    monkeypatch.setattr(frontend_main, "DoctorDashboard", _DashboardStub)
    monkeypatch.setattr(frontend_main, "_fetch_doctor_profile", fetch_profile)
    monkeypatch.setattr(frontend_main.api_client, "role", "DOCTOR")
    monkeypatch.setattr(frontend_main.api_client, "username", "doctor01")
    monkeypatch.setattr(frontend_main.api_client, "token", "token-a")

    frontend_main.open_dashboard()
    first_generation = frontend_main.doctor_profile_generation
    first_worker, first_handler, _first_snapshot = (
        frontend_main.doctor_profile_routes[first_generation]
    )
    assert login.isHidden()
    assert not login.login_btn.isEnabled()

    # A new authenticated identity supersedes the route that is still in flight.
    frontend_main.api_client.username = "doctor02"
    frontend_main.api_client.token = "token-b"
    frontend_main.open_dashboard()
    second_generation = frontend_main.doctor_profile_generation
    second_worker, second_handler, _second_snapshot = (
        frontend_main.doctor_profile_routes[second_generation]
    )

    first_worker.operation()
    second_worker.operation()
    assert fetched_tokens == ["token-a", "token-b"]

    first_handler.success({"doctor_id": 1, "doctor_name": "Stale doctor"})
    assert frontend_main.dashboard is None
    first_handler.error(RuntimeError("stale error"))
    assert login.isHidden()

    second_handler.success({"doctor_id": 2, "doctor_name": "Current doctor"})
    assert isinstance(frontend_main.dashboard, _DashboardStub)
    assert frontend_main.dashboard.session_data["access_token"] == "token-b"
    assert frontend_main.dashboard.session_data["doctor_id"] == 2
    assert frontend_main.dashboard.shown

    first_handler.finished()
    second_handler.finished()
    assert frontend_main.doctor_profile_routes == {}
    login.close()
    login.deleteLater()
    qt_app.processEvents()
