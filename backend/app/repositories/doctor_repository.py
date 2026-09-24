"""Persistence operations for specialties, doctors, and doctor schedules."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from backend.app.models import Doctor, DoctorSchedule, Specialty


class DoctorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_specialties(self) -> list[tuple[Specialty, int]]:
        statement = (
            select(Specialty, func.count(Doctor.doctor_id))
            .outerjoin(Doctor, (Doctor.specialty_id == Specialty.specialty_id) & Doctor.is_active)
            .where(Specialty.is_active)
            .group_by(
                Specialty.specialty_id,
                Specialty.specialty_name,
                Specialty.description,
                Specialty.is_active,
            )
            .order_by(Specialty.specialty_name)
        )
        return list(self.session.execute(statement).all())

    def list_doctors(
        self,
        specialty_id: int | None = None,
        day_of_week: int | None = None,
    ) -> list[Doctor]:
        statement = (
            select(Doctor)
            .options(
                joinedload(Doctor.user),
                joinedload(Doctor.specialty),
                joinedload(Doctor.clinic),
            )
            .where(Doctor.is_active)
        )
        if specialty_id is not None:
            statement = statement.where(Doctor.specialty_id == specialty_id)
        if day_of_week is not None:
            statement = statement.join(Doctor.schedules).where(
                DoctorSchedule.day_of_week == day_of_week,
                DoctorSchedule.is_active,
            )
        statement = statement.order_by(Doctor.doctor_id)
        return list(self.session.execute(statement).unique().scalars().all())

    def get_doctor_by_id(self, doctor_id: int) -> Doctor | None:
        statement = (
            select(Doctor)
            .options(
                joinedload(Doctor.user),
                joinedload(Doctor.specialty),
                joinedload(Doctor.clinic),
            )
            .where(Doctor.doctor_id == doctor_id, Doctor.is_active)
        )
        return self.session.execute(statement).unique().scalar_one_or_none()

    def get_schedules(self, doctor_id: int, day_of_week: int | None = None) -> list[DoctorSchedule]:
        statement = (
            select(DoctorSchedule)
            .where(
                DoctorSchedule.doctor_id == doctor_id,
                DoctorSchedule.is_active,
            )
            .order_by(DoctorSchedule.day_of_week, DoctorSchedule.start_time)
        )
        if day_of_week is not None:
            statement = statement.where(DoctorSchedule.day_of_week == day_of_week)
        return list(self.session.execute(statement).scalars().all())
