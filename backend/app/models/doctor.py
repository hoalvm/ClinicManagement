"""Mapping for the existing ``Doctors`` table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.appointment import Appointment
    from backend.app.models.clinic import Clinic
    from backend.app.models.doctor_schedule import DoctorSchedule
    from backend.app.models.specialty import Specialty
    from backend.app.models.user import User


class Doctor(Base):
    __tablename__ = "Doctors"

    doctor_id: Mapped[int] = mapped_column("DoctorID", Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        "UserID", ForeignKey("Users.UserID"), unique=True, nullable=False
    )
    specialty_id: Mapped[int] = mapped_column(
        "SpecialtyID", ForeignKey("Specialties.SpecialtyID"), nullable=False
    )
    clinic_id: Mapped[int | None] = mapped_column(
        "ClinicID", ForeignKey("Clinics.ClinicID"), nullable=True
    )
    license_number: Mapped[str | None] = mapped_column(
        "LicenseNumber", String(50), unique=True, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, server_default=text("1")
    )

    user: Mapped[User] = relationship("User", back_populates="doctor")
    specialty: Mapped[Specialty] = relationship("Specialty", back_populates="doctors")
    clinic: Mapped[Clinic | None] = relationship("Clinic", back_populates="doctors")
    schedules: Mapped[list[DoctorSchedule]] = relationship(
        "DoctorSchedule", back_populates="doctor"
    )
    appointments: Mapped[list[Appointment]] = relationship("Appointment", back_populates="doctor")
