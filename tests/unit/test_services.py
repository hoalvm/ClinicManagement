"""Service-layer tests using repositories/mocks rather than an alternate database."""

from datetime import date, datetime, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from backend.app.schemas.auth import LoginRequest, RegisterRequest
from backend.app.schemas.patient import PatientProfileUpdate
from backend.app.services.appointment_service import AppointmentService
from backend.app.services.auth_service import AuthService
from backend.app.services.dashboard_service import DashboardService
from backend.app.services.invoice_service import InvoiceService
from backend.app.services.medical_record_service import MedicalRecordService
from backend.app.services.patient_service import PatientService


def registration_payload() -> RegisterRequest:
    return RegisterRequest(
        username="patient03",
        password="Password123!",
        confirm_password="Password123!",
        full_name="Nguyen Van C",
        phone="0900000003",
        email="patient03@example.com",
        date_of_birth=date(2000, 1, 1),
        gender="MALE",
        address="Ho Chi Minh City",
    )


def user_stub(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "user_id": 1,
        "username": "patient01",
        "password_hash": "$argon2id$unit-test-hash",
        "full_name": "Nguyen Van A",
        "phone": "0900000000",
        "email": "patient01@example.com",
        "role": "PATIENT",
        "is_active": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def patient_stub(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "patient_id": 10,
        "user_id": 1,
        "user": user_stub(),
        "date_of_birth": date(2000, 1, 1),
        "gender": "MALE",
        "address": "Ho Chi Minh City",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def doctor_stub() -> SimpleNamespace:
    return SimpleNamespace(
        doctor_id=3,
        user=user_stub(
            user_id=30,
            username="doctor03",
            full_name="Nguyen Van B",
            phone="0900000001",
            email="doctor@example.com",
            role="DOCTOR",
        ),
        specialty=SimpleNamespace(specialty_name="Internal Medicine"),
        license_number="LIC-003",
    )


def clinic_stub() -> SimpleNamespace:
    return SimpleNamespace(
        clinic_id=1,
        clinic_name="Central Clinic",
        address="1 Clinic Street",
        phone="0280000000",
    )


def appointment_stub(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "appointment_id": 100,
        "patient_id": 10,
        "appointment_date": date(2026, 9, 19),
        "start_time": time(9, 0),
        "end_time": time(9, 30),
        "reason": "Follow-up",
        "status": "COMPLETED",
        "doctor": doctor_stub(),
        "clinic": clinic_stub(),
        "medical_record": SimpleNamespace(medical_record_id=200),
        "invoice": SimpleNamespace(invoice_id=300),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_register_creates_patient_and_commits_one_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock()
    service = AuthService(session)
    service.users = MagicMock()
    service.patients = MagicMock()
    service.users.get_by_username.return_value = None
    service.users.add.side_effect = lambda user: setattr(user, "user_id", 7) or user
    service.patients.add.side_effect = lambda patient: setattr(patient, "patient_id", 17) or patient
    monkeypatch.setattr(
        "backend.app.services.auth_service.hash_password",
        lambda _password: "$argon2id$test-hash",
    )

    result = service.register(registration_payload())

    created_user = service.users.add.call_args.args[0]
    created_patient = service.patients.add.call_args.args[0]
    assert result.user_id == 7
    assert result.patient_id == 17
    assert created_user.role == "PATIENT"
    assert created_user.password_hash == "$argon2id$test-hash"
    assert created_user.password_hash != registration_payload().password
    assert created_patient.user_id == 7
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_register_rejects_duplicate_username_without_writing() -> None:
    session = MagicMock()
    service = AuthService(session)
    service.users = MagicMock()
    service.patients = MagicMock()
    service.users.get_by_username.return_value = user_stub()

    with pytest.raises(ConflictError):
        service.register(registration_payload())

    service.users.add.assert_not_called()
    service.patients.add.assert_not_called()
    session.commit.assert_not_called()


def test_register_rolls_back_user_when_patient_insert_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock()
    service = AuthService(session)
    service.users = MagicMock()
    service.patients = MagicMock()
    service.users.get_by_username.return_value = None
    service.users.add.side_effect = lambda user: setattr(user, "user_id", 7) or user
    service.patients.add.side_effect = SQLAlchemyError("patient insert failed")
    monkeypatch.setattr(
        "backend.app.services.auth_service.hash_password", lambda _password: "test-hash"
    )

    with pytest.raises(Exception, match="Unable to register patient"):
        service.register(registration_payload())

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


def test_login_success_returns_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AuthService(MagicMock())
    service.users = MagicMock()
    service.users.get_by_username.return_value = user_stub()
    monkeypatch.setattr(
        "backend.app.services.auth_service.verify_password",
        lambda _password, _password_hash: True,
    )
    monkeypatch.setattr(
        "backend.app.services.auth_service.create_access_token",
        lambda **_claims: "signed-token",
    )

    result = service.login(LoginRequest(username="patient01", password="Password123!"))

    assert result.access_token == "signed-token"
    assert result.token_type == "bearer"


def test_login_rejects_non_patient_accounts(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AuthService(MagicMock())
    service.users = MagicMock()
    service.users.get_by_username.return_value = user_stub(role="DOCTOR")
    monkeypatch.setattr(
        "backend.app.services.auth_service.verify_password",
        lambda _password, _password_hash: True,
    )

    with pytest.raises(AuthenticationError, match="Incorrect username or password"):
        service.login(LoginRequest(username="doctor01", password="Doctor123!"))


@pytest.mark.parametrize("user", [None, user_stub(is_active=False), user_stub()])
def test_login_rejects_unknown_inactive_or_wrong_password(
    user: SimpleNamespace | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = AuthService(MagicMock())
    service.users = MagicMock()
    service.users.get_by_username.return_value = user
    monkeypatch.setattr(
        "backend.app.services.auth_service.verify_password",
        lambda _password, _password_hash: False,
    )

    with pytest.raises(AuthenticationError, match="Incorrect username or password"):
        service.login(LoginRequest(username="patient01", password="WrongPassword!"))


def test_profile_update_commits_user_and_patient_changes_together() -> None:
    session = MagicMock()
    service = PatientService(session)
    patient = patient_stub()

    result = service.update_profile(
        patient,
        PatientProfileUpdate(
            full_name="Updated Name",
            phone="0911111111",
            email="updated@example.com",
            address="Updated Address",
        ),
    )

    assert patient.user.full_name == "Updated Name"
    assert patient.user.phone == "0911111111"
    assert patient.user.email == "updated@example.com"
    assert patient.address == "Updated Address"
    assert result.full_name == "Updated Name"
    session.commit.assert_called_once_with()


def test_profile_update_rolls_back_on_database_error() -> None:
    session = MagicMock()
    session.commit.side_effect = SQLAlchemyError("commit failed")
    service = PatientService(session)

    with pytest.raises(Exception, match="Unable to update patient profile"):
        service.update_profile(patient_stub(), PatientProfileUpdate(full_name="Updated Name"))

    session.rollback.assert_called_once_with()


def test_appointment_list_forwards_pagination_search_and_status() -> None:
    service = AppointmentService(MagicMock())
    service.repository = MagicMock()
    service.repository.list_for_patient.return_value = ([appointment_stub()], 11)

    result = service.list_appointments(
        10,
        page=2,
        page_size=10,
        keyword="Internal",
        status="COMPLETED",
    )

    assert result.page == 2
    assert result.total == 11
    assert result.total_pages == 2
    assert result.items[0].doctor.full_name == "Nguyen Van B"
    service.repository.list_for_patient.assert_called_once_with(
        10,
        page=2,
        page_size=10,
        keyword="Internal",
        status="COMPLETED",
    )


def test_upcoming_appointment_uses_explicit_clinic_time() -> None:
    service = AppointmentService(MagicMock())
    service.repository = MagicMock()
    service.repository.get_upcoming.return_value = appointment_stub(status="CONFIRMED")
    now = datetime(2026, 9, 19, 8, 30)

    result = service.get_upcoming(10, now=now)

    assert result is not None
    assert result.status == "CONFIRMED"
    service.repository.get_upcoming.assert_called_once_with(
        10,
        current_date=date(2026, 9, 19),
        current_time=time(8, 30),
    )


def test_appointment_detail_not_owned_is_indistinguishable_from_missing() -> None:
    service = AppointmentService(MagicMock())
    service.repository = MagicMock()
    service.repository.get_owned.return_value = None

    with pytest.raises(NotFoundError, match="Appointment not found"):
        service.get_detail(999, patient_id=10)

    service.repository.get_owned.assert_called_once_with(999, 10)


def test_medical_result_loads_prescription_items() -> None:
    service = MedicalRecordService(MagicMock())
    service.repository = MagicMock()
    appointment = appointment_stub()
    prescription = SimpleNamespace(
        prescription_id=55,
        created_at=datetime(2026, 9, 19, 9, 50),
        items=[
            SimpleNamespace(
                medicine_name="Paracetamol",
                quantity=10,
                dosage="500 mg",
                instructions="Twice daily after meals",
            )
        ],
    )
    record = SimpleNamespace(
        medical_record_id=200,
        appointment_id=100,
        appointment=appointment,
        examination_date=datetime(2026, 9, 19, 9, 45),
        symptoms="Sore throat",
        diagnosis="Acute pharyngitis",
        notes="Rest",
        prescription=prescription,
    )
    service.repository.get_owned.return_value = record

    result = service.get_detail(200, patient_id=10)

    assert result.prescription is not None
    assert result.prescription.items[0].medicine_name == "Paracetamol"
    assert result.appointment_id == 100
    service.repository.get_owned.assert_called_once_with(200, 10)


def test_medical_record_not_owned_returns_not_found() -> None:
    service = MedicalRecordService(MagicMock())
    service.repository = MagicMock()
    service.repository.get_owned.return_value = None

    with pytest.raises(NotFoundError, match="Medical record not found"):
        service.get_detail(999, patient_id=10)


def test_invoice_detail_uses_decimal_for_line_totals_and_loads_payment() -> None:
    service = InvoiceService(MagicMock())
    service.repository = MagicMock()
    invoice = SimpleNamespace(
        invoice_id=300,
        appointment_id=100,
        created_at=datetime(2026, 9, 19, 10, 0),
        total_amount=Decimal("450000.00"),
        status="PAID",
        appointment=appointment_stub(),
        items=[
            SimpleNamespace(
                item_name="Consultation",
                quantity=2,
                unit_price=Decimal("200000.00"),
            )
        ],
        payment=SimpleNamespace(
            payment_id=400,
            amount=Decimal("450000.00"),
            payment_method="CARD",
            payment_date=datetime(2026, 9, 19, 10, 5),
        ),
    )
    service.repository.get_owned.return_value = invoice

    result = service.get_detail(300, patient_id=10)

    assert result.items[0].line_total == Decimal("400000.00")
    assert isinstance(result.items[0].line_total, Decimal)
    assert result.payment is not None
    assert result.payment.payment_method == "CARD"
    service.repository.get_owned.assert_called_once_with(300, 10)


def test_invoice_not_owned_returns_not_found() -> None:
    service = InvoiceService(MagicMock())
    service.repository = MagicMock()
    service.repository.get_owned.return_value = None

    with pytest.raises(NotFoundError, match="Invoice not found"):
        service.get_detail(999, patient_id=10)


def test_dashboard_aggregates_patient_scoped_counts() -> None:
    service = DashboardService(MagicMock())
    service.appointments = MagicMock()
    service.medical_records = MagicMock()
    service.invoices = MagicMock()
    service.appointment_service = MagicMock()
    service.appointments.count_for_patient.return_value = 8
    service.medical_records.count_for_patient.return_value = 5
    service.invoices.count_for_patient.side_effect = [4, 1]
    service.appointment_service.get_upcoming.return_value = None

    result = service.get_dashboard(patient_stub())

    assert result.patient_name == "Nguyen Van A"
    assert result.total_appointments == 8
    assert result.total_medical_records == 5
    assert result.total_invoices == 4
    assert result.unpaid_invoices == 1
    assert result.upcoming_appointment is None
    service.appointments.count_for_patient.assert_called_once_with(10)
    service.medical_records.count_for_patient.assert_called_once_with(10)
    assert service.invoices.count_for_patient.call_args_list[1].kwargs == {"status": "UNPAID"}
