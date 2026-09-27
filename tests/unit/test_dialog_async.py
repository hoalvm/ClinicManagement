"""Regression tests for non-blocking appointment action dialogs."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from frontend.api.api_client import ApiClient
from frontend.style import APP_STYLE
from frontend.views.cancel_dialog import CancelAppointmentDialog
from frontend.views.reschedule_dialog import RescheduleAppointmentDialog
from frontend.widgets import async_task_controller


class _DeferredPool:
    def __init__(self) -> None:
        self.workers = []

    def start(self, worker) -> None:
        self.workers.append(worker)


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    previous_style = application.styleSheet()
    application.setStyleSheet(APP_STYLE)
    yield application
    application.setStyleSheet(previous_style)


@pytest.fixture
def deferred_pool(monkeypatch: pytest.MonkeyPatch) -> _DeferredPool:
    pool = _DeferredPool()

    class _ThreadPoolProxy:
        @staticmethod
        def globalInstance():  # noqa: N802
            return pool

    monkeypatch.setattr(async_task_controller, "QThreadPool", _ThreadPoolProxy)
    return pool


def _appointment() -> dict[str, object]:
    return {
        "appointment_id": 42,
        "appointment_date": "2026-10-01",
        "start_time": "09:00",
        "end_time": "09:30",
        "doctor": {
            "doctor_id": 7,
            "full_name": "Bác sĩ Nguyễn Văn An",
            "specialty": "Nội tổng quát",
        },
    }


def test_cancel_dialog_runs_once_without_blocking_caller(
    qt_app: QApplication,
    deferred_pool: _DeferredPool,
) -> None:
    client = MagicMock(spec=ApiClient)
    client.post.return_value = {"appointment_id": 42, "status": "CANCELLED"}
    dialog = CancelAppointmentDialog(client, _appointment())
    assert any(
        "01/10/2026" in label.text() for label in dialog.findChildren(QLabel)
    )
    emitted: list[dict[str, object]] = []
    dialog.appointment_canceled.connect(emitted.append)

    dialog._submit_cancel()
    dialog._submit_cancel()

    assert len(deferred_pool.workers) == 1
    assert not dialog.confirm_button.isEnabled()
    client.post.assert_not_called()

    deferred_pool.workers[0].run()
    qt_app.processEvents()

    client.post.assert_called_once()
    assert emitted == [{"appointment_id": 42, "status": "CANCELLED"}]
    dialog.deleteLater()


def test_reschedule_dialog_loads_and_submits_through_workers(
    qt_app: QApplication,
    deferred_pool: _DeferredPool,
) -> None:
    client = MagicMock(spec=ApiClient)

    def get(path: str, **_kwargs: object) -> object:
        if path == "/api/v1/catalog/doctors":
            return [
                {
                    "doctor_id": 7,
                    "full_name": "Bác sĩ Nguyễn Văn An",
                    "specialty_name": "Nội tổng quát",
                    "clinic_name": "Cơ sở Trung tâm",
                }
            ]
        return {
            "has_schedule": True,
            "slots": [
                {
                    "start_time": "10:00",
                    "end_time": "10:30",
                    "is_available": True,
                }
            ],
        }

    client.get.side_effect = get
    client.post.return_value = {"appointment_id": 42, "status": "PENDING"}
    dialog = RescheduleAppointmentDialog(client, _appointment())
    assert "01/10/2026" in dialog.summary_current_label.text()
    emitted: list[dict[str, object]] = []
    dialog.appointment_rescheduled.connect(emitted.append)

    assert len(deferred_pool.workers) == 1
    client.get.assert_not_called()
    deferred_pool.workers[0].run()
    qt_app.processEvents()

    assert len(deferred_pool.workers) == 2
    deferred_pool.workers[1].run()
    qt_app.processEvents()
    assert dialog.slot_combo.count() == 1
    assert dialog.save_button.isEnabled()

    dialog._submit_reschedule()
    dialog._submit_reschedule()

    assert len(deferred_pool.workers) == 3
    client.post.assert_not_called()
    deferred_pool.workers[2].run()
    qt_app.processEvents()

    client.post.assert_called_once()
    assert emitted == [{"appointment_id": 42, "status": "PENDING"}]
    dialog.deleteLater()
