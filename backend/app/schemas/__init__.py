"""Legacy admin request/response schemas with database-sized validation."""

from __future__ import annotations

import re
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


def _nonblank(value: str | None) -> str | None:
    if value is not None and not value.strip():
        raise ValueError("Blank text is not allowed")
    return value


def _phone(value: object | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", "", str(value))
    digits = cleaned[1:] if cleaned.startswith("+") else cleaned
    if not digits.isdigit() or not 7 <= len(digits) <= 14 or len(cleaned) > 15:
        raise ValueError("Phone must contain 7 to 14 digits, optionally prefixed by +")
    return cleaned


def _strong_password(value: str) -> str:
    if any(re.search(pattern, value) is None for pattern in (r"[A-Z]", r"[a-z]", r"\d", r"[^A-Za-z0-9]")):
        raise ValueError("Password must contain uppercase, lowercase, number, and special character")
    return value


class AdminModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("IsActive", check_fields=False)
    @classmethod
    def active_must_be_boolean(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("IsActive cannot be null")
        return value


class UserBase(AdminModel):
    Username: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    FullName: str = Field(min_length=1, max_length=100)
    Phone: str | None = Field(default=None, max_length=15)
    Email: EmailStr | None = Field(default=None, max_length=100)
    Role: str = Field(pattern=r"^(PATIENT|DOCTOR|STAFF|ADMIN)$")

    @field_validator("Phone", mode="before")
    @classmethod
    def valid_phone(cls, value: object | None) -> str | None:
        return _phone(value)

    @field_validator("Username")
    @classmethod
    def normalized_username(cls, value: str) -> str:
        return value.lower()


class UserCreate(UserBase):
    Password: str = Field(min_length=8, max_length=128)

    @field_validator("Password")
    @classmethod
    def password_complexity(cls, value: str) -> str:
        return _strong_password(value)


class UserUpdate(AdminModel):
    Username: str | None = Field(default=None, min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    FullName: str | None = Field(default=None, min_length=1, max_length=100)
    Phone: str | None = Field(default=None, max_length=15)
    Email: EmailStr | None = Field(default=None, max_length=100)
    Role: str | None = Field(default=None, pattern=r"^(PATIENT|DOCTOR|STAFF|ADMIN)$")
    IsActive: bool | None = None

    @field_validator("Username", "FullName", "Role")
    @classmethod
    def required_if_present(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Required field cannot be null")
        return value

    @field_validator("Username")
    @classmethod
    def normalized_username(cls, value: str | None) -> str | None:
        return value.lower() if value is not None else None

    @field_validator("Phone", mode="before")
    @classmethod
    def valid_phone(cls, value: object | None) -> str | None:
        return _phone(value)


class UserOut(UserBase):
    UserID: int
    IsActive: bool
    CreatedAt: datetime
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(AdminModel):
    Username: str = Field(min_length=1, max_length=50)
    Password: str = Field(min_length=1, max_length=128)


class Token(AdminModel):
    access_token: str
    token_type: str = "bearer"


class SpecialtyCreate(AdminModel):
    SpecialtyName: str = Field(min_length=1, max_length=100)
    Description: str | None = Field(default=None, max_length=255)

    @field_validator("Description")
    @classmethod
    def valid_description(cls, value: str | None) -> str | None:
        return _nonblank(value)


class SpecialtyUpdate(AdminModel):
    SpecialtyName: str | None = Field(default=None, min_length=1, max_length=100)
    Description: str | None = Field(default=None, max_length=255)
    IsActive: bool | None = None

    @field_validator("SpecialtyName")
    @classmethod
    def valid_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Text cannot be null")
        return value

    @field_validator("Description")
    @classmethod
    def valid_description(cls, value: str | None) -> str | None:
        return _nonblank(value)


class SpecialtyOut(AdminModel):
    SpecialtyID: int
    SpecialtyName: str
    Description: str | None = None
    IsActive: bool
    model_config = ConfigDict(from_attributes=True)


class ClinicCreate(AdminModel):
    ClinicName: str = Field(min_length=1, max_length=150)
    Address: str | None = Field(default=None, max_length=255)
    Phone: str | None = Field(default=None, max_length=15)

    @field_validator("Address")
    @classmethod
    def valid_address(cls, value: str | None) -> str | None:
        return _nonblank(value)

    @field_validator("Phone", mode="before")
    @classmethod
    def valid_phone(cls, value: object | None) -> str | None:
        return _phone(value)


class ClinicUpdate(AdminModel):
    ClinicName: str | None = Field(default=None, min_length=1, max_length=150)
    Address: str | None = Field(default=None, max_length=255)
    Phone: str | None = Field(default=None, max_length=15)
    IsActive: bool | None = None

    @field_validator("ClinicName")
    @classmethod
    def valid_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Text cannot be null")
        return value

    @field_validator("Address")
    @classmethod
    def valid_address(cls, value: str | None) -> str | None:
        return _nonblank(value)

    @field_validator("Phone", mode="before")
    @classmethod
    def valid_phone(cls, value: object | None) -> str | None:
        return _phone(value)


class ClinicOut(AdminModel):
    ClinicID: int
    ClinicName: str
    Address: str | None = None
    Phone: str | None = None
    IsActive: bool
    model_config = ConfigDict(from_attributes=True)


class DoctorCreate(AdminModel):
    Username: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    Password: str = Field(min_length=8, max_length=128)
    FullName: str = Field(min_length=1, max_length=100)
    Phone: str | None = Field(default=None, max_length=15)
    Email: EmailStr | None = Field(default=None, max_length=100)
    SpecialtyID: int = Field(gt=0)
    ClinicID: int = Field(gt=0)
    LicenseNumber: str | None = Field(default=None, max_length=50)

    @field_validator("Username")
    @classmethod
    def normalized_username(cls, value: str) -> str:
        return value.lower()

    @field_validator("Phone", mode="before")
    @classmethod
    def valid_phone(cls, value: object | None) -> str | None:
        return _phone(value)

    @field_validator("Password")
    @classmethod
    def password_complexity(cls, value: str) -> str:
        return _strong_password(value)

    @field_validator("LicenseNumber")
    @classmethod
    def valid_license(cls, value: str | None) -> str | None:
        return _nonblank(value)


class DoctorUpdate(AdminModel):
    SpecialtyID: int | None = Field(default=None, gt=0)
    ClinicID: int | None = Field(default=None, gt=0)
    LicenseNumber: str | None = Field(default=None, max_length=50)
    IsActive: bool | None = None

    @field_validator("SpecialtyID", "ClinicID")
    @classmethod
    def required_id_if_present(cls, value: int | None) -> int | None:
        if value is None:
            raise ValueError("ID cannot be null")
        return value

    @field_validator("LicenseNumber")
    @classmethod
    def valid_license(cls, value: str | None) -> str | None:
        return _nonblank(value)


class DoctorOut(AdminModel):
    DoctorID: int
    UserID: int
    FullName: str
    SpecialtyID: int
    SpecialtyName: str | None = None
    ClinicID: int | None = None
    ClinicName: str | None = None
    LicenseNumber: str | None = None
    IsActive: bool
    model_config = ConfigDict(from_attributes=True)


def _valid_shift(start: time, end: time, duration: int) -> None:
    if start.tzinfo is not None or end.tzinfo is not None or start >= end:
        raise ValueError("StartTime must be before EndTime")
    minutes = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
    if start.second or start.microsecond or end.second or end.microsecond:
        raise ValueError("Shift boundaries must be whole minutes")
    if duration > minutes or minutes % duration:
        raise ValueError("SlotDuration must divide the shift into complete slots")


class ScheduleCreate(AdminModel):
    DoctorID: int = Field(gt=0)
    DayOfWeek: int = Field(ge=1, le=7)
    StartTime: time
    EndTime: time
    SlotDuration: int = Field(default=30, gt=0, le=480)

    @model_validator(mode="after")
    def valid_shift(self) -> ScheduleCreate:
        _valid_shift(self.StartTime, self.EndTime, self.SlotDuration)
        return self


class ScheduleUpdate(AdminModel):
    DayOfWeek: int | None = Field(default=None, ge=1, le=7)
    StartTime: time | None = None
    EndTime: time | None = None
    SlotDuration: int | None = Field(default=None, gt=0, le=480)
    IsActive: bool | None = None

    @field_validator("DayOfWeek", "StartTime", "EndTime", "SlotDuration")
    @classmethod
    def nonnull_if_present(cls, value: object | None) -> object:
        if value is None:
            raise ValueError("Schedule fields cannot be null")
        return value


class ScheduleOut(AdminModel):
    ScheduleID: int
    DoctorID: int
    DayOfWeek: int
    StartTime: time
    EndTime: time
    SlotDuration: int
    IsActive: bool
    model_config = ConfigDict(from_attributes=True)
