from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.audit import record_audit_event
from backend.app.models import Clinic

from .. import schemas
from ..database import get_db
from ..deps import require_admin
from ._admin_guards import (
    commit_or_error,
    flush_or_error,
    lock_catalog,
    lock_doctors,
    require_no_open_appointments,
)

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
    lock_catalog(db)
    obj = Clinic(clinic_name=data.ClinicName, address=data.Address, phone=data.Phone)
    db.add(obj)
    flush_or_error(db)
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="CLINIC_CREATED",
        entity_type="Clinic",
        entity_id=obj.clinic_id,
        clinic_id=obj.clinic_id,
    )
    commit_or_error(db)
    db.refresh(obj)
    return _clinic_dict(obj)


@router.put("/{clinic_id}", response_model=schemas.ClinicOut)
def update_clinic(clinic_id: int, data: schemas.ClinicUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    lock_catalog(db)
    obj = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy phòng khám")
    if data.IsActive is False:
        lock_doctors(db, clinic_id=clinic_id)
        require_no_open_appointments(db, clinic_id=clinic_id)
    mapping = {
        "ClinicName": "clinic_name", "Address": "address",
        "Phone": "phone", "IsActive": "is_active",
    }
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, mapping.get(field, field), value)
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="CLINIC_UPDATED",
        entity_type="Clinic",
        entity_id=clinic_id,
        clinic_id=clinic_id,
    )
    commit_or_error(db)
    db.refresh(obj)
    return _clinic_dict(obj)


@router.delete("/{clinic_id}")
def delete_clinic(clinic_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    lock_catalog(db)
    obj = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not obj:
        raise HTTPException(404, "Không tìm thấy phòng khám")
    lock_doctors(db, clinic_id=clinic_id)
    require_no_open_appointments(db, clinic_id=clinic_id)
    obj.is_active = False
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="CLINIC_DEACTIVATED",
        entity_type="Clinic",
        entity_id=clinic_id,
        clinic_id=clinic_id,
    )
    commit_or_error(db)
    return {"message": "Đã vô hiệu hóa phòng khám"}
