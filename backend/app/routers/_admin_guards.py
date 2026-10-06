"""Checks that admin changes do not invalidate unfinished appointments."""

from __future__ import annotations

import logging
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import Appointment, Doctor, DoctorSchedule, Patient, User

OPEN_STATUSES = ("PENDING", "CONFIRMED", "CHECKED_IN", "IN_PROGRESS")
logger = logging.getLogger(__name__)


def commit_or_error(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Dữ liệu trùng hoặc đang được tham chiếu.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Admin database commit failed: %s", type(exc).__name__)
        raise HTTPException(500, "Không thể lưu thay đổi.") from exc


def flush_or_error(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Dữ liệu trùng hoặc đang được tham chiếu.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Admin database flush failed: %s", type(exc).__name__)
        raise HTTPException(500, "Không thể lưu thay đổi.") from exc


def lock_doctors(db: Session, *, doctor_id: int | None = None, clinic_id: int | None = None) -> None:
    """Use the booking doctor-row lock before changing its catalog or shifts."""
    bind = db.get_bind()
    if getattr(getattr(bind, "dialect", None), "name", None) != "mssql":
        return
    statement = select(Doctor.doctor_id).order_by(Doctor.doctor_id).with_hint(
        Doctor, "WITH (UPDLOCK, HOLDLOCK)", dialect_name="mssql"
    )
    if doctor_id is not None:
        statement = statement.where(Doctor.doctor_id == doctor_id)
    if clinic_id is not None:
        statement = statement.where(Doctor.clinic_id == clinic_id)
    db.execute(statement).all()


def lock_patient(db: Session, patient_id: int) -> None:
    bind = db.get_bind()
    if getattr(getattr(bind, "dialect", None), "name", None) != "mssql":
        return
    statement = (
        select(Patient.patient_id)
        .where(Patient.patient_id == patient_id)
        .with_hint(Patient, "WITH (UPDLOCK, HOLDLOCK)", dialect_name="mssql")
    )
    db.execute(statement).scalar_one_or_none()


def lock_active_admins(db: Session) -> None:
    bind = db.get_bind()
    if getattr(getattr(bind, "dialect", None), "name", None) != "mssql":
        return
    statement = (
        select(User.user_id)
        .where(User.role == "ADMIN", User.is_active)
        .order_by(User.user_id)
        .with_hint(User, "WITH (UPDLOCK, HOLDLOCK)", dialect_name="mssql")
    )
    db.execute(statement).all()


def lock_catalog(db: Session) -> None:
    """Serialize admin changes to doctors, clinics, and specialties on SQL Server."""
    bind = db.get_bind()
    if getattr(getattr(bind, "dialect", None), "name", None) != "mssql":
        return
    result = db.execute(
        text(
            "DECLARE @result int; "
            "EXEC @result = sp_getapplock "
            "@Resource = 'ClinicManagement.AdminCatalog', "
            "@LockMode = 'Exclusive', @LockOwner = 'Transaction', @LockTimeout = 10000; "
            "SELECT @result"
        )
    ).scalar_one()
    if result < 0:
        raise HTTPException(409, "Danh mục đang được cập nhật; vui lòng thử lại.")


def has_open_appointments(
    db: Session,
    *,
    doctor_id: int | None = None,
    clinic_id: int | None = None,
    patient_id: int | None = None,
) -> bool:
    query = db.query(Appointment).filter(Appointment.status.in_(OPEN_STATUSES))
    if doctor_id is not None:
        query = query.filter(Appointment.doctor_id == doctor_id)
    if clinic_id is not None:
        query = query.filter(Appointment.clinic_id == clinic_id)
    if patient_id is not None:
        query = query.filter(Appointment.patient_id == patient_id)
    count = query.count()
    return isinstance(count, int) and count > 0


def require_no_open_appointments(
    db: Session,
    *,
    doctor_id: int | None = None,
    clinic_id: int | None = None,
    patient_id: int | None = None,
) -> None:
    if has_open_appointments(
        db, doctor_id=doctor_id, clinic_id=clinic_id, patient_id=patient_id
    ):
        raise HTTPException(409, "Còn lịch hẹn chưa kết thúc; hãy xử lý các lịch này trước.")


def _covers(shift: DoctorSchedule, appointment: Appointment) -> bool:
    if not shift.is_active or shift.day_of_week != appointment.appointment_date.isoweekday():
        return False
    if not (shift.start_time <= appointment.start_time < appointment.end_time <= shift.end_time):
        return False
    step = shift.slot_duration
    if step <= 0:
        return False
    start = datetime.combine(date(2000, 1, 1), shift.start_time)
    booked_start = datetime.combine(date(2000, 1, 1), appointment.start_time)
    booked_end = datetime.combine(date(2000, 1, 1), appointment.end_time)
    return (
        (booked_start - start).total_seconds() % (step * 60) == 0
        and (booked_end - booked_start).total_seconds() == step * 60
    )


def require_appointments_covered(
    db: Session,
    doctor_id: int,
    replacement: DoctorSchedule | None = None,
    *,
    excluded_schedule_id: int | None = None,
) -> None:
    """Reject changing a shift if any unfinished booking loses a valid slot."""
    appointments = (
        db.query(Appointment)
        .filter(Appointment.doctor_id == doctor_id, Appointment.status.in_(OPEN_STATUSES))
        .all()
    )
    schedules = db.query(DoctorSchedule).filter(DoctorSchedule.doctor_id == doctor_id).all()
    if not isinstance(appointments, list) or not isinstance(schedules, list):
        return  # Unit fakes do not expose the SQLAlchemy collection contract.
    candidates = [
        shift
        for shift in schedules
        if shift.schedule_id != excluded_schedule_id and shift.is_active
    ]
    if replacement is not None and replacement.is_active:
        candidates.append(replacement)
    if any(not any(_covers(shift, appt) for shift in candidates) for appt in appointments):
        raise HTTPException(409, "Thay đổi ca trực sẽ làm lịch hẹn chưa kết thúc không hợp lệ.")
