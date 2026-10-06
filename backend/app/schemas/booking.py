"""Pydantic schemas for patient booking, doctor catalog, and appointment actions."""

from __future__ import annotations

from datetime import date, time

from pydantic import Field, field_validator

from backend.app.schemas.common import APIModel


class SpecialtyItem(APIModel):
    specialty_id: int
    specialty_name: str
    description: str | None = None
    doctor_count: int = 0


class DoctorPublicItem(APIModel):
    doctor_id: int
    full_name: str
    specialty_id: int
    specialty_name: str
    clinic_id: int | None = None
    clinic_name: str | None = None
    clinic_address: str | None = None
    license_number: str | None = None
    phone: str | None = None
    email: str | None = None


class TimeSlot(APIModel):
    start_time: time
    end_time: time
    is_available: bool
    reason: str | None = None


class AvailableSlotsResponse(APIModel):
    doctor_id: int
    doctor_name: str
    specialty_name: str
    clinic_name: str | None = None
    appointment_date: date
    day_of_week: int
    has_schedule: bool
    slots: list[TimeSlot] = []


class DoctorScheduleItem(APIModel):
    schedule_id: int
    doctor_id: int
    day_of_week: int
    start_time: time
    end_time: time
    slot_duration: int


class AppointmentCreateRequest(APIModel):
    doctor_id: int = Field(gt=0)
    appointment_date: date
    start_time: time
    end_time: time
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Reason cannot be blank")
        return value


class AppointmentRescheduleRequest(APIModel):
    new_appointment_date: date
    new_start_time: time
    new_end_time: time
    new_doctor_id: int | None = Field(default=None, gt=0)
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Reason cannot be blank")
        return value


class AppointmentCancelRequest(APIModel):
    cancellation_reason: str | None = Field(default=None, max_length=500)

    @field_validator("cancellation_reason")
    @classmethod
    def nonblank_reason(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Cancellation reason cannot be blank")
        return value
