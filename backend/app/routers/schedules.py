from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/schedules", tags=["DoctorSchedules"])

def _check_overlap(db: Session, doctor_id: int, day: int, start, end, exclude_id: int = None):
    query = db.query(models.DoctorSchedule).filter(
        models.DoctorSchedule.DoctorID == doctor_id,
        models.DoctorSchedule.DayOfWeek == day,
        models.DoctorSchedule.IsActive == True,
        models.DoctorSchedule.StartTime < end,
        models.DoctorSchedule.EndTime > start,
    )
    if exclude_id:
        query = query.filter(models.DoctorSchedule.ScheduleID != exclude_id)
    return query.first() is not None

@router.get("/", response_model=list[schemas.ScheduleOut])
def get_schedules(doctor_id: int = None, db: Session = Depends(get_db), admin=Depends(require_admin)):
    query = db.query(models.DoctorSchedule)
    if doctor_id:
        query = query.filter(models.DoctorSchedule.DoctorID == doctor_id)
    return query.all()

@router.post("/", response_model=schemas.ScheduleOut)
def create_schedule(data: schemas.ScheduleCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if not db.query(models.Doctor).filter(models.Doctor.DoctorID == data.DoctorID).first():
        raise HTTPException(400, "Bác sĩ không tồn tại")
    if data.StartTime >= data.EndTime:
        raise HTTPException(400, "Giờ bắt đầu phải nhỏ hơn giờ kết thúc")
    if _check_overlap(db, data.DoctorID, data.DayOfWeek, data.StartTime, data.EndTime):
        raise HTTPException(400, "Lịch bị trùng với ca làm việc đã có của bác sĩ này")

    obj = models.DoctorSchedule(**data.dict())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/{schedule_id}", response_model=schemas.ScheduleOut)
def update_schedule(schedule_id: int, data: schemas.ScheduleUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = db.query(models.DoctorSchedule).filter(models.DoctorSchedule.ScheduleID == schedule_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy lịch làm việc")

    new_day = data.DayOfWeek if data.DayOfWeek is not None else obj.DayOfWeek
    new_start = data.StartTime if data.StartTime is not None else obj.StartTime
    new_end = data.EndTime if data.EndTime is not None else obj.EndTime
    if new_start >= new_end:
        raise HTTPException(400, "Giờ bắt đầu phải nhỏ hơn giờ kết thúc")
    if _check_overlap(db, obj.DoctorID, new_day, new_start, new_end, exclude_id=schedule_id):
        raise HTTPException(400, "Lịch bị trùng với ca làm việc khác")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = db.query(models.DoctorSchedule).filter(models.DoctorSchedule.ScheduleID == schedule_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy lịch làm việc")
    obj.IsActive = False
    db.commit()
    return {"message": "Đã xóa lịch làm việc"}