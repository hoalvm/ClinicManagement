"""Boundary validation tests for patient authentication and profile requests."""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from backend.app.core.clock import clinic_today
from backend.app.routers.doctor_portal import DoctorLoginRequest
from backend.app.schemas import DoctorCreate, UserCreate, UserUpdate
from backend.app.schemas.auth import RegisterRequest
from backend.app.schemas.patient import PatientProfileUpdate
from backend.app.schemas.reception import (
    BookForPatientRequest,
    CheckInRequest,
    CreateInvoiceRequest,
    InvoiceItemCreate,
    ProcessPaymentRequest,
    RescheduleAppointmentRequest,
)


def valid_registration(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "username": "patient03",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "full_name": "Nguyen Van C",
        "phone": "0900000003",
        "email": "patient03@example.com",
        "date_of_birth": "2000-01-01",
        "gender": "MALE",
        "address": "Ho Chi Minh City",
    }
    payload.update(overrides)
    return payload


def test_registration_normalizes_required_text() -> None:
    request = RegisterRequest.model_validate(
        valid_registration(username="  Patient03  ", full_name="  Nguyen Van C ")
    )

    assert request.username == "patient03"
    assert request.full_name == "Nguyen Van C"
    assert request.model_dump()["confirm_password"] == "Password123!"


def test_staff_and_doctor_usernames_are_stored_in_login_form() -> None:
    staff = UserCreate(
        Username="Staff_A",
        FullName="Nhân viên A",
        Role="STAFF",
        Password="Password123!",
    )
    doctor = DoctorCreate(
        Username="Doctor_A",
        FullName="Bác sĩ A",
        Password="Password123!",
        SpecialtyID=1,
        ClinicID=1,
        LicenseNumber="LIC-001",
    )
    renamed = UserUpdate(Username="Doctor_New")
    login = DoctorLoginRequest(username="DOCTOR_A", password="Password123!")
    assert (staff.Username, doctor.Username, renamed.Username, login.username) == (
        "staff_a", "doctor_a", "doctor_new", "doctor_a"
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"confirm_password": "Different123!"},
        {"password": "short", "confirm_password": "short"},
        {"password": "password123!", "confirm_password": "password123!"},
        {"password": "PASSWORD123!", "confirm_password": "PASSWORD123!"},
        {"password": "Passwordabc!", "confirm_password": "Passwordabc!"},
        {"password": "Password123", "confirm_password": "Password123"},
        {"username": "   "},
        {"username": "patient 03"},
        {"username": "bệnhnhân03"},
        {"full_name": "   "},
        {"email": "not-an-email"},
        {"phone": None},
        {"phone": "12-ab"},
        {"date_of_birth": clinic_today() + timedelta(days=1)},
        {"gender": "INVALID"},
        {"unexpected": "ignored before"},
    ],
)
def test_invalid_registration_is_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        RegisterRequest.model_validate(valid_registration(**overrides))


def test_profile_update_only_exposes_allowed_fields() -> None:
    allowed = set(PatientProfileUpdate.model_fields)

    assert allowed == {
        "full_name",
        "phone",
        "email",
        "date_of_birth",
        "gender",
        "address",
    }
    assert allowed.isdisjoint(
        {"user_id", "patient_id", "username", "password_hash", "role", "is_active"}
    )


def test_profile_update_rejects_future_date_of_birth() -> None:
    with pytest.raises(ValidationError):
        PatientProfileUpdate(date_of_birth=clinic_today() + timedelta(days=1))


@pytest.mark.parametrize("value", ["INVALID", "", "male"])
def test_profile_update_rejects_invalid_gender(value: str) -> None:
    with pytest.raises(ValidationError):
        PatientProfileUpdate(gender=value)


def test_reception_write_models_reject_extra_blank_and_bad_money() -> None:
    with pytest.raises(ValidationError):
        CheckInRequest(notes="   ")
    with pytest.raises(ValidationError):
        CheckInRequest(queue_number="A-999")
    with pytest.raises(ValidationError):
        RescheduleAppointmentRequest(
            appointment_date=clinic_today(),
            start_time="10:00:00",
            end_time="10:30:00",
            reason="   ",
        )
    with pytest.raises(ValidationError):
        BookForPatientRequest(
            doctor_id=1,
            appointment_date=clinic_today(),
            start_time="10:00:00",
            end_time="10:30:00",
            full_name="   ",
            phone="0900000000",
        )
    with pytest.raises(ValidationError):
        InvoiceItemCreate(item_name="Khám", quantity=0, unit_price="100.00")
    with pytest.raises(ValidationError):
        InvoiceItemCreate(item_name="Khám", quantity=1, unit_price="-100.00")
    with pytest.raises(ValidationError):
        ProcessPaymentRequest(payment_method="CARD", amount="100.00")
    with pytest.raises(ValidationError):
        CreateInvoiceRequest(appointment_id=1, items=[])
