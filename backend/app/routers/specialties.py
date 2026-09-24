from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas
from ..database import get_db
from ..deps import require_admin
from backend.app.models import Specialty, Doctor

router = APIRouter(prefix="/specialties", tags=["Specialties"])


@router.get("/", response_model=list[schemas.SpecialtyOut])
def get_specialties(db: Session = Depends(get_db), admin=Depends(require_admin)):
    specialties = db.query(Specialty).all()
    return [
        {
            "SpecialtyID": s.specialty_id, "SpecialtyName": s.specialty_name,
            "Description": s.description, "IsActive": s.is_active,
        }
        for s in specialties
    ]


@router.post("/", response_model=schemas.SpecialtyOut)
def create_specialty(data: schemas.SpecialtyCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if db.query(Specialty).filter(Specialty.specialty_name == data.SpecialtyName).first():
        raise HTTPException(400, "Tên chuyên khoa đã tồn tại")
    obj = Specialty(specialty_name=data.SpecialtyName, description=data.Description)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {
        "SpecialtyID": obj.specialty_id, "SpecialtyName": obj.specialty_name,
        "Description": obj.description, "IsActive": obj.is_active,
    }


@router.put("/{specialty_id}", response_model=schemas.SpecialtyOut)
def update_specialty(specialty_id: int, data: schemas.SpecialtyUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = db.query(Specialty).filter(Specialty.specialty_id == specialty_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy chuyên khoa")
    mapping = {"SpecialtyName": "specialty_name", "Description": "description", "IsActive": "is_active"}
    for field, value in data.dict(exclude_unset=True).items():
        setattr(obj, mapping.get(field, field), value)
    db.commit()
    db.refresh(obj)
    return {
        "SpecialtyID": obj.specialty_id, "SpecialtyName": obj.specialty_name,
        "Description": obj.description, "IsActive": obj.is_active,
    }


@router.delete("/{specialty_id}")
def delete_specialty(specialty_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = db.query(Specialty).filter(Specialty.specialty_id == specialty_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy chuyên khoa")
    if db.query(Doctor).filter(Doctor.specialty_id == specialty_id).first():
        raise HTTPException(400, "Không thể xóa: đang có bác sĩ thuộc chuyên khoa này")
    obj.is_active = False
    db.commit()
    return {"message": "Đã vô hiệu hóa chuyên khoa"}