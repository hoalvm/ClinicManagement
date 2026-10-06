"""Mapping for the existing ``Appointments`` table."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, Time, text
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.clinic import Clinic
    from backend.app.models.doctor import Doctor
    from backend.app.models.invoice import Invoice
    from backend.app.models.medical_record import MedicalRecord
    from backend.app.models.patient import Patient


class Appointment(Base):
    __tablename__ = "Appointments"

    appointment_id: Mapped[int] = mapped_column("AppointmentID", Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        "PatientID", ForeignKey("Patients.PatientID"), nullable=False
    )
    doctor_id: Mapped[int] = mapped_column(
        "DoctorID", ForeignKey("Doctors.DoctorID"), nullable=False
    )
    clinic_id: Mapped[int | None] = mapped_column(
        "ClinicID", ForeignKey("Clinics.ClinicID"), nullable=True
    )
    specialty_id: Mapped[int | None] = mapped_column(
        "SpecialtyID", ForeignKey("Specialties.SpecialtyID"), nullable=True
    )
    appointment_date: Mapped[date] = mapped_column("AppointmentDate", Date, nullable=False)
    start_time: Mapped[time] = mapped_column("StartTime", Time, nullable=False)
    end_time: Mapped[time] = mapped_column("EndTime", Time, nullable=False)
    reason: Mapped[str | None] = mapped_column("Reason", NVARCHAR(500), nullable=True)
    queue_number: Mapped[str | None] = mapped_column("QueueNumber", NVARCHAR(10), nullable=True)
    check_in_at: Mapped[datetime | None] = mapped_column("CheckInAt", DATETIME2, nullable=True)
    clinical_context_loaded_at: Mapped[datetime | None] = mapped_column(
        "ClinicalContextLoadedAt", DATETIME2, nullable=True
    )
    clinical_context_loaded_by_user_id: Mapped[int | None] = mapped_column(
        "ClinicalContextLoadedByUserID", ForeignKey("Users.UserID"), nullable=True
    )
    check_in_note: Mapped[str | None] = mapped_column("CheckInNote", NVARCHAR(500), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(
        "CancellationReason", NVARCHAR(500), nullable=True
    )
    last_reschedule_reason: Mapped[str | None] = mapped_column(
        "LastRescheduleReason", NVARCHAR(500), nullable=True
    )
    no_show_at: Mapped[datetime | None] = mapped_column("NoShowAt", DATETIME2, nullable=True)
    no_show_by_user_id: Mapped[int | None] = mapped_column(
        "NoShowByUserID", ForeignKey("Users.UserID"), nullable=True
    )
    no_show_reason_code: Mapped[str | None] = mapped_column(
        "NoShowReasonCode", NVARCHAR(30), nullable=True
    )
    status: Mapped[str] = mapped_column(
        "Status", NVARCHAR(20), nullable=False, server_default=text("'PENDING'")
    )
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DATETIME2, nullable=False, server_default=text("GETDATE()")
    )

    patient: Mapped[Patient] = relationship("Patient", back_populates="appointments")
    doctor: Mapped[Doctor] = relationship("Doctor", back_populates="appointments")
    clinic: Mapped[Clinic | None] = relationship("Clinic", back_populates="appointments")
    medical_record: Mapped[MedicalRecord | None] = relationship(
        "MedicalRecord", back_populates="appointment", uselist=False
    )
    invoice: Mapped[Invoice | None] = relationship(
        "Invoice", back_populates="appointment", uselist=False
    )
