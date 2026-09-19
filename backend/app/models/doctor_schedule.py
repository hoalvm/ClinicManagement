"""Mapping for the existing ``DoctorSchedules`` table."""

from __future__ import annotations

from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, Time, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.doctor import Doctor


class DoctorSchedule(Base):
    __tablename__ = "DoctorSchedules"

    schedule_id: Mapped[int] = mapped_column("ScheduleID", Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(
        "DoctorID", ForeignKey("Doctors.DoctorID"), nullable=False
    )
    day_of_week: Mapped[int] = mapped_column("DayOfWeek", SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column("StartTime", Time, nullable=False)
    end_time: Mapped[time] = mapped_column("EndTime", Time, nullable=False)
    slot_duration: Mapped[int] = mapped_column(
        "SlotDuration", Integer, nullable=False, server_default=text("30")
    )
    is_active: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, server_default=text("1")
    )

    doctor: Mapped[Doctor] = relationship("Doctor", back_populates="schedules")
