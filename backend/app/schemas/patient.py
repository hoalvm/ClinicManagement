"""Patient profile schemas."""

from datetime import date

from pydantic import EmailStr, Field, field_validator

from backend.app.core.clock import clinic_today
from backend.app.schemas.auth import _clean_required
from backend.app.schemas.common import APIModel


class PatientProfileResponse(APIModel):
    patient_id: int
    username: str
    full_name: str
    phone: str | None = None
    email: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    address: str | None = None


class PatientProfileUpdate(APIModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=15)
    email: EmailStr | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=10)
    address: str | None = Field(default=None, max_length=255)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Full name cannot be null")
        return _clean_required(value, "Full name")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip()
        normalized = cleaned[1:] if cleaned.startswith("+") else cleaned
        if not normalized.isdigit() or not 7 <= len(normalized) <= 14:
            raise ValueError("Phone must contain 7 to 14 digits, optionally prefixed by +")
        return cleaned

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date | None) -> date | None:
        if value is not None and value > clinic_today():
            raise ValueError("Date of birth cannot be in the future")
        return value

    @field_validator("gender", "address")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
