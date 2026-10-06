from datetime import date, time
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator
from sqlalchemy.orm import Session

from backend.app.core.audit import record_audit_event
from backend.app.core.clock import clinic_today
from backend.app.core.config import get_settings
from backend.app.models import Appointment, Doctor, DoctorSchedule
from backend.app.models.doctor_schedule_exception import DoctorScheduleException

from .. import schemas
from ..database import get_db
from ..deps import require_admin
from ._admin_guards import (
    commit_or_error,
    flush_or_error,
    lock_doctors,
    require_appointments_covered,
)

router = APIRouter(prefix="/schedules", tags=["DoctorSchedules"])


class ScheduleExceptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    doctor_id: PositiveInt
    exception_date: date
    start_time: time | None = None
    end_time: time | None = None
    reason: str = Field(min_length=3, max_length=255)

    @model_validator(mode="after")
    def valid_interval(self) -> "ScheduleExceptionCreate":
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError("Both start_time and end_time are required for a partial closure")
        if self.start_time is not None and (
            self.start_time.tzinfo is not None
            or self.end_time.tzinfo is not None
            or self.start_time >= self.end_time
        ):
            raise ValueError("The closure interval must have increasing local times")
        return self


def _exception_dict(item: DoctorScheduleException) -> dict:
    return {
        "exception_id": item.exception_id,
        "doctor_id": item.doctor_id,
        "exception_date": item.exception_date,
        "start_time": item.start_time,
        "end_time": item.end_time,
        "reason": item.reason,
        "is_active": item.is_active,
    }


@router.get("/exceptions")
def list_schedule_exceptions(
    doctor_id: int | None = None,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    query = db.query(DoctorScheduleException)
    if doctor_id is not None:
        query = query.filter(DoctorScheduleException.doctor_id == doctor_id)
    return [
        _exception_dict(item)
        for item in query.order_by(
            DoctorScheduleException.exception_date.desc(),
            DoctorScheduleException.exception_id.desc(),
        ).all()
    ]


@router.post("/exceptions", status_code=201)
def create_schedule_exception(
    body: ScheduleExceptionCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    if get_settings().app_mode != "production":
        raise HTTPException(403, "Ngoại lệ ca trực chỉ áp dụng trong chế độ production.")
    if body.exception_date < clinic_today():
        raise HTTPException(422, "Không thể đóng ca trực trong quá khứ.")
    lock_doctors(db, doctor_id=body.doctor_id)
    doctor = db.query(Doctor).filter(Doctor.doctor_id == body.doctor_id).first()
    if doctor is None or not doctor.is_active or not doctor.user.is_active:
        raise HTTPException(404, "Không tìm thấy bác sĩ đang hoạt động.")

    existing = (
        db.query(DoctorScheduleException)
        .filter(
            DoctorScheduleException.doctor_id == body.doctor_id,
            DoctorScheduleException.exception_date == body.exception_date,
            DoctorScheduleException.is_active.is_(True),
        )
        .all()
    )
    if any(
        body.start_time is None
        or item.start_time is None
        or max(body.start_time, item.start_time) < min(body.end_time, item.end_time)
        for item in existing
    ):
        raise HTTPException(409, "Ca trực đã được đóng trong khoảng thời gian này.")

    open_appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == body.doctor_id,
            Appointment.appointment_date == body.exception_date,
            Appointment.status.in_(
                ["PENDING", "CONFIRMED", "CHECKED_IN", "IN_PROGRESS"]
            ),
        )
        .all()
    )
    if any(
        body.start_time is None
        or max(body.start_time, appt.start_time) < min(body.end_time, appt.end_time)
        for appt in open_appointments
    ):
        raise HTTPException(
            409,
            "Cần chuyển hoặc hủy các lịch hẹn chưa kết thúc trước khi đóng ca trực.",
        )

    item = DoctorScheduleException(
        doctor_id=body.doctor_id,
        exception_date=body.exception_date,
        start_time=body.start_time,
        end_time=body.end_time,
        reason=body.reason,
        created_by_user_id=admin.user_id,
        is_active=True,
    )
    db.add(item)
    flush_or_error(db)
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="SCHEDULE_EXCEPTION_CREATED",
        entity_type="DoctorScheduleException",
        entity_id=item.exception_id,
        clinic_id=getattr(doctor, "clinic_id", None),
        details={"doctor_id": body.doctor_id},
    )
    commit_or_error(db)
    db.refresh(item)
    return _exception_dict(item)


@router.delete("/exceptions/{exception_id}")
def deactivate_schedule_exception(
    exception_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    if get_settings().app_mode != "production":
        raise HTTPException(403, "Ngoại lệ ca trực chỉ áp dụng trong chế độ production.")
    item = db.get(DoctorScheduleException, exception_id)
    if item is None or not item.is_active:
        raise HTTPException(404, "Không tìm thấy ngoại lệ ca trực đang hoạt động.")
    lock_doctors(db, doctor_id=item.doctor_id)
    item.is_active = False
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="SCHEDULE_EXCEPTION_DEACTIVATED",
        entity_type="DoctorScheduleException",
        entity_id=exception_id,
        details={"doctor_id": item.doctor_id},
    )
    commit_or_error(db)
    return _exception_dict(item)


def _sched_dict(s: DoctorSchedule) -> dict:
    return {
        "ScheduleID": s.schedule_id,
        "DoctorID": s.doctor_id,
        "DayOfWeek": s.day_of_week,
        "StartTime": s.start_time,
        "EndTime": s.end_time,
        "SlotDuration": s.slot_duration,
        "IsActive": s.is_active,
    }


def _check_overlap(db: Session, doctor_id: int, day: int, start, end, exclude_id: int = None):
    query = db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor_id,
        DoctorSchedule.day_of_week == day,
        DoctorSchedule.is_active,
        DoctorSchedule.start_time < end,
        DoctorSchedule.end_time > start,
    )
    if exclude_id:
        query = query.filter(DoctorSchedule.schedule_id != exclude_id)
    return query.first() is not None


@router.get("/", response_model=list[schemas.ScheduleOut])
def get_schedules(
    doctor_id: int = None, db: Session = Depends(get_db), admin=Depends(require_admin)
):
    query = db.query(DoctorSchedule)
    if doctor_id:
        query = query.filter(DoctorSchedule.doctor_id == doctor_id)
    return [_sched_dict(s) for s in query.all()]


@router.post("/", response_model=schemas.ScheduleOut)
def create_schedule(
    data: schemas.ScheduleCreate, db: Session = Depends(get_db), admin=Depends(require_admin)
):
    lock_doctors(db, doctor_id=data.DoctorID)
    doctor = db.query(Doctor).filter(Doctor.doctor_id == data.DoctorID).first()
    if not doctor or not getattr(doctor, "is_active", True):
        raise HTTPException(422, "Bác sĩ không tồn tại hoặc đã ngừng hoạt động")
    if data.StartTime >= data.EndTime:
        raise HTTPException(422, "Giờ bắt đầu phải nhỏ hơn giờ kết thúc")
    if _check_overlap(db, data.DoctorID, data.DayOfWeek, data.StartTime, data.EndTime):
        raise HTTPException(409, "Lịch bị trùng với ca làm việc đã có của bác sĩ này")

    # Soft-deleted schedules may still be protected by a database unique key.
    # Reuse the exact inactive row instead of attempting an indistinguishable
    # insert, so deleting then adding the same shift is a supported workflow.
    inactive = (
        db.query(DoctorSchedule)
        .filter(
            DoctorSchedule.doctor_id == data.DoctorID,
            DoctorSchedule.day_of_week == data.DayOfWeek,
            DoctorSchedule.start_time == data.StartTime,
            DoctorSchedule.end_time == data.EndTime,
            ~DoctorSchedule.is_active,
        )
        .first()
    )
    if inactive:
        inactive.slot_duration = data.SlotDuration
        inactive.is_active = True
        record_audit_event(
            db,
            actor_user_id=getattr(admin, "user_id", None),
            actor_role="ADMIN",
            action="SCHEDULE_REACTIVATED",
            entity_type="DoctorSchedule",
            entity_id=inactive.schedule_id,
            clinic_id=getattr(doctor, "clinic_id", None),
            details={"doctor_id": data.DoctorID},
        )
        commit_or_error(db)
        db.refresh(inactive)
        return _sched_dict(inactive)

    obj = DoctorSchedule(
        doctor_id=data.DoctorID,
        day_of_week=data.DayOfWeek,
        start_time=data.StartTime,
        end_time=data.EndTime,
        slot_duration=data.SlotDuration,
    )
    db.add(obj)
    flush_or_error(db)
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="SCHEDULE_CREATED",
        entity_type="DoctorSchedule",
        entity_id=obj.schedule_id,
        clinic_id=getattr(doctor, "clinic_id", None),
        details={"doctor_id": data.DoctorID},
    )
    commit_or_error(db)
    db.refresh(obj)
    return _sched_dict(obj)


@router.put("/{schedule_id}", response_model=schemas.ScheduleOut)
def update_schedule(
    schedule_id: int,
    data: schemas.ScheduleUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    obj = db.query(DoctorSchedule).filter(DoctorSchedule.schedule_id == schedule_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy lịch làm việc")
    lock_doctors(db, doctor_id=obj.doctor_id)

    updates = data.model_dump(exclude_unset=True)
    new_day = updates.get("DayOfWeek", obj.day_of_week)
    new_start = updates.get("StartTime", obj.start_time)
    new_end = updates.get("EndTime", obj.end_time)
    new_duration = updates.get("SlotDuration", obj.slot_duration)
    new_active = updates.get("IsActive", obj.is_active)
    try:
        schemas._valid_shift(new_start, new_end, new_duration)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if new_active and _check_overlap(
        db, obj.doctor_id, new_day, new_start, new_end, exclude_id=schedule_id
    ):
        raise HTTPException(409, "Lịch bị trùng với ca làm việc khác")
    replacement = SimpleNamespace(
        schedule_id=schedule_id,
        day_of_week=new_day,
        start_time=new_start,
        end_time=new_end,
        slot_duration=new_duration,
        is_active=new_active,
    )
    require_appointments_covered(
        db, obj.doctor_id, replacement, excluded_schedule_id=schedule_id
    )

    mapping = {
        "DayOfWeek": "day_of_week",
        "StartTime": "start_time",
        "EndTime": "end_time",
        "SlotDuration": "slot_duration",
        "IsActive": "is_active",
    }
    for field, value in updates.items():
        setattr(obj, mapping.get(field, field), value)
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="SCHEDULE_UPDATED",
        entity_type="DoctorSchedule",
        entity_id=schedule_id,
        details={"doctor_id": obj.doctor_id},
    )
    commit_or_error(db)
    db.refresh(obj)
    return _sched_dict(obj)


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = db.query(DoctorSchedule).filter(DoctorSchedule.schedule_id == schedule_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy lịch làm việc")
    lock_doctors(db, doctor_id=obj.doctor_id)
    require_appointments_covered(db, obj.doctor_id, excluded_schedule_id=schedule_id)
    obj.is_active = False
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="SCHEDULE_DEACTIVATED",
        entity_type="DoctorSchedule",
        entity_id=schedule_id,
        details={"doctor_id": obj.doctor_id},
    )
    commit_or_error(db)
    return {"message": "Đã xóa lịch làm việc"}
