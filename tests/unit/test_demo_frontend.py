"""Desktop demo contract: server clock, tickets, invoice entry, and payments."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QDate, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QLineEdit, QPushButton, QTableWidget

from frontend.api.api_client import ApiClient
from frontend.core.clinic_clock import ClinicClock, clinic_clock
from frontend.views.book_for_patient_view import BookForPatientView
from frontend.views.booking_view import BookingView
from frontend.views.check_in_view import CheckInView
from frontend.views.invoice_view import InvoiceManagementView
from frontend.views.payment_view import PaymentView, demo_transfer_payload


@pytest.fixture
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_demo_clock_rejects_naive_time_and_keeps_fixed_date() -> None:
    clock = ClinicClock()
    with pytest.raises(ValueError, match="múi giờ"):
        clock.set_from_payload(
            {"clinic_now": "2026-10-05T09:59:00", "timezone": "Asia/Ho_Chi_Minh", "demo_mode": True}
        )
    clock.set_from_payload(
        {
            "clinic_now": "2026-10-05T09:59:00+07:00",
            "timezone": "Asia/Ho_Chi_Minh",
            "demo_mode": True,
        }
    )
    assert clock.today_qdate() == QDate(2026, 10, 5)
    assert clock.now().hour == 9
    assert "DỮ LIỆU MẪU" in clock.display_label()
    assert "Giờ mô phỏng" in clock.display_label()


def test_sample_data_clock_advances_when_server_uses_live_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from frontend.core import clinic_clock as clinic_clock_module

    elapsed = [100.0]
    monkeypatch.setattr(clinic_clock_module, "monotonic", lambda: elapsed[0])
    clock = ClinicClock()
    clock.set_from_payload(
        {
            "clinic_now": "2026-10-06T09:59:00+07:00",
            "timezone": "Asia/Ho_Chi_Minh",
            "demo_mode": True,
            "clock_fixed": False,
        }
    )
    elapsed[0] += 120
    assert clock.now().hour == 10
    assert clock.now().minute == 1
    assert "DỮ LIỆU MẪU" in clock.display_label()
    assert "Giờ phòng khám" in clock.display_label()
    assert "mô phỏng" not in clock.display_label()


def test_booking_dates_follow_new_server_day_after_desktop_stays_open(
    qt_app: QApplication, monkeypatch: pytest.MonkeyPatch,
) -> None:
    clinic_clock.set_from_payload(
        {
            "clinic_now": "2026-10-05T09:59:00+07:00",
            "timezone": "Asia/Ho_Chi_Minh",
            "demo_mode": True,
            "clock_fixed": False,
        }
    )
    monkeypatch.setattr(BookingView, "run_api_task", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(BookForPatientView, "_load_doctors", lambda _self: None)
    patient = BookingView(MagicMock(spec=ApiClient))
    staff = BookForPatientView(MagicMock(spec=ApiClient))
    try:
        clinic_clock.set_from_payload(
            {
                "clinic_now": "2026-10-07T00:01:00+07:00",
                "timezone": "Asia/Ho_Chi_Minh",
                "demo_mode": True,
                "clock_fixed": False,
            }
        )
        patient.reset_flow()
        staff.refresh()
        for editor in (patient.step2_date_edit, patient.slot_date_edit, staff.date_edit):
            assert editor.minimumDate() == QDate(2026, 10, 7)
            assert editor.date() >= QDate(2026, 10, 7)
    finally:
        clinic_clock.clear()
        patient.deleteLater()
        staff.deleteLater()
        qt_app.processEvents()


def test_desktop_booking_and_checkin_use_server_date(qt_app: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    clinic_clock.set_from_payload(
        {
            "clinic_now": "2026-10-05T09:59:00+07:00",
            "timezone": "Asia/Ho_Chi_Minh",
            "demo_mode": True,
        }
    )
    try:
        monkeypatch.setattr(BookForPatientView, "_load_doctors", lambda _self: None)
        patient = BookingView(MagicMock(spec=ApiClient))
        staff = BookForPatientView(MagicMock(spec=ApiClient))
        check_in = CheckInView(MagicMock(spec=ApiClient))
        check_in.run_api_task = MagicMock()  # type: ignore[method-assign]

        assert patient.step2_date_edit.minimumDate() == QDate(2026, 10, 5)
        assert staff.date_edit.date() == QDate(2026, 10, 5)
        check_in.search_and_load()
        operation = check_in.run_api_task.call_args.args[1]
        operation()
        assert check_in.api_client.get.call_args.kwargs["params"]["appointment_date"] == "2026-10-05"
    finally:
        clinic_clock.clear()
        for view in (patient, staff, check_in):
            view.deleteLater()
        qt_app.processEvents()


def test_check_in_uses_server_ticket_number(qt_app: QApplication) -> None:
    view = CheckInView(MagicMock(spec=ApiClient))
    view.search_and_load = lambda **_kwargs: None  # type: ignore[method-assign]
    appointment = {
        "appointment_id": 27,
        "appointment_date": "2026-10-05",
        "start_time": "10:00:00",
        "patient": {"full_name": "Nguyễn Văn An", "phone": "0900000001"},
        "doctor": {"full_name": "Lý Võ Mỹ Hoa"},
        "clinic": {"clinic_name": "Quận 1"},
        "queue_number": "A-001",
        "check_in_at": "2026-10-05T10:01:00+07:00",
    }
    view._on_check_in_success(appointment)
    assert view.queue_num_input.text() == "A-001"
    assert "10:01" in view._ticket_text()
    assert "Nguyễn Văn An" in view._ticket_text()
    view.deleteLater()
    qt_app.processEvents()


def test_invoice_form_stays_open_with_invalid_fields(qt_app: QApplication) -> None:
    view = InvoiceManagementView(MagicMock(spec=ApiClient))
    checked: list[bool] = []

    def inspect_dialog() -> None:
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, QDialog)
        table = dialog.findChild(QTableWidget)
        assert table is not None
        assert table.rowCount() == 1
        assert table.item(0, 0).text() == ""
        submit = next(button for button in dialog.findChildren(QPushButton) if button.text() == "Tạo hóa đơn")
        submit.click()
        assert dialog.isVisible()
        assert any(label.isVisible() and "mã lịch hẹn" in label.text() for label in dialog.findChildren(QLabel))
        dialog.findChild(QLineEdit).setText("27")
        submit.click()
        assert dialog.isVisible()
        checked.append(True)
        dialog.reject()

    QTimer.singleShot(0, inspect_dialog)
    view._create_invoice_dialog()
    assert checked == [True]
    view.api_client.post.assert_not_called()
    view.deleteLater()
    qt_app.processEvents()


def test_payment_uses_cash_tender_and_server_change(qt_app: QApplication) -> None:
    client = MagicMock(spec=ApiClient)
    view = PaymentView(client)
    view._current_invoice = {"invoice_id": 7, "total_amount": "200000.00"}
    view.cash_input.setText("250.000")
    view.run_api_task = MagicMock()  # type: ignore[method-assign]

    view._process_payment()
    view.run_api_task.call_args.args[1]()
    assert client.post.call_args.kwargs["json"] == {
        "payment_method": "CASH",
        "amount": "250000",
    }

    view._on_payment_success(
        {
            "invoice_id": 7,
            "total_amount": "200000.00",
            "amount_received": "250000.00",
            "change_due": "50000.00",
            "payment_method": "CASH",
            "patient_name": "Nguyễn Văn An",
        }
    )
    assert "50.000 ₫" in view.receipt_text.text()
    view.deleteLater()
    qt_app.processEvents()


def test_transfer_qr_is_demo_only_and_never_posts_before_confirmation(qt_app: QApplication) -> None:
    client = MagicMock(spec=ApiClient)
    view = PaymentView(client)
    view._show_invoice_details({"invoice_id": 9, "total_amount": "200000.00", "status": "UNPAID"})
    view.rb_transfer.setChecked(True)

    assert demo_transfer_payload(9, Decimal("200000.00")) == "CLINIC-INVOICE|9|200000.00"
    assert view.qr_label.toolTip() == "CLINIC-INVOICE|9|200000.00"
    assert not view.qr_label.pixmap().isNull()
    client.post.assert_not_called()

    view.run_api_task = MagicMock()  # type: ignore[method-assign]
    view._process_payment()
    view.run_api_task.call_args.args[1]()
    assert client.post.call_args.kwargs["json"] == {
        "payment_method": "TRANSFER",
        "amount": "200000.00",
    }
    view.deleteLater()
    qt_app.processEvents()


def test_production_transfer_requires_bank_reference_and_manual_reconciliation(
    qt_app: QApplication, monkeypatch,
) -> None:
    from types import SimpleNamespace

    monkeypatch.setattr(
        "frontend.views.payment_view.get_frontend_settings",
        lambda: SimpleNamespace(app_mode="production"),
    )
    client = MagicMock(spec=ApiClient)
    view = PaymentView(client)
    view._show_invoice_details(
        {"invoice_id": 9, "total_amount": "200000.00", "status": "UNPAID"}
    )
    view.rb_transfer.setChecked(True)
    assert view.qr_title.isHidden()
    assert view.transfer_reference_input.isHidden() is False

    view.run_api_task = MagicMock()  # type: ignore[method-assign]
    view._process_payment()
    view.run_api_task.assert_not_called()

    view.transfer_reference_input.setText("BANK-20261006-001")
    view.transfer_verified_check.setChecked(True)
    view._process_payment()
    view.run_api_task.call_args.args[1]()
    assert client.post.call_args.kwargs["json"] == {
        "payment_method": "TRANSFER",
        "amount": "200000.00",
        "external_reference": "BANK-20261006-001",
        "manual_verified": True,
    }
    view.deleteLater()
    qt_app.processEvents()
