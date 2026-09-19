"""Ownership-scoped appointment queries."""

from datetime import date, time

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from backend.app.models import Appointment, Clinic, Doctor, Specialty, User


def _appointment_load_options():
    return (
        joinedload(Appointment.doctor).joinedload(Doctor.user),
        joinedload(Appointment.doctor).joinedload(Doctor.specialty),
        joinedload(Appointment.clinic),
    )


class AppointmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _apply_search(statement, keyword: str | None):
        if not keyword or not keyword.strip():
            return statement
        pattern = f"%{keyword.strip()}%"
        return statement.where(
            or_(
                User.full_name.ilike(pattern),
                Specialty.specialty_name.ilike(pattern),
                Clinic.clinic_name.ilike(pattern),
                Appointment.reason.ilike(pattern),
            )
        )

    def list_for_patient(
        self,
        patient_id: int,
        *,
        page: int,
        page_size: int,
        keyword: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Appointment], int]:
        base = (
            select(Appointment)
            .join(Appointment.doctor)
            .join(Doctor.user)
            .join(Doctor.specialty)
            .outerjoin(Appointment.clinic)
            .where(Appointment.patient_id == patient_id)
        )
        count_statement = (
            select(func.count(Appointment.appointment_id))
            .select_from(Appointment)
            .join(Appointment.doctor)
            .join(Doctor.user)
            .join(Doctor.specialty)
            .outerjoin(Appointment.clinic)
            .where(Appointment.patient_id == patient_id)
        )
        if status:
            base = base.where(Appointment.status == status)
            count_statement = count_statement.where(Appointment.status == status)
        base = self._apply_search(base, keyword)
        count_statement = self._apply_search(count_statement, keyword)

        total = int(self.session.scalar(count_statement) or 0)
        statement = (
            base.options(*_appointment_load_options())
            .order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        appointments = list(self.session.execute(statement).unique().scalars().all())
        return appointments, total

    def get_upcoming(
        self, patient_id: int, *, current_date: date, current_time: time
    ) -> Appointment | None:
        statement = (
            select(Appointment)
            .options(*_appointment_load_options())
            .where(
                Appointment.patient_id == patient_id,
                Appointment.status.in_(("PENDING", "CONFIRMED")),
                or_(
                    Appointment.appointment_date > current_date,
                    (
                        (Appointment.appointment_date == current_date)
                        & (Appointment.start_time >= current_time)
                    ),
                ),
            )
            .order_by(Appointment.appointment_date.asc(), Appointment.start_time.asc())
            .limit(1)
        )
        return self.session.execute(statement).unique().scalar_one_or_none()

    def get_owned(self, appointment_id: int, patient_id: int) -> Appointment | None:
        statement = (
            select(Appointment)
            .options(
                *_appointment_load_options(),
                joinedload(Appointment.medical_record),
                joinedload(Appointment.invoice),
            )
            .where(
                Appointment.appointment_id == appointment_id,
                Appointment.patient_id == patient_id,
            )
        )
        return self.session.execute(statement).unique().scalar_one_or_none()

    def count_for_patient(self, patient_id: int) -> int:
        statement = select(func.count(Appointment.appointment_id)).where(
            Appointment.patient_id == patient_id
        )
        return int(self.session.scalar(statement) or 0)
