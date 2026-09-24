from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas
from ..database import get_db
from ..deps import require_admin
from backend.app.models import Doctor, DoctorSchedule

router = APIRouter(prefix="/schedules", tags=["DoctorSchedules"])


def _sched_dict(s: DoctorSchedule) -> dict:
    return {
        "ScheduleID": s.schedule_id, "DoctorID": s.doctor_id,
        "DayOfWeek": s.day_of_week, "StartTime": s.start_time,
        "EndTime": s.end_time, "SlotDuration": s.slot_duration, "IsActive": s.is_active,
    }


def _check_overlap(db: Session, doctor_id: int, day: int, start, end, exclude_id: int = None):
    query = db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor_id,
        DoctorSchedule.day_of_week == day,
        DoctorSchedule.is_active == True,
        DoctorSchedule.start_time < end,
        DoctorSchedule.end_time > start,
    )
    if exclude_id:
        query = query.filter(DoctorSchedule.schedule_id != exclude_id)
    return query.first() is not None


@router.get("/", response_model=list[schemas.ScheduleOut])
def get_schedules(doctor_id: int = None, db: Session = Depends(get_db), admin=Depends(require_admin)):
    query = db.query(DoctorSchedule)
    if doctor_id:
        query = query.filter(DoctorSchedule.doctor_id == doctor_id)
    return [_sched_dict(s) for s in query.all()]


@router.post("/", response_model=schemas.ScheduleOut)
def create_schedule(data: schemas.ScheduleCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if not db.query(Doctor).filter(Doctor.doctor_id == data.DoctorID).first():
        raise HTTPException(400, "Bác sĩ không tồn tại")
    if data.StartTime >= data.EndTime:
        raise HTTPException(400, "Giờ bắt đầu phải nhỏ hơn giờ kết thúc")
    if _check_overlap(db, data.DoctorID, data.DayOfWeek, data.StartTime, data.EndTime):
        raise HTTPException(400, "Lịch bị trùng với ca làm việc đã có của bác sĩ này")

    obj = DoctorSchedule(
        doctor_id=data.DoctorID, day_of_week=data.DayOfWeek,
        start_time=data.StartTime, end_time=data.EndTime, slot_duration=data.SlotDuration,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _sched_dict(obj)


@router.put("/{schedule_id}", response_model=schemas.ScheduleOut)
def update_schedule(schedule_id: int, data: schemas.ScheduleUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = db.query(DoctorSchedule).filter(DoctorSchedule.schedule_id == schedule_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy lịch làm việc")

    new_day = data.DayOfWeek if data.DayOfWeek is not None else obj.day_of_week
    new_start = data.StartTime if data.StartTime is not None else obj.start_time
    new_end = data.EndTime if data.EndTime is not None else obj.end_time
    if new_start >= new_end:
        raise HTTPException(400, "Giờ bắt đầu phải nhỏ hơn giờ kết thúc")
    if _check_overlap(db, obj.doctor_id, new_day, new_start, new_end, exclude_id=schedule_id):
        raise HTTPException(400, "Lịch bị trùng với ca làm việc khác")

    mapping = {
        "DayOfWeek": "day_of_week", "StartTime": "start_time",
        "EndTime": "end_time", "SlotDuration": "slot_duration", "IsActive": "is_active",
    }
    for field, value in data.dict(exclude_unset=True).items():
        setattr(obj, mapping.get(field, field), value)
    db.commit()
    db.refresh(obj)
    return _sched_dict(obj)


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = db.query(DoctorSchedule).filter(DoctorSchedule.schedule_id == schedule_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy lịch làm việc")
    obj.is_active = False
    db.commit()
    return {"message": "Đã xóa lịch làm việc"}