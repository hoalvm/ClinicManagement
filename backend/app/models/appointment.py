"""Mapping for the existing ``Appointments`` table."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, String, Time, text
from sqlalchemy.dialects.mssql import DATETIME2
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
    appointment_date: Mapped[date] = mapped_column("AppointmentDate", Date, nullable=False)
    start_time: Mapped[time] = mapped_column("StartTime", Time, nullable=False)
    end_time: Mapped[time] = mapped_column("EndTime", Time, nullable=False)
    reason: Mapped[str | None] = mapped_column("Reason", String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        "Status", String(20), nullable=False, server_default=text("'PENDING'")
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
