"""Offscreen geometry regressions for the supported compact role viewports."""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QScrollArea, QTableView

from frontend.api.api_client import ApiClient
from frontend.views.appointment_management_view import AppointmentManagementView
from frontend.views.booking_view import BookingView
from frontend.views.check_in_view import CheckInView
from frontend.views.common import BaseApiView
from frontend.views.invoice_view import InvoiceManagementView
from frontend.views.payment_history_view import PaymentHistoryView
from frontend.views.reception_dashboard_view import ReceptionDashboardView

LONG_NAME = "Nguyễn Văn Một Hai Ba Bốn Năm Sáu Bảy Tám Chín Mười Rất Dài"
LONG_TEXT = (
    "123 Đường Một Địa Chỉ Rất Dài, Phường Hai, Quận Ba, "
    "Thành phố Hồ Chí Minh. "
)


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    yield application


def test_patient_booking_steps_fit_minimum_viewport_and_scroll_vertically(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(BaseApiView, "run_api_task", lambda *_args, **_kwargs: False)
    view = BookingView(MagicMock(spec=ApiClient))
    view.resize(946, 680)
    view.show()
    view.selected_specialty = {
        "specialty_id": 1,
        "specialty_name": "Chuyên khoa Nội tổng hợp có tên rất dài",
    }
    view.selected_doctor = {
        "doctor_id": 1,
        "full_name": LONG_NAME,
        "specialty_name": LONG_NAME,
        "clinic_name": LONG_NAME,
        "clinic_address": LONG_TEXT * 4,
    }
    view.selected_date = "2026-09-30"
    view.selected_slot = ("10:00", "10:30")

    for step in (1, 2):
        view._go_to_step(step)
        qt_app.processEvents()
        page = view.step_layout.currentWidget()
        assert page.minimumSizeHint().width() <= view.step_container.width()
        for scroll in page.findChildren(QScrollArea):
            if scroll.isVisible():
                assert scroll.horizontalScrollBar().maximum() == 0

    view._go_to_step(3)
    qt_app.processEvents()
    confirm_scroll = view.step_layout.currentWidget()
    assert isinstance(confirm_scroll, QScrollArea)
    assert confirm_scroll.horizontalScrollBar().maximum() == 0
    assert confirm_scroll.verticalScrollBar().maximum() > 0
    assert view.summary_details_lbl.wordWrap()
    assert (
        view.summary_details_lbl.height()
        >= view.summary_details_lbl.fontMetrics().lineSpacing() * 6
    )

    view.close()
    view.deleteLater()
    qt_app.processEvents()


def test_staff_operational_tables_fit_1022_pixel_content_width(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(BaseApiView, "run_api_task", lambda *_args, **_kwargs: False)
    client = MagicMock(spec=ApiClient)
    appointment = {
        "appointment_id": 123456,
        "appointment_date": "2026-09-27",
        "start_time": "10:30:00",
        "status": "PENDING",
        "patient": {"full_name": LONG_NAME, "phone": "0912345678"},
        "doctor": {"full_name": LONG_NAME},
    }
    invoice = {
        "invoice_id": 123456,
        "appointment_id": 987654,
        "patient_name": LONG_NAME,
        "patient_phone": "0912345678",
        "doctor_name": LONG_NAME,
        "total_amount": 999_999_999,
        "status": "UNPAID",
    }

    dashboard = ReceptionDashboardView(client)
    dashboard._on_stats_loaded(
        {
            "recent_checked_in": [appointment],
            "today_total_appointments": 128,
            "today_pending_confirm": 42,
            "today_checked_in": 23,
            "unpaid_invoices_count": 56,
        }
    )
    check_in = CheckInView(client)
    check_in._on_candidates_loaded({"items": [{**appointment, "status": "CONFIRMED"}]})
    appointments = AppointmentManagementView(client)
    appointments._on_appointments_loaded(
        {"items": [appointment], "total": 1, "total_pages": 1}
    )
    invoices = InvoiceManagementView(client)
    invoices._on_invoices_loaded(
        {"items": [invoice], "total": 1, "total_pages": 1}
    )
    payments = PaymentHistoryView(client)
    payments._on_payments_loaded(
        {
            "items": [
                {
                    "payment_id": 123456,
                    "invoice_id": 987654,
                    "patient_name": LONG_NAME,
                    "doctor_name": LONG_NAME,
                    "amount": 999_999_999,
                    "payment_method": "CARD",
                    "payment_date": "2026-09-27T10:30:00",
                }
            ],
            "total": 1,
            "total_pages": 1,
        }
    )

    views = (dashboard, check_in, appointments, invoices, payments)
    for view in views:
        view.resize(1022, 680)
        view.show()
        qt_app.processEvents()
        visible_tables = [
            table for table in view.findChildren(QTableView) if table.isVisible()
        ]
        assert visible_tables
        assert all(table.horizontalScrollBar().maximum() == 0 for table in visible_tables)
        view.close()
        view.deleteLater()
    qt_app.processEvents()
