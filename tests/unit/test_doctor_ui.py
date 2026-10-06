"""Regression coverage for the responsive doctor workspace."""

from collections.abc import Iterator
from datetime import date
from threading import Event
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QAbstractItemView, QApplication, QMessageBox, QToolButton

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


class _ControllableCompleteWorker(QObject):
    finished = Signal(bool, str)
    instances: list["_ControllableCompleteWorker"] = []

    def __init__(self, appt_id: int, payload: dict, token: str) -> None:
        super().__init__()
        self.appt_id = appt_id
        self.payload = payload
        self.token = token
        self.running = False
        self.instances.append(self)

    def start(self) -> None:
        self.running = True

    def isRunning(self) -> bool:  # noqa: N802 - Qt-compatible test double
        return self.running

    def resolve(self, ok: bool, message: str) -> None:
        self.running = False
        self.finished.emit(ok, message)


class _ControllableContextWorker(QObject):
    success = Signal(dict)
    error = Signal(str)
    unauthorized = Signal(str)
    finished = Signal()
    instances: list["_ControllableContextWorker"] = []

    def __init__(self, appointment_id: int, token: str) -> None:
        super().__init__()
        self.appointment_id = appointment_id
        self.token = token
        self.instances.append(self)

    def start(self) -> None:
        pass

    def resolve(self, context: dict) -> None:
        self.success.emit(context)
        self.finished.emit()

    def reject(self, message: str) -> None:
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


def test_exam_v2_uses_full_width_summary_balanced_body_and_fixed_footer(
    qt_app: QApplication,
) -> None:
    view = MedicalExamView(SimpleNamespace(token="test-token", doctor_id=7))
    view.load_patient_data(_appointment())
    view.resize(1240, 780)
    view.show()
    qt_app.processEvents()

    assert view.header.title == "Khám bệnh"
    assert view.breadcrumb.text() == "← Hàng đợi khám"
    assert view.patient_summary.parent() is view.scroll_content
    assert view.patient_summary.width() > view.left_panel.width()
    assert view.body_layout.columnStretch(0) == 11
    assert view.body_layout.columnStretch(1) == 9
    assert view.txt_symptoms.height() == 120
    assert view.txt_diagnosis.height() == 120
    assert view.txt_notes.height() == 96
    assert view.spin_qty.value() == 1
    assert view.prescription_empty.isVisible()
    assert not view.table_med.isVisible()
    assert view.footer.parent() is view
    assert view.footer.geometry().top() >= view.scroll_area.geometry().bottom()
    assert view.btn_finish.text() == "Lưu và hoàn tất khám"

    view.close()
    view.deleteLater()
    qt_app.processEvents()


def test_prescription_supports_local_edit_delete_and_single_overflow_action(
    qt_app: QApplication,
) -> None:
    view = MedicalExamView(SimpleNamespace(token="test-token", doctor_id=7))
    view.load_patient_data(_appointment())
    view.show()
    qt_app.processEvents()

    view.in_med.setText("Paracetamol")
    view.in_dosage.setText("500 mg")
    view.in_instructions.setText("Uống sau ăn")
    view.add_medicine()

    assert view.table_med.rowCount() == 1
    assert view.table_med.columnCount() == 5
    assert not view.prescription_empty.isVisible()
    assert view.table_med.isVisible()
    action = view.table_med.cellWidget(0, 4).findChild(
        QToolButton,
        "tableMoreButton",
    )
    assert action is not None
    assert action.text() == "⋯"
    assert action.menu() is None
    assert view.has_unsaved_changes()

    view.edit_medicine(0)
    assert view.btn_add_medicine.text() == "Lưu thay đổi"
    assert view.btn_cancel_medicine_edit.isVisible()
    view.in_instructions.setText("Uống sau ăn, ngày hai lần")
    view.add_medicine()

    assert view.table_med.rowCount() == 1
    assert view.table_med.item(0, 3).text() == "Uống sau ăn, ngày hai lần"
    assert view.btn_add_medicine.text() == "Thêm vào đơn"
    assert not view.btn_cancel_medicine_edit.isVisible()
    assert view.spin_qty.value() == 1

    view.delete_medicine(0)
    assert view.table_med.rowCount() == 0
    assert view.prescription_empty.isVisible()
    assert not view.table_med.isVisible()

    view.close()
    view.deleteLater()
    qt_app.processEvents()


def test_exam_confirms_completion_and_keeps_api_payload_compatible(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ControllableCompleteWorker.instances.clear()
    monkeypatch.setattr(doctor_app, "CompleteExamWorker", _ControllableCompleteWorker)
    view = MedicalExamView(SimpleNamespace(token="test-token", doctor_id=7))
    view.load_patient_data(_appointment())
    view.txt_diagnosis.setText("Đau đầu do thiếu ngủ")

    monkeypatch.setattr(view, "_ask_confirmation", lambda *_args, **_kwargs: False)
    view.submit_examination()
    assert _ControllableCompleteWorker.instances == []

    monkeypatch.setattr(view, "_ask_confirmation", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(QMessageBox, "information", lambda *_args, **_kwargs: None)
    completed: list[bool] = []
    view.examination_done.connect(lambda: completed.append(True))
    view.submit_examination()

    worker = _ControllableCompleteWorker.instances[0]
    assert worker.appt_id == _appointment()["AppointmentID"]
    assert worker.payload == {
        "symptoms": _appointment()["Reason"].strip(),
        "diagnosis": "Đau đầu do thiếu ngủ",
        "notes": None,
        "prescription_items": [],
    }
    assert not view.btn_finish.isEnabled()

    worker.resolve(True, "Đã lưu")
    assert view.btn_finish.isEnabled()
    assert view.btn_finish.text() == "Lưu và hoàn tất khám"
    assert completed == [True]
    assert not view.has_unsaved_changes()

    view.close()
    view.deleteLater()
    qt_app.processEvents()


def test_production_exam_requires_history_load_and_displays_prior_care(
    qt_app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ControllableContextWorker.instances.clear()
    monkeypatch.setattr(
        doctor_app, "get_frontend_settings", lambda: SimpleNamespace(app_mode="production")
    )
    monkeypatch.setattr(doctor_app, "FetchClinicalContextWorker", _ControllableContextWorker)
    view = MedicalExamView(SimpleNamespace(token="test-token", doctor_id=7))
    view.load_patient_data(_appointment())

    first = _ControllableContextWorker.instances[0]
    assert first.appointment_id == 241
    assert not view.btn_finish.isEnabled()
    assert not view.btn_add_medicine.isEnabled()
    assert "CHƯA ĐƯỢC GHI NHẬN" in view.allergy_status_label.text()

    first.resolve(
        {
            "appointment_id": 241,
            "allergy_status": "NOT_DOCUMENTED",
            "prior_records_has_more": False,
            "prior_records": [
                {
                    "examination_date": "2026-09-12T10:00:00",
                    "doctor_name": "Bác sĩ A",
                    "symptoms": "Ho khan",
                    "diagnosis": "Viêm họng",
                    "notes": "Theo dõi",
                    "prescription_items": [
                        {
                            "medicine_name": "Thuốc mẫu",
                            "dosage": "500 mg",
                            "quantity": 2,
                            "instructions": "Theo đơn",
                        }
                    ],
                }
            ],
        }
    )
    assert view.btn_finish.isEnabled()
    assert not view.btn_add_medicine.isEnabled()
    assert not view.in_med.isEnabled()
    assert "chưa hỗ trợ kê đơn" in view.prescription_notice.text()
    view.in_med.setText("Thuốc thử")
    view.add_medicine()
    assert view.table_med.rowCount() == 0
    assert "Viêm họng" in view.clinical_context_history.toPlainText()
    assert "Thuốc mẫu" in view.clinical_context_history.toPlainText()

    view.load_clinical_context()
    second = _ControllableContextWorker.instances[1]
    assert not view.btn_finish.isEnabled()
    second.resolve(
        {
            "appointment_id": 241,
            "allergy_status": "NOT_DOCUMENTED",
            "prior_records_has_more": True,
            "prior_records": [],
        }
    )
    assert "còn hồ sơ cũ hơn" in view.clinical_context_status.text()

    view.load_clinical_context()
    third = _ControllableContextWorker.instances[2]
    third.reject("Mất kết nối")
    assert not view.btn_finish.isEnabled()
    assert "Mất kết nối" in view.clinical_context_status.text()

    view.close()
    view.deleteLater()
    qt_app.processEvents()


def test_production_past_in_progress_visit_requires_visible_late_entry_reason(
    qt_app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ControllableContextWorker.instances.clear()
    _ControllableCompleteWorker.instances.clear()
    monkeypatch.setattr(
        doctor_app, "get_frontend_settings", lambda: SimpleNamespace(app_mode="production")
    )
    monkeypatch.setattr(doctor_app.clinic_clock, "today", lambda: date(2026, 10, 6))
    monkeypatch.setattr(doctor_app, "FetchClinicalContextWorker", _ControllableContextWorker)
    monkeypatch.setattr(doctor_app, "CompleteExamWorker", _ControllableCompleteWorker)
    appointment = _appointment()
    appointment["AppointmentDate"] = "2026-10-05"
    appointment["Status"] = "IN_PROGRESS"
    view = MedicalExamView(SimpleNamespace(token="test-token", doctor_id=7))
    view.load_patient_data(appointment)
    view.show()
    qt_app.processEvents()
    assert view.late_entry_panel.isVisible()
    _ControllableContextWorker.instances[-1].resolve(
        {
            "appointment_id": appointment["AppointmentID"],
            "allergy_status": "NOT_DOCUMENTED",
            "prior_records_has_more": False,
            "prior_records": [],
        }
    )
    view.txt_diagnosis.setText("Đau đầu do thiếu ngủ")
    monkeypatch.setattr(view, "_ask_confirmation", lambda *_args, **_kwargs: True)
    view.submit_examination()
    assert not _ControllableCompleteWorker.instances

    view.txt_late_reason.setText("Gián đoạn hệ thống tại thời điểm kết thúc ca")
    view.submit_examination()
    assert _ControllableCompleteWorker.instances[-1].payload["late_entry_reason"] == (
        "Gián đoạn hệ thống tại thời điểm kết thúc ca"
    )
    view.close()
    view.deleteLater()
    qt_app.processEvents()


def test_dashboard_warns_before_discarding_dirty_examination(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor_app.FetchScheduleWorker, "start", lambda _worker: None)
    dashboard = DoctorDashboard(
        {
            "access_token": "test-token",
            "doctor_id": 7,
            "doctor_name": "Nguyễn Văn Bác Sĩ",
            "license_number": "CCHN-001",
        }
    )
    dashboard.go_to_exam(_appointment())
    dashboard.exam_view.txt_diagnosis.setText("Chẩn đoán chưa lưu")
    assert dashboard.exam_view.has_unsaved_changes()

    monkeypatch.setattr(
        dashboard.exam_view,
        "_ask_confirmation",
        lambda *_args, **_kwargs: False,
    )
    assert dashboard.go_to_schedule() is False
    assert dashboard.stack.currentWidget() is dashboard.exam_view
    assert dashboard.sidebar.exam_button.isChecked()

    monkeypatch.setattr(
        dashboard.exam_view,
        "_ask_confirmation",
        lambda *_args, **_kwargs: True,
    )
    assert dashboard.go_to_schedule() is True
    assert dashboard.stack.currentWidget() is dashboard.schedule_view
    assert not dashboard.exam_view.has_unsaved_changes()

    dashboard.close()
    dashboard.deleteLater()
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
    assert dashboard.sidebar.schedule_button.accessibleName() == "Hàng đợi khám"

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
