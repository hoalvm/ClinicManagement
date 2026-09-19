"""Appointment history, upcoming, and detail business logic."""

from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.models import Appointment
from backend.app.repositories import AppointmentRepository
from backend.app.schemas.appointment import (
    AppointmentDetail,
    AppointmentPage,
    AppointmentSummary,
    ClinicDetail,
    ClinicSummary,
    DoctorDetail,
    DoctorSummary,
)


class AppointmentService:
    def __init__(self, session: Session) -> None:
        self.repository = AppointmentRepository(session)

    @staticmethod
    def to_summary(appointment: Appointment) -> AppointmentSummary:
        doctor = appointment.doctor
        clinic = appointment.clinic
        return AppointmentSummary(
            appointment_id=appointment.appointment_id,
            appointment_date=appointment.appointment_date,
            start_time=appointment.start_time,
            end_time=appointment.end_time,
            reason=appointment.reason,
            status=appointment.status,
            doctor=DoctorSummary(
                doctor_id=doctor.doctor_id,
                full_name=doctor.user.full_name,
                specialty=doctor.specialty.specialty_name,
            ),
            clinic=(
                ClinicSummary(clinic_id=clinic.clinic_id, clinic_name=clinic.clinic_name)
                if clinic is not None
                else None
            ),
        )

    def list_appointments(
        self,
        patient_id: int,
        *,
        page: int,
        page_size: int,
        keyword: str | None,
        status: str | None,
    ) -> AppointmentPage:
        appointments, total = self.repository.list_for_patient(
            patient_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
        )
        return AppointmentPage(
            items=[self.to_summary(item) for item in appointments],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
        )

    def get_upcoming(
        self, patient_id: int, *, now: datetime | None = None
    ) -> AppointmentSummary | None:
        clinic_now = now or datetime.now().astimezone()
        appointment = self.repository.get_upcoming(
            patient_id,
            current_date=clinic_now.date(),
            current_time=clinic_now.time().replace(tzinfo=None),
        )
        return self.to_summary(appointment) if appointment is not None else None

    def get_detail(self, appointment_id: int, patient_id: int) -> AppointmentDetail:
        appointment = self.repository.get_owned(appointment_id, patient_id)
        if appointment is None:
            raise NotFoundError("Appointment not found.")
        doctor = appointment.doctor
        clinic = appointment.clinic
        return AppointmentDetail(
            appointment_id=appointment.appointment_id,
            appointment_date=appointment.appointment_date,
            start_time=appointment.start_time,
            end_time=appointment.end_time,
            reason=appointment.reason,
            status=appointment.status,
            doctor=DoctorDetail(
                doctor_id=doctor.doctor_id,
                full_name=doctor.user.full_name,
                specialty=doctor.specialty.specialty_name,
                phone=doctor.user.phone,
                email=doctor.user.email,
                license_number=doctor.license_number,
            ),
            clinic=(
                ClinicDetail(
                    clinic_id=clinic.clinic_id,
                    clinic_name=clinic.clinic_name,
                    address=clinic.address,
                    phone=clinic.phone,
                )
                if clinic is not None
                else None
            ),
            medical_record_id=(
                appointment.medical_record.medical_record_id
                if appointment.medical_record is not None
                else None
            ),
            invoice_id=(
                appointment.invoice.invoice_id if appointment.invoice is not None else None
            ),
        )
