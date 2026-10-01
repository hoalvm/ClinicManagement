from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.models import Doctor, Specialty

from .. import schemas
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/specialties", tags=["Specialties"])


@router.get("/", response_model=list[schemas.SpecialtyOut])
def get_specialties(db: Session = Depends(get_db), admin=Depends(require_admin)):
    specialties = db.query(Specialty).all()
    return [
        {
            "SpecialtyID": s.specialty_id,
            "SpecialtyName": s.specialty_name,
            "Description": s.description,
            "IsActive": s.is_active,
        }
        for s in specialties
    ]


@router.post("/", response_model=schemas.SpecialtyOut)
def create_specialty(
    data: schemas.SpecialtyCreate, db: Session = Depends(get_db), admin=Depends(require_admin)
):
    if db.query(Specialty).filter(Specialty.specialty_name == data.SpecialtyName).first():
        raise HTTPException(400, "Tên chuyên khoa đã tồn tại")
    obj = Specialty(specialty_name=data.SpecialtyName, description=data.Description)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {
        "SpecialtyID": obj.specialty_id,
        "SpecialtyName": obj.specialty_name,
        "Description": obj.description,
        "IsActive": obj.is_active,
    }


@router.put("/{specialty_id}", response_model=schemas.SpecialtyOut)
def update_specialty(
    specialty_id: int,
    data: schemas.SpecialtyUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    obj = db.query(Specialty).filter(Specialty.specialty_id == specialty_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy chuyên khoa")

    if (
        data.SpecialtyName
        and db.query(Specialty)
        .filter(
            Specialty.specialty_name == data.SpecialtyName, Specialty.specialty_id != specialty_id
        )
        .first()
    ):
        raise HTTPException(400, "Tên chuyên khoa đã tồn tại")

    mapping = {
        "SpecialtyName": "specialty_name",
        "Description": "description",
        "IsActive": "is_active",
    }
    for field, value in data.dict(exclude_unset=True).items():
        setattr(obj, mapping.get(field, field), value)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Không thể cập nhật chuyên khoa: {str(e)}") from e
    db.refresh(obj)
    return {
        "SpecialtyID": obj.specialty_id,
        "SpecialtyName": obj.specialty_name,
        "Description": obj.description,
        "IsActive": obj.is_active,
    }


@router.delete("/{specialty_id}")
def delete_specialty(
    specialty_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)
):
    obj = db.query(Specialty).filter(Specialty.specialty_id == specialty_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy chuyên khoa")
    active_doctor_count = (
        db.query(Doctor)
        .filter(
            Doctor.specialty_id == specialty_id,
            Doctor.is_active.is_(True),
        )
        .count()
    )
    if isinstance(active_doctor_count, int) and active_doctor_count > 0:
        raise HTTPException(
            400,
            f"Không thể ngừng hoạt động chuyên khoa vì còn {active_doctor_count} bác sĩ đang hoạt động.",
        )
    obj.is_active = False
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Không thể vô hiệu hóa chuyên khoa: {str(e)}") from e
    return {"message": "Đã vô hiệu hóa chuyên khoa"}
