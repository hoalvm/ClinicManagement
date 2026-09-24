from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas
from ..database import get_db
from ..deps import require_admin
from backend.app.models import Clinic, Doctor

router = APIRouter(prefix="/clinics", tags=["Clinics"])


def _clinic_dict(c: Clinic) -> dict:
    return {
        "ClinicID": c.clinic_id, "ClinicName": c.clinic_name,
        "Address": c.address, "Phone": c.phone, "IsActive": c.is_active,
    }


@router.get("/", response_model=list[schemas.ClinicOut])
def get_clinics(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return [_clinic_dict(c) for c in db.query(Clinic).all()]


@router.post("/", response_model=schemas.ClinicOut)
def create_clinic(data: schemas.ClinicCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = Clinic(clinic_name=data.ClinicName, address=data.Address, phone=data.Phone)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _clinic_dict(obj)


@router.put("/{clinic_id}", response_model=schemas.ClinicOut)
def update_clinic(clinic_id: int, data: schemas.ClinicUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy phòng khám")
    mapping = {
        "ClinicName": "clinic_name", "Address": "address",
        "Phone": "phone", "IsActive": "is_active",
    }
    for field, value in data.dict(exclude_unset=True).items():
        setattr(obj, mapping.get(field, field), value)
    db.commit()
    db.refresh(obj)
    return _clinic_dict(obj)


@router.delete("/{clinic_id}")
def delete_clinic(clinic_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    obj = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy phòng khám")
    obj.is_active = False
    db.commit()
    return {"message": "Đã vô hiệu hóa phòng khám"}