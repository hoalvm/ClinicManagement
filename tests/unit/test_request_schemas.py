"""Boundary validation tests for patient authentication and profile requests."""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from backend.app.core.clock import clinic_today
from backend.app.schemas.auth import RegisterRequest
from backend.app.schemas.patient import PatientProfileUpdate


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
        valid_registration(username="  patient03  ", full_name="  Nguyen Van C  ")
    )

    assert request.username == "patient03"
    assert request.full_name == "Nguyen Van C"
    assert request.model_dump()["confirm_password"] == "Password123!"


@pytest.mark.parametrize(
    "overrides",
    [
        {"confirm_password": "Different123!"},
        {"password": "short", "confirm_password": "short"},
        {"username": "   "},
        {"full_name": "   "},
        {"email": "not-an-email"},
        {"phone": "12-ab"},
        {"date_of_birth": clinic_today() + timedelta(days=1)},
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
