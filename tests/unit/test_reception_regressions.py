"""Regression tests for reception, booking, invoicing, and payment workflows."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from backend.app.core.clock import clinic_today
from backend.app.core.exceptions import ConflictError, ValidationError
from backend.app.core.phone import normalize_phone
from backend.app.schemas.auth import RegisterRequest
from backend.app.schemas.patient import PatientProfileUpdate
from backend.app.schemas.reception import (
    BookForPatientRequest,
    CreateInvoiceRequest,
    InvoiceItemCreate,
    ProcessPaymentRequest,
)
from backend.app.services.reception_service import ReceptionService
from frontend.api.api_client import ApiClient
from frontend.views.check_in_view import CheckInView
from frontend.views.common import BaseApiView


def _appointment(status: str = "CONFIRMED") -> SimpleNamespace:
    return SimpleNamespace(
        appointment_id=29,
        patient_id=4,
        clinic_id=2,
        status=status,
        reason="Tai kham",
        appointment_date=clinic_today(),
        start_time=time(9, 30),
        end_time=time(10, 0),
        doctor_id=8,
    )


def test_check_in_requires_confirmation_and_uses_server_queue() -> None:
    session = MagicMock()
    appointment = _appointment("PENDING")
    session.get.return_value = appointment
    session.scalars.return_value.all.return_value = []
    service = ReceptionService(session)
    service._to_appointment_item = lambda item: item  # type: ignore[method-assign]

    with pytest.raises(ConflictError):
        service.check_in_patient(appointment.appointment_id)
    session.commit.assert_not_called()

    appointment.status = "CONFIRMED"
    result = service.check_in_patient(appointment.appointment_id)

    assert result.status == "CHECKED_IN"
    assert result.queue_number == "A-001"
    assert result.check_in_at is not None
    session.commit.assert_called_once_with()


@pytest.mark.parametrize("terminal_status", ["COMPLETED", "CANCELLED"])
def test_terminal_appointments_cannot_be_cancelled_or_rescheduled(
    terminal_status: str,
) -> None:
    session = MagicMock()
    session.get.return_value = _appointment(terminal_status)
    service = ReceptionService(session)

    with pytest.raises(ConflictError):
        service.cancel_appointment(29, "Benh nhan yeu cau")
    with pytest.raises(ConflictError):
        service.reschedule_appointment(
            29,
            date.today() + timedelta(days=2),
            time(10, 0),
            time(10, 30),
        )

    session.commit.assert_not_called()


def test_booking_and_rescheduling_reject_past_dates() -> None:
    service = ReceptionService(MagicMock())
    past_date = clinic_today() - timedelta(days=1)
    request = BookForPatientRequest(
        patient_id=1,
        doctor_id=2,
        appointment_date=past_date,
        start_time=time(9, 30),
        end_time=time(10, 0),
    )

    with pytest.raises(ValidationError):
        service.book_for_patient(request)

    service.session.get.return_value = _appointment()
    with pytest.raises(ValidationError):
        service.reschedule_appointment(29, past_date, time(9, 30), time(10, 0))


def _invoice(total: str = "150000") -> SimpleNamespace:
    patient_user = SimpleNamespace(full_name="Nguyen Van An", phone="0900000001")
    doctor_user = SimpleNamespace(full_name="Nguyen Minh Anh")
    appointment = SimpleNamespace(
        patient=SimpleNamespace(user=patient_user),
        doctor=SimpleNamespace(user=doctor_user),
        clinic_id=1,
        appointment_date=date.today(),
    )
    return SimpleNamespace(
        invoice_id=6,
        appointment_id=20,
        created_at=datetime.now(),
        total_amount=Decimal(total),
        status="UNPAID",
        appointment=appointment,
    )


def test_cash_payment_rejects_shortfall_and_records_only_invoice_total() -> None:
    session = MagicMock()
    invoice = _invoice()
    session.get.return_value = invoice
    session.scalar.return_value = None
    service = ReceptionService(session)

    with pytest.raises(ValidationError):
        service.process_payment(
            invoice.invoice_id,
            ProcessPaymentRequest(payment_method="CASH", amount=Decimal("149999")),
        )
    session.commit.assert_not_called()

    result = service.process_payment(
        invoice.invoice_id,
        ProcessPaymentRequest(payment_method="CASH", amount=Decimal("200000")),
    )

    payment = session.add.call_args.args[0]
    assert payment.amount == Decimal("150000")
    assert result.status == "PAID"
    assert result.amount_received == Decimal("200000")
    assert result.change_due == Decimal("50000")
    session.commit.assert_called_once_with()


def test_transfer_payment_must_match_invoice_total() -> None:
    session = MagicMock()
    invoice = _invoice()
    session.get.return_value = invoice
    session.scalar.return_value = None
    service = ReceptionService(session)

    with pytest.raises(ValidationError):
        service.process_payment(
            invoice.invoice_id,
            ProcessPaymentRequest(payment_method="TRANSFER", amount=Decimal("200000")),
        )

    session.add.assert_not_called()
    session.commit.assert_not_called()


def test_invoice_total_is_calculated_from_items_and_duplicate_is_blocked() -> None:
    patient_user = SimpleNamespace(full_name="Nguyen Van An", phone="0900000001")
    doctor_user = SimpleNamespace(full_name="Nguyen Minh Anh")
    appointment = SimpleNamespace(
        status="COMPLETED",
        patient=SimpleNamespace(user=patient_user),
        doctor=SimpleNamespace(
            user=doctor_user,
            specialty=SimpleNamespace(specialty_name="Nội tổng quát"),
        ),
        appointment_date=date.today(),
    )
    record = SimpleNamespace(
        prescription=SimpleNamespace(
            items=[SimpleNamespace(medicine_name="Natri clorid 0,9% súc họng", quantity=2)]
        )
    )
    session = MagicMock()
    session.get.return_value = appointment
    session.scalar.side_effect = [record, None]

    def assign_server_values() -> None:
        invoice_model = session.add.call_args_list[0].args[0]
        invoice_model.invoice_id = 77
        invoice_model.created_at = datetime.now()

    session.flush.side_effect = assign_server_values
    service = ReceptionService(session)
    request = CreateInvoiceRequest(
        appointment_id=29,
        items=[
            InvoiceItemCreate(item_name="Phí khám Nội tổng quát", quantity=1, unit_price=150000),
            InvoiceItemCreate(item_name="Natri clorid 0,9% súc họng", quantity=2, unit_price=200000),
        ],
    )

    result = service.create_invoice(request)

    assert result.total_amount == Decimal("550000")
    assert appointment.status == "COMPLETED"
    assert session.add.call_count == 3
    session.commit.assert_called_once_with()

    duplicate_session = MagicMock()
    duplicate_session.get.return_value = appointment
    duplicate_session.scalar.side_effect = [record, SimpleNamespace(invoice_id=77)]
    with pytest.raises(ConflictError):
        ReceptionService(duplicate_session).create_invoice(request)
    duplicate_session.add.assert_not_called()

    unprescribed = CreateInvoiceRequest(
        appointment_id=29,
        items=[
            InvoiceItemCreate(item_name="Phí khám Nội tổng quát", quantity=1, unit_price=150000),
            InvoiceItemCreate(item_name="Thuốc không kê", quantity=1, unit_price=10000),
        ],
    )
    invalid_session = MagicMock()
    invalid_session.get.return_value = appointment
    invalid_session.scalar.side_effect = [record, None]
    with pytest.raises(ValidationError):
        ReceptionService(invalid_session).create_invoice(unprescribed)
    invalid_session.add.assert_not_called()


def test_phone_whitespace_is_normalized_at_input_boundaries() -> None:
    assert normalize_phone(" 090 123 4567 ") == "0901234567"
    registration = RegisterRequest(
        username="patient01",
        password="Strong#123",
        confirm_password="Strong#123",
        full_name="Nguyen Van An",
        phone="090 123 4567",
    )
    profile = PatientProfileUpdate(phone="090 123 4567")

    assert registration.phone == "0901234567"
    assert profile.phone == "0901234567"


def test_check_in_uses_server_queue_number_and_ticket_contains_patient_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application = QApplication.instance() or QApplication([])
    monkeypatch.setattr(BaseApiView, "run_api_task", lambda *_args, **_kwargs: False)
    view = CheckInView(MagicMock(spec=ApiClient))
    base_item = {
        "appointment_id": 29,
        "appointment_date": "2026-10-04",
        "start_time": "09:30:00",
        "end_time": "10:00:00",
        "status": "CONFIRMED",
        "patient": {"full_name": "Vu Dinh Trong", "phone": "0900000005"},
        "doctor": {"full_name": "Nguyen Minh Anh"},
        "clinic": {"clinic_name": "Phong kham Tan Binh"},
    }

    view._on_candidates_loaded({"items": [base_item]})
    assert view.queue_num_input.text() == "Tự động"

    checked_item = {**base_item, "status": "CHECKED_IN"}
    second_item = {**base_item, "appointment_id": 30, "status": "PENDING"}
    view._on_candidates_loaded({"items": [checked_item, second_item]})
    assert view.queue_num_input.text() == "Tự động"

    view.search_and_load = lambda **_kwargs: None  # type: ignore[method-assign]
    view._on_check_in_success(
        {
            **base_item,
            "status": "CHECKED_IN",
            "queue_number": "A-001",
            "check_in_at": "2026-10-05T10:01:00+07:00",
        }
    )
    ticket = view._ticket_text()
    assert "A-001" in ticket
    assert "10:01" in ticket
    assert "Vu Dinh Trong" in ticket
    assert "0900000005" in ticket
    assert "Nguyen Minh Anh" in ticket

    beeps: list[bool] = []
    monkeypatch.setattr(QApplication, "beep", staticmethod(lambda: beeps.append(True)))
    view._call_current_number()
    assert beeps == [True]

    view.deleteLater()
    application.processEvents()

