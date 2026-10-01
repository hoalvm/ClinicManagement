"""Regression tests for patient history filter query parameters."""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication

from frontend.api.api_client import ApiClient
from frontend.views.appointment_history_view import AppointmentHistoryView
from frontend.views.invoice_history_view import InvoiceHistoryView
from frontend.views.medical_history_view import MedicalHistoryView


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    yield application


def _capture_load(view, client: MagicMock) -> dict[str, object]:
    captured: dict[str, object] = {}

    def capture(_key, operation, *_args, **_kwargs):
        operation()
        captured.update(client.get.call_args.kwargs["params"])
        return True

    view.run_api_task = capture  # type: ignore[method-assign]
    view.load()
    return captured


def test_appointment_history_sends_date_specialty_and_clinic_filters(
    qt_app: QApplication,
) -> None:
    client = MagicMock(spec=ApiClient)
    view = AppointmentHistoryView(client)
    view.date_filter.setChecked(True)
    view.date_edit.setDate(QDate(2026, 10, 1))
    view.specialty.addItem("Tất cả", "")
    view.specialty.addItem("Tim mạch", "Tim mạch")
    view.specialty.setCurrentIndex(1)
    view.clinic.addItem("Tất cả", "")
    view.clinic.addItem("Trung tâm", "Trung tâm")
    view.clinic.setCurrentIndex(1)

    params = _capture_load(view, client)

    assert params["appointment_date"] == "2026-10-01"
    assert params["specialty"] == "Tim mạch"
    assert params["clinic"] == "Trung tâm"
    view.deleteLater()
    qt_app.processEvents()


def test_medical_history_sends_examination_filters(qt_app: QApplication) -> None:
    client = MagicMock(spec=ApiClient)
    view = MedicalHistoryView(client)
    view.date_filter.setChecked(True)
    view.date_edit.setDate(QDate(2026, 10, 1))
    view.specialty.addItem("Tất cả", "")
    view.specialty.addItem("Nội khoa", "Nội khoa")
    view.specialty.setCurrentIndex(1)
    view.clinic.addItem("Tất cả", "")
    view.clinic.addItem("Quận 1", "Quận 1")
    view.clinic.setCurrentIndex(1)

    params = _capture_load(view, client)

    assert params["examination_date"] == "2026-10-01"
    assert params["specialty"] == "Nội khoa"
    assert params["clinic"] == "Quận 1"
    view.deleteLater()
    qt_app.processEvents()


def test_invoice_history_sends_appointment_date_filter(qt_app: QApplication) -> None:
    client = MagicMock(spec=ApiClient)
    view = InvoiceHistoryView(client)
    view.date_filter.setChecked(True)
    view.date_edit.setDate(QDate(2026, 10, 1))

    params = _capture_load(view, client)

    assert params["appointment_date"] == "2026-10-01"
    view.deleteLater()
    qt_app.processEvents()
