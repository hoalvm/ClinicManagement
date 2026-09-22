from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/specialties", tags=["Specialties"])

@router.get("/", response_model=list[schemas.SpecialtyOut])
def get_specialties(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return db.query(models.Specialty).all()

@router.post("/", response_model=schemas.SpecialtyOut)
def create_specialty(data: schemas.SpecialtyCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if db.query(models.Specialty).filter(models.Specialty.SpecialtyName == data.SpecialtyName).first():
        raise HTTPException(400, "Tên chuyên khoa đã tồn tại")
    obj = models.Specialty(**data.dict())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/{specialty_id}", response_model=schemas.SpecialtyOut)
def update_specialty(specialty_id: int, data: schemas.SpecialtyUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = db.query(models.Specialty).filter(models.Specialty.SpecialtyID == specialty_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy chuyên khoa")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/{specialty_id}")
def delete_specialty(specialty_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = db.query(models.Specialty).filter(models.Specialty.SpecialtyID == specialty_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy chuyên khoa")
    if db.query(models.Doctor).filter(models.Doctor.SpecialtyID == specialty_id).first():
        raise HTTPException(400, "Không thể xóa: đang có bác sĩ thuộc chuyên khoa này")
    obj.IsActive = False
    db.commit()
    return {"message": "Đã vô hiệu hóa chuyên khoa"}