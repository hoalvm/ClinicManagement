"""Production billing and clinic-scope invariants."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm.attributes import set_committed_value

from backend.app.core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from backend.app.models import Appointment
from backend.app.schemas.reception import (
    BookForPatientRequest,
    CreateInvoiceRequest,
    InvoiceItemCreate,
    ProcessPaymentRequest,
    VerifyPatientIdentityRequest,
)
from backend.app.services import reception_service as module


@pytest.fixture(autouse=True)
def production_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(app_mode="production", appointment_grace_minutes=15),
    )
    monkeypatch.setattr(module, "record_audit_event", lambda *_args, **_kwargs: None)


def _service(*, clinic_ids: list[int] | None = None) -> tuple[module.ReceptionService, MagicMock]:
    session = MagicMock()
    session.scalars.return_value.all.return_value = clinic_ids if clinic_ids is not None else [1]
    return module.ReceptionService(session, staff_user_id=7), session


def _appointment(*, status: str = "COMPLETED", clinic_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        appointment_id=21,
        clinic_id=clinic_id,
        specialty_id=3,
        status=status,
        appointment_date=date(2026, 10, 6),
        start_time=time(9, 0),
        end_time=time(9, 30),
        medical_record=SimpleNamespace(symptoms="Ho khan", diagnosis="Viêm họng"),
        invoice=None,
        patient=SimpleNamespace(user=SimpleNamespace(full_name="Patient A", phone="0900000001")),
        doctor=SimpleNamespace(user=SimpleNamespace(full_name="Doctor A")),
    )


def _charge(price: str = "175000.00") -> SimpleNamespace:
    return SimpleNamespace(
        charge_id=9,
        display_name="Khám Nội tổng quát",
        unit_price=Decimal(price),
    )


def test_staff_without_clinic_assignment_is_denied() -> None:
    with pytest.raises(AuthorizationError):
        _service(clinic_ids=[])


def test_staff_reschedule_rechecks_source_clinic_after_concurrent_patient_move(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, session = _service(clinic_ids=[1])
    appointment = Appointment(appointment_id=21, doctor_id=3, clinic_id=1, status="PENDING")
    session.get.side_effect = [appointment, SimpleNamespace(clinic_id=1)]

    class ConcurrentBooking:
        def __init__(self, _session: object) -> None:
            pass

        def reschedule_for_patient(self, changed: Appointment, *_args: object, **kwargs: object) -> None:
            # BookingService's locked refresh observes the patient's A -> B
            # change before applying the receptionist's requested target A.
            set_committed_value(changed, "clinic_id", 2)
            changed.clinic_id = 1
            changed.status = "CONFIRMED"
            kwargs["before_commit"](changed)
            session.commit()

    monkeypatch.setattr(module, "BookingService", ConcurrentBooking)
    with pytest.raises(AuthorizationError):
        service.reschedule_appointment(
            21, date(2026, 10, 9), time(10), time(10, 30), doctor_id=3
        )
    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()


def test_production_walk_in_requires_birth_date_before_any_write() -> None:
    service, session = _service()
    request = BookForPatientRequest(
        full_name="Patient A",
        phone="0900000001",
        doctor_id=3,
        appointment_date=date(2026, 10, 7),
        start_time=time(10, 0),
        end_time=time(10, 30),
    )
    with pytest.raises(ValidationError):
        service.book_for_patient(request)
    session.add.assert_not_called()


def test_new_walk_in_requires_staff_identity_attestation() -> None:
    service, session = _service()
    request = BookForPatientRequest(
        full_name="Patient A",
        phone="0900000001",
        date_of_birth=date(1990, 4, 3),
        doctor_id=3,
        appointment_date=date(2026, 10, 7),
        start_time=time(10, 0),
        end_time=time(10, 30),
        identity_checked=False,
    )
    with pytest.raises(ValidationError, match="danh tính"):
        service.book_for_patient(request)
    session.add.assert_not_called()


def test_production_invoice_rejects_client_prices_and_uses_catalog_snapshot() -> None:
    service, session = _service()
    appointment = _appointment()
    session.get.return_value = appointment

    with pytest.raises(ValidationError):
        service.create_invoice(
            CreateInvoiceRequest(
                appointment_id=21,
                items=[InvoiceItemCreate(item_name="Khám", quantity=1, unit_price=1)],
            )
        )
    session.add.assert_not_called()

    session.scalar.side_effect = [appointment.medical_record, None]
    session.scalars.return_value.all.return_value = [_charge()]

    def assign_invoice_id() -> None:
        created = session.add.call_args_list[0].args[0]
        created.invoice_id = 88

    session.flush.side_effect = assign_invoice_id
    result = service.create_invoice(CreateInvoiceRequest(appointment_id=21))

    invoice = session.add.call_args_list[0].args[0]
    line = session.add.call_args_list[1].args[0]
    assert invoice.total_amount == Decimal("175000.00")
    assert line.charge_id == 9
    assert line.item_name == "Khám Nội tổng quát"
    assert line.unit_price == Decimal("175000.00")
    assert line.quantity == 1
    assert result.total_amount == Decimal("175000.00")
    session.commit.assert_called_once_with()


def test_invoice_preview_uses_same_catalog_price_and_rejects_wrong_clinic() -> None:
    service, session = _service()
    appointment = _appointment()
    session.get.return_value = appointment
    session.scalars.return_value.all.return_value = [_charge("210000.00")]

    preview = service.invoice_preview(21)
    assert preview.charge_id == 9
    assert preview.total_amount == Decimal("210000.00")
    assert "chưa được giao" in preview.medication_note

    appointment.clinic_id = 2
    with pytest.raises(AuthorizationError):
        service.invoice_preview(21)


def test_production_transfer_requires_manual_evidence_and_persists_it() -> None:
    service, session = _service()
    appointment = _appointment()
    invoice = SimpleNamespace(
        invoice_id=5,
        appointment_id=21,
        appointment=appointment,
        created_at=datetime(2026, 10, 6, 9, 45),
        total_amount=Decimal("175000.00"),
        status="UNPAID",
    )
    session.get.return_value = invoice
    session.scalar.return_value = None

    with pytest.raises(ValidationError):
        service.process_payment(
            5,
            ProcessPaymentRequest(payment_method="TRANSFER", amount=Decimal("175000.00")),
            recorded_by_user_id=7,
        )
    session.add.assert_not_called()

    paid = service.process_payment(
        5,
        ProcessPaymentRequest(
            payment_method="TRANSFER",
            amount=Decimal("175000.00"),
            external_reference="BANK-TXN-12345",
            manual_verified=True,
        ),
        recorded_by_user_id=7,
    )
    payment = session.add.call_args.args[0]
    assert payment.external_reference == "BANK-TXN-12345"
    assert payment.verified_at is not None
    assert payment.recorded_by_user_id == 7
    assert payment.amount_received == Decimal("175000.00")
    assert payment.change_due == Decimal("0.00")
    assert paid.status == "PAID"


def test_production_cash_persists_tender_change_and_actor() -> None:
    service, session = _service()
    invoice = SimpleNamespace(
        invoice_id=5,
        appointment_id=21,
        appointment=_appointment(),
        created_at=datetime(2026, 10, 6, 9, 45),
        total_amount=Decimal("175000.00"),
        status="UNPAID",
    )
    session.get.return_value = invoice
    session.scalar.return_value = None

    service.process_payment(
        5,
        ProcessPaymentRequest(payment_method="CASH", amount=Decimal("200000.00")),
        recorded_by_user_id=7,
    )
    payment = session.add.call_args.args[0]
    assert payment.amount == Decimal("175000.00")
    assert payment.amount_received == Decimal("200000.00")
    assert payment.change_due == Decimal("25000.00")
    assert payment.recorded_by_user_id == 7


def test_production_rejects_late_confirmation_and_check_in(monkeypatch: pytest.MonkeyPatch) -> None:
    service, session = _service()
    now = datetime(2026, 10, 6, 10, 30)
    monkeypatch.setattr(module, "clinic_now", lambda: now)
    monkeypatch.setattr(module, "clinic_naive_now", lambda: now)
    monkeypatch.setattr(module, "clinic_today", lambda: now.date())
    appointment = _appointment(status="PENDING")
    session.get.return_value = appointment

    with pytest.raises(ConflictError):
        service.confirm_appointment(21)
    appointment.status = "CONFIRMED"
    with pytest.raises(ConflictError):
        service.check_in_patient(21)
    session.commit.assert_not_called()


def test_no_show_requires_elapsed_grace_and_records_actor(monkeypatch: pytest.MonkeyPatch) -> None:
    service, session = _service()
    appointment = _appointment(status="CONFIRMED")
    session.get.return_value = appointment
    service._to_appointment_item = lambda item: item  # type: ignore[method-assign]
    monkeypatch.setattr(module, "clinic_naive_now", lambda: datetime(2026, 10, 6, 9, 45))

    with pytest.raises(ConflictError):
        service.mark_no_show(21)
    assert appointment.status == "CONFIRMED"
    session.commit.assert_not_called()

    monkeypatch.setattr(module, "clinic_naive_now", lambda: datetime(2026, 10, 6, 9, 46))
    result = service.mark_no_show(21)
    assert result.status == "NO_SHOW"
    assert result.no_show_by_user_id == 7
    assert result.no_show_reason_code == "NO_ARRIVAL"
    session.commit.assert_called_once_with()


def test_no_show_cannot_overwrite_started_encounter() -> None:
    service, session = _service()
    session.get.return_value = _appointment(status="IN_PROGRESS")
    with pytest.raises(ConflictError):
        service.mark_no_show(21)
    session.commit.assert_not_called()


def test_unconfirmed_request_is_not_a_patient_no_show() -> None:
    service, session = _service()
    session.get.return_value = _appointment(status="PENDING")
    with pytest.raises(ConflictError, match="đã xác nhận"):
        service.mark_no_show(21)
    session.commit.assert_not_called()


def test_confirmed_missed_visit_cannot_be_cancelled_after_grace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, session = _service()
    session.get.return_value = _appointment(status="CONFIRMED")
    monkeypatch.setattr(module, "clinic_naive_now", lambda: datetime(2026, 10, 6, 9, 46))
    with pytest.raises(ConflictError, match="vắng mặt"):
        service.cancel_appointment(21, "Bệnh nhân không đến")
    session.commit.assert_not_called()


def test_prior_day_checked_in_cancellation_requires_care_attestation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, session = _service()
    appointment = _appointment(status="CHECKED_IN")
    session.get.return_value = appointment
    service._to_appointment_item = lambda item: item  # type: ignore[method-assign]
    monkeypatch.setattr(module, "clinic_today", lambda: date(2026, 10, 7))
    events: list[dict[str, object]] = []
    monkeypatch.setattr(
        module, "record_audit_event", lambda _session, **kwargs: events.append(kwargs)
    )

    with pytest.raises(ValidationError, match="xác nhận chưa được khám"):
        service.cancel_appointment(21, "Bệnh nhân rời phòng khám khi chưa được khám")
    assert appointment.status == "CHECKED_IN"
    session.commit.assert_not_called()

    cancelled = service.cancel_appointment(
        21,
        "Bệnh nhân rời phòng khám khi chưa được khám",
        care_not_started=True,
    )
    assert cancelled.status == "CANCELLED"
    assert events[-1]["action"] == "APPOINTMENT_LATE_CHECKIN_CANCELLED"
    assert events[-1]["details"]["care_not_started"] is True
    session.commit.assert_called_once_with()


def test_cross_clinic_identity_lookup_requires_exact_id_dob_and_attestation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, session = _service()
    patient = SimpleNamespace(
        patient_id=33,
        date_of_birth=date(1990, 4, 3),
        is_walk_in=False,
        user=SimpleNamespace(full_name="Patient B", role="PATIENT", is_active=True),
    )
    session.get.return_value = patient
    events: list[dict[str, object]] = []
    monkeypatch.setattr(
        module,
        "record_audit_event",
        lambda _session, **kwargs: events.append(kwargs),
    )
    request = VerifyPatientIdentityRequest(
        patient_id=33,
        date_of_birth=date(1990, 4, 3),
        clinic_id=1,
        identity_checked=True,
    )
    result = service.verify_patient_identity(request)
    assert result.patient_id == 33
    assert result.full_name == "Patient B"
    assert events[-1]["outcome"] == "SUCCESS"
    session.commit.assert_called_once_with()

    with pytest.raises(NotFoundError):
        service.verify_patient_identity(request.model_copy(update={"date_of_birth": date(1991, 4, 3)}))
    assert events[-1]["outcome"] == "DENIED"

    with pytest.raises(AuthorizationError):
        service.verify_patient_identity(request.model_copy(update={"clinic_id": 2}))

    with pytest.raises(ValidationError):
        service.verify_patient_identity(request.model_copy(update={"identity_checked": False}))
