"""Authentication request and response schemas."""

from datetime import date

import re

from pydantic import EmailStr, Field, field_validator, model_validator

from backend.app.core.clock import clinic_today
from backend.app.schemas.common import APIModel


def _clean_required(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")
    return cleaned


class RegisterRequest(APIModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=7, max_length=14)
    email: EmailStr | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=10)
    address: str | None = Field(default=None, max_length=255)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        cleaned = _clean_required(value, "Username")
        if not re.fullmatch(r"[A-Za-z0-9]+", cleaned):
            raise ValueError("Username may contain only letters and numbers")
        return cleaned.lower()

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return _clean_required(value, "Full name")

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, value: str) -> str:
        requirements = (
            r"[A-Z]",
            r"[a-z]",
            r"\d",
            r"[^A-Za-z0-9]",
        )
        if any(re.search(pattern, value) is None for pattern in requirements):
            raise ValueError(
                "Password must contain an uppercase letter, a lowercase letter, "
                "a number, and a special character"
            )
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.isdigit() or not 7 <= len(cleaned) <= 14:
            raise ValueError("Phone must contain 7 to 14 digits")
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

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(APIModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        return _clean_required(value, "Username").lower()


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(APIModel):
    user_id: int
    patient_id: int
    username: str
    full_name: str
    role: str


class CurrentUserResponse(APIModel):
    user_id: int
    patient_id: int | None = None
    username: str
    full_name: str
    phone: str | None = None
    email: str | None = None
    role: str
    is_active: bool
