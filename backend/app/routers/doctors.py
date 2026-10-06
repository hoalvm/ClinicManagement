from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.audit import record_audit_event
from backend.app.core.config import get_settings
from backend.app.core.phone import normalize_phone
from backend.app.core.security import revoke_user_sessions
from backend.app.models import Clinic, Doctor, Specialty, User

from .. import auth, schemas
from ..database import get_db
from ..deps import require_admin
from ._admin_guards import (
    commit_or_error,
    flush_or_error,
    lock_catalog,
    lock_doctors,
    require_no_open_appointments,
)

router = APIRouter(prefix="/doctors", tags=["Doctors"])


def _to_doctor_out(d: Doctor) -> dict:
    return {
        "DoctorID": d.doctor_id,
        "UserID": d.user_id,
        "FullName": getattr(d.user, "full_name", "") if d.user else "",
        "SpecialtyID": d.specialty_id,
        "SpecialtyName": d.specialty.specialty_name if d.specialty else None,
        "ClinicID": d.clinic_id,
        "ClinicName": d.clinic.clinic_name if d.clinic else None,
        "LicenseNumber": d.license_number,
        "IsActive": d.is_active,
    }


@router.get("/", response_model=list[schemas.DoctorOut])
def get_doctors(db: Session = Depends(get_db), admin=Depends(require_admin)):
    doctors = db.query(Doctor).all()
    return [_to_doctor_out(d) for d in doctors]


@router.post("/", response_model=schemas.DoctorOut)
def create_doctor(
    data: schemas.DoctorCreate, db: Session = Depends(get_db), admin=Depends(require_admin)
):
    if get_settings().app_mode == "production" and (
        not data.LicenseNumber
        or data.LicenseNumber.upper().startswith("DEMO")
        or data.Username.lower() in {f"doctor{number:02d}" for number in range(1, 6)}
    ):
        raise HTTPException(422, "Production yêu cầu số giấy phép đã đối chiếu và định danh bác sĩ thật.")
    lock_catalog(db)
    if db.query(User).filter(User.username == data.Username).first():
        raise HTTPException(409, "Username đã tồn tại")
    specialty = db.query(Specialty).filter(Specialty.specialty_id == data.SpecialtyID).first()
    if not specialty or not getattr(specialty, "is_active", True):
        raise HTTPException(422, "Chuyên khoa không tồn tại hoặc đã ngừng hoạt động")
    clinic = db.query(Clinic).filter(Clinic.clinic_id == data.ClinicID).first()
    if not clinic or not getattr(clinic, "is_active", True):
        raise HTTPException(422, "Phòng khám không tồn tại hoặc đã ngừng hoạt động")
    if (
        data.LicenseNumber
        and db.query(Doctor).filter(Doctor.license_number == data.LicenseNumber).first()
    ):
        raise HTTPException(409, "Số chứng chỉ hành nghề đã tồn tại")

    new_user = User(
        username=data.Username,
        password_hash=auth.hash_password(data.Password),
        full_name=data.FullName,
        phone=normalize_phone(data.Phone),
        email=data.Email,
        role="DOCTOR",
    )
    db.add(new_user)
    flush_or_error(db)

    new_doctor = Doctor(
        user_id=new_user.user_id,
        specialty_id=data.SpecialtyID,
        clinic_id=data.ClinicID,
        license_number=data.LicenseNumber,
    )
    db.add(new_doctor)
    flush_or_error(db)
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="DOCTOR_CREATED",
        entity_type="Doctor",
        entity_id=new_doctor.doctor_id,
        clinic_id=new_doctor.clinic_id,
    )
    commit_or_error(db)
    db.refresh(new_doctor)
    return _to_doctor_out(new_doctor)


@router.put("/{doctor_id}", response_model=schemas.DoctorOut)
def update_doctor(
    doctor_id: int,
    data: schemas.DoctorUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    lock_catalog(db)
    lock_doctors(db, doctor_id=doctor_id)
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(404, "Không tìm thấy bác sĩ")
    updates = data.model_dump(exclude_unset=True)
    if get_settings().app_mode == "production" and updates.get("IsActive") is not False:
        target_license = (
            data.LicenseNumber
            if "LicenseNumber" in data.model_fields_set
            else doctor.license_number
        )
        if not target_license or target_license.upper().startswith("DEMO"):
            raise HTTPException(422, "Bác sĩ production cần số giấy phép hành nghề đã đối chiếu.")
    if ("SpecialtyID" in updates and updates["SpecialtyID"] != doctor.specialty_id) or (
        "ClinicID" in updates and updates["ClinicID"] != doctor.clinic_id
    ) or updates.get("IsActive") is False:
        require_no_open_appointments(db, doctor_id=doctor_id)
    if "SpecialtyID" in updates or updates.get("IsActive") is True:
        target_specialty_id = updates.get("SpecialtyID", doctor.specialty_id)
        specialty = db.query(Specialty).filter(Specialty.specialty_id == target_specialty_id).first()
        if not specialty or not getattr(specialty, "is_active", True):
            raise HTTPException(422, "Chuyên khoa không tồn tại hoặc đã ngừng hoạt động")
    if "ClinicID" in updates or updates.get("IsActive") is True:
        target_clinic_id = updates.get("ClinicID", doctor.clinic_id)
        clinic = db.query(Clinic).filter(Clinic.clinic_id == target_clinic_id).first()
        if not clinic or not getattr(clinic, "is_active", True):
            raise HTTPException(422, "Phòng khám không tồn tại hoặc đã ngừng hoạt động")
    if (
        updates.get("IsActive") is True
        and doctor.user
        and getattr(doctor.user, "role", "DOCTOR") != "DOCTOR"
    ):
        raise HTTPException(409, "Tài khoản bác sĩ không còn role DOCTOR")

    if (
        data.LicenseNumber
        and db.query(Doctor)
        .filter(Doctor.license_number == data.LicenseNumber, Doctor.doctor_id != doctor_id)
        .first()
    ):
        raise HTTPException(409, "Số chứng chỉ hành nghề đã được sử dụng bởi bác sĩ khác")

    mapping = {
        "SpecialtyID": "specialty_id",
        "ClinicID": "clinic_id",
        "LicenseNumber": "license_number",
        "IsActive": "is_active",
    }
    for field, value in updates.items():
        setattr(doctor, mapping.get(field, field), value)
        if field == "IsActive" and doctor.user:
            doctor.user.is_active = bool(value)

    if updates and doctor.user:
        revoke_user_sessions(db, doctor.user_id)
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="DOCTOR_UPDATED",
        entity_type="Doctor",
        entity_id=doctor_id,
        clinic_id=doctor.clinic_id,
    )
    commit_or_error(db)
    db.refresh(doctor)
    return _to_doctor_out(doctor)


@router.delete("/{doctor_id}")
def delete_doctor(doctor_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    lock_catalog(db)
    lock_doctors(db, doctor_id=doctor_id)
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(404, "Không tìm thấy bác sĩ")
    require_no_open_appointments(db, doctor_id=doctor_id)
    doctor.is_active = False
    if doctor.user:
        doctor.user.is_active = False
    revoke_user_sessions(db, doctor.user_id)
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="DOCTOR_DEACTIVATED",
        entity_type="Doctor",
        entity_id=doctor_id,
        clinic_id=doctor.clinic_id,
    )
    commit_or_error(db)
    return {"message": "Đã vô hiệu hóa bác sĩ"}
