"""Mapping for the existing ``Clinics`` table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, text
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.appointment import Appointment
    from backend.app.models.doctor import Doctor


class Clinic(Base):
    __tablename__ = "Clinics"

    clinic_id: Mapped[int] = mapped_column("ClinicID", Integer, primary_key=True)
    clinic_name: Mapped[str] = mapped_column("ClinicName", NVARCHAR(150), nullable=False)
    address: Mapped[str | None] = mapped_column("Address", NVARCHAR(255), nullable=True)
    phone: Mapped[str | None] = mapped_column("Phone", NVARCHAR(15), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, server_default=text("1")
    )

    doctors: Mapped[list[Doctor]] = relationship("Doctor", back_populates="clinic")
    appointments: Mapped[list[Appointment]] = relationship("Appointment", back_populates="clinic")
