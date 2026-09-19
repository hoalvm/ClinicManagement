"""Mapping for the existing ``MedicalRecords`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, text
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.appointment import Appointment
    from backend.app.models.prescription import Prescription


class MedicalRecord(Base):
    __tablename__ = "MedicalRecords"

    medical_record_id: Mapped[int] = mapped_column("MedicalRecordID", Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        "AppointmentID",
        ForeignKey("Appointments.AppointmentID"),
        unique=True,
        nullable=False,
    )
    symptoms: Mapped[str | None] = mapped_column("Symptoms", NVARCHAR(1000), nullable=True)
    diagnosis: Mapped[str | None] = mapped_column("Diagnosis", NVARCHAR(1000), nullable=True)
    notes: Mapped[str | None] = mapped_column("Notes", NVARCHAR(2000), nullable=True)
    examination_date: Mapped[datetime] = mapped_column(
        "ExaminationDate", DATETIME2, nullable=False, server_default=text("GETDATE()")
    )

    appointment: Mapped[Appointment] = relationship("Appointment", back_populates="medical_record")
    prescription: Mapped[Prescription | None] = relationship(
        "Prescription", back_populates="medical_record", uselist=False
    )
