"""Clinic access granted to reception staff."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class StaffClinicAssignment(Base):
    __tablename__ = "StaffClinicAssignments"

    user_id: Mapped[int] = mapped_column(
        "UserID", Integer, ForeignKey("Users.UserID"), primary_key=True
    )
    clinic_id: Mapped[int] = mapped_column(
        "ClinicID", Integer, ForeignKey("Clinics.ClinicID"), primary_key=True
    )
    is_active: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, server_default=text("1")
    )
