"""Regression coverage for the responsive doctor workspace."""

from collections.abc import Iterator
from threading import Event
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QAbstractItemView, QApplication

import frontend.app as doctor_app
from frontend.app import DoctorDashboard, DoctorScheduleView, MedicalExamView
from frontend.style import APP_STYLE
from frontend.ui.design_system import ViewState


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    application.setStyleSheet(APP_STYLE)
    yield application


def _appointment() -> dict:
    return {
        "AppointmentID": 241,
        "StartTime": "08:00",
        "EndTime": "08:30",
        "Status": "CHECKED_IN",
        "Reason": "Đau đầu kéo dài, chóng mặt và mất ngủ trong nhiều ngày " * 4,
        "Patient": {
            "FullName": "Nguyễn Hoàng Minh Anh với tên hồ sơ rất dài",
            "Phone": "0901 234 567",
            "Gender": "FEMALE",
            "DateOfBirth": "1994-06-18",
            "Address": "128 Nguyễn Thị Minh Khai, Phường Võ Thị Sáu, Quận 3 " * 3,
        },
    }


class _ControllableScheduleWorker(QObject):
    """Signal-compatible worker used to drive each state deterministically."""

    success = Signal(list)
    error = Signal(str)
    unauthorized = Signal(str)
    finished = Signal()

    def __init__(self, _doctor_id: int, _token: str) -> None:
        super().__init__()
        self.started = False
        self.running = False

    def start(self) -> None:
        self.started = True
        self.running = True

    def isRunning(self) -> bool:  # noqa: N802 - Qt-compatible test double
        return self.running

    def resolve(self, items: list[dict]) -> None:
        self.running = False
        self.success.emit(items)
        self.finished.emit()

    def reject(self, message: str) -> None:
        self.running = False
        self.error.emit(message)
        self.finished.emit()


def test_schedule_table_is_read_only_and_preserves_full_text(
    qt_app: QApplication,
) -> None:
    host = SimpleNamespace(token="test-token", doctor_id=7)
    view = DoctorScheduleView(host)
    appointment = _appointment()
    view.render_table([appointment])
    view.resize(920, 600)
    view.show()
    qt_app.processEvents()

    reason_item = view.table.item(0, 3)
    status_item = view.table.item(0, 4)
    assert view.table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    assert not reason_item.flags() & Qt.ItemFlag.ItemIsEditable
    assert reason_item.toolTip() == appointment["Reason"].strip()
    assert status_item.data(doctor_app.STATUS_ROLE) == "CHECKED_IN"
    assert view.table.horizontalScrollBar().maximum() == 0

    view.close()
    view.deleteLater()
    qt_app.processEvents()


def test_schedule_state_host_covers_loading_empty_error_retry_and_content(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workers: list[_ControllableScheduleWorker] = []

    def make_worker(doctor_id: int, token: str) -> _ControllableScheduleWorker:
        worker = _ControllableScheduleWorker(doctor_id, token)
        workers.append(worker)
        return worker

    monkeypatch.setattr(doctor_app, "FetchScheduleWorker", make_worker)
    view = DoctorScheduleView(SimpleNamespace(token="test-token", doctor_id=7))

    assert view.state_host.state is ViewState.EMPTY
    assert view.state_host.stack.currentWidget() is view.state_host.empty

    view.load_schedule()
    assert workers[0].started
    assert view.state_host.state is ViewState.LOADING
    assert view.state_host.stack.currentWidget() is view.state_host.loading_page
    assert not view.btn_refresh.isEnabled()

    workers[0].resolve([])
    assert view.state_host.state is ViewState.EMPTY
    assert view.btn_refresh.isEnabled()

    view.load_schedule()
    workers[1].reject("Mất kết nối máy chủ")
    assert view.state_host.state is ViewState.ERROR
    assert view.state_host.stack.currentWidget() is view.state_host.error
    assert "Mất kết nối" in view.state_host.error.description_label.text()

    view.state_host.error.action_button.click()
    assert len(workers) == 3
    assert workers[2].started
    assert view.state_host.state is ViewState.LOADING

    workers[2].resolve([_appointment()])
    assert view.state_host.state is ViewState.CONTENT
    assert view.state_host.stack.currentWidget() is view.table
    assert view.table.rowCount() == 1

    view.close()
    view.deleteLater()
    qt_app.processEvents()


def test_schedule_worker_keeps_event_loop_responsive(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker_started = Event()
    release_worker = Event()

    def wait_in_background(worker: doctor_app.FetchScheduleWorker) -> None:
        worker_started.set()
        release_worker.wait(timeout=1)
        worker.success.emit([])

    monkeypatch.setattr(doctor_app.FetchScheduleWorker, "run", wait_in_background)
    view = DoctorScheduleView(SimpleNamespace(token="test-token", doctor_id=7))
    event_loop_ticks: list[bool] = []

    view.load_schedule()
    assert worker_started.wait(timeout=1)
    QTimer.singleShot(0, lambda: event_loop_ticks.append(True))
    qt_app.processEvents()

    assert event_loop_ticks == [True]
    assert view.state_host.state is ViewState.LOADING
    assert view.worker is not None and view.worker.isRunning()

    release_worker.set()
    assert view.worker.wait(1000)
    qt_app.processEvents()
    assert view.state_host.state is ViewState.EMPTY

    view.close()
    view.deleteLater()
    qt_app.processEvents()


def test_schedule_unauthorized_expires_dashboard_only_once(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor_app.FetchScheduleWorker, "start", lambda _worker: None)
    dashboard = DoctorDashboard(
        {
            "access_token": "expired-token",
            "doctor_id": 7,
            "doctor_name": "Bác sĩ kiểm thử",
        }
    )
    logout_events: list[bool] = []
    dashboard.logout_requested.connect(lambda: logout_events.append(True))

    dashboard.schedule_view._on_schedule_unauthorized("Phiên không còn hợp lệ")
    dashboard.schedule_view.session_expired.emit()

    assert dashboard.schedule_view.state_host.state is ViewState.ERROR
    assert logout_events == [True]
    dashboard.deleteLater()
    qt_app.processEvents()


def test_exam_reflows_without_horizontal_overflow_or_overlapping_fields(
    qt_app: QApplication,
) -> None:
    host = SimpleNamespace(token="test-token", doctor_id=7)
    view = MedicalExamView(host)
    view.load_patient_data(_appointment())
    view.resize(1000, 660)
    view.show()
    qt_app.processEvents()

    assert view._stacked_layout is True
    assert view.right_panel.geometry().top() > view.left_panel.geometry().bottom()
    assert view.scroll_area.horizontalScrollBar().maximum() == 0
    assert view.txt_symptoms.geometry().bottom() < view.txt_diagnosis.geometry().top()
    assert view.txt_diagnosis.geometry().bottom() < view.txt_notes.geometry().top()

    view.in_med.setText("Paracetamol giải phóng kéo dài")
    view.in_dosage.setText("500 mg")
    instructions = (
        "Uống một viên sau ăn, ngày hai lần trong bảy ngày; không tự ý tăng liều "
        "và liên hệ phòng khám nếu xuất hiện dấu hiệu bất thường."
    )
    view.in_instructions.setText(instructions)
    view.add_medicine()

    assert view.table_med.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    assert view.table_med.wordWrap()
    assert view.table_med.item(0, 3).toolTip() == instructions
    assert view.table_med.rowHeight(0) > 44
    assert not view.table_med.item(0, 0).flags() & Qt.ItemFlag.ItemIsEditable

    view.close()
    view.deleteLater()
    qt_app.processEvents()


def test_doctor_shell_collapses_and_exam_returns_to_two_columns_when_wide(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor_app.FetchScheduleWorker, "start", lambda _worker: None)
    dashboard = DoctorDashboard(
        {
            "access_token": "test-token",
            "doctor_id": 7,
            "doctor_name": "Nguyễn Văn Bác Sĩ Tên Dài",
            "license_number": "CCHN-001",
        }
    )

    dashboard.resize(1080, 660)
    dashboard.show()
    qt_app.processEvents()
    assert dashboard.sidebar.is_compact is True
    assert dashboard.sidebar.schedule_button.text() == ""
    assert dashboard.sidebar.schedule_button.accessibleName() == "Lịch khám hôm nay"

    dashboard.resize(1280, 800)
    dashboard.go_to_exam(_appointment())
    qt_app.processEvents()
    assert dashboard.sidebar.is_compact is True
    assert dashboard.exam_view._stacked_layout is False
    assert dashboard.exam_view.scroll_area.horizontalScrollBar().maximum() == 0
    assert dashboard.sidebar.exam_button.isEnabled()
    assert dashboard.sidebar.exam_button.isChecked()

    dashboard.resize(dashboard.SIDEBAR_COMPACT_BREAKPOINT - 1, 660)
    qt_app.processEvents()
    assert dashboard.sidebar.is_compact is True
    assert dashboard.exam_view._stacked_layout is False
    assert dashboard.exam_view.scroll_area.horizontalScrollBar().maximum() == 0

    dashboard.resize(dashboard.SIDEBAR_COMPACT_BREAKPOINT, 660)
    qt_app.processEvents()
    assert dashboard.sidebar.is_compact is False
    assert dashboard.exam_view._stacked_layout is False
    assert dashboard.exam_view.scroll_area.horizontalScrollBar().maximum() == 0

    dashboard.resize(1440, 900)
    qt_app.processEvents()
    assert dashboard.sidebar.is_compact is False

    dashboard.close()
    dashboard.deleteLater()
    qt_app.processEvents()
