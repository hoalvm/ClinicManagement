from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/clinics", tags=["Clinics"])

@router.get("/", response_model=list[schemas.ClinicOut])
def get_clinics(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return db.query(models.Clinic).all()

@router.post("/", response_model=schemas.ClinicOut)
def create_clinic(data: schemas.ClinicCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = models.Clinic(**data.dict())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.put("/{clinic_id}", response_model=schemas.ClinicOut)
def update_clinic(clinic_id: int, data: schemas.ClinicUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = db.query(models.Clinic).filter(models.Clinic.ClinicID == clinic_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy phòng khám")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/{clinic_id}")
def delete_clinic(clinic_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = db.query(models.Clinic).filter(models.Clinic.ClinicID == clinic_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy phòng khám")
    obj.IsActive = False
    db.commit()
    return {"message": "Đã vô hiệu hóa phòng khám"}