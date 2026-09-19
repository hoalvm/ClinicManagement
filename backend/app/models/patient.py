"""Mapping for the existing ``Patients`` table."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.appointment import Appointment
    from backend.app.models.user import User


class Patient(Base):
    __tablename__ = "Patients"

    patient_id: Mapped[int] = mapped_column("PatientID", Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        "UserID", ForeignKey("Users.UserID"), unique=True, nullable=False
    )
    date_of_birth: Mapped[date | None] = mapped_column("DateOfBirth", Date, nullable=True)
    gender: Mapped[str | None] = mapped_column("Gender", NVARCHAR(10), nullable=True)
    address: Mapped[str | None] = mapped_column("Address", NVARCHAR(255), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="patient")
    appointments: Mapped[list[Appointment]] = relationship("Appointment", back_populates="patient")
