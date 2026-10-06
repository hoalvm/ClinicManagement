"""Approved doctor leave and one-off schedule closures."""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Time, text
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class DoctorScheduleException(Base):
    __tablename__ = "DoctorScheduleExceptions"

    exception_id: Mapped[int] = mapped_column("ExceptionID", Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(
        "DoctorID", Integer, ForeignKey("Doctors.DoctorID"), nullable=False
    )
    exception_date: Mapped[date] = mapped_column("ExceptionDate", Date, nullable=False)
    start_time: Mapped[time | None] = mapped_column("StartTime", Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column("EndTime", Time, nullable=True)
    reason: Mapped[str] = mapped_column("Reason", NVARCHAR(255), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        "CreatedByUserID", Integer, ForeignKey("Users.UserID"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DATETIME2, nullable=False, server_default=text("SYSUTCDATETIME()")
    )
