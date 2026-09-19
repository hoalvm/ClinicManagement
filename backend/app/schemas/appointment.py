"""Appointment response schemas."""

from datetime import date, time

from backend.app.schemas.common import APIModel, Page


class DoctorSummary(APIModel):
    doctor_id: int
    full_name: str
    specialty: str


class ClinicSummary(APIModel):
    clinic_id: int
    clinic_name: str


class AppointmentSummary(APIModel):
    appointment_id: int
    appointment_date: date
    start_time: time
    end_time: time
    reason: str | None = None
    status: str
    doctor: DoctorSummary
    clinic: ClinicSummary | None = None


class AppointmentPage(Page[AppointmentSummary]):
    """Paginated appointment history response."""


class DoctorDetail(DoctorSummary):
    phone: str | None = None
    email: str | None = None
    license_number: str | None = None


class ClinicDetail(ClinicSummary):
    address: str | None = None
    phone: str | None = None


class AppointmentDetail(APIModel):
    appointment_id: int
    appointment_date: date
    start_time: time
    end_time: time
    reason: str | None = None
    status: str
    doctor: DoctorDetail
    clinic: ClinicDetail | None = None
    medical_record_id: int | None = None
    invoice_id: int | None = None
