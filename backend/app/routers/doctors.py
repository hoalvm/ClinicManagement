from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas, auth
from ..database import get_db
from ..deps import require_admin
from backend.app.models import User, Doctor, Specialty, Clinic

router = APIRouter(prefix="/doctors", tags=["Doctors"])


def _to_doctor_out(d: Doctor) -> dict:
    return {
        "DoctorID": d.doctor_id,
        "UserID": d.user_id,
        "FullName": d.user.full_name if d.user else "",
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
def create_doctor(data: schemas.DoctorCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if db.query(User).filter(User.username == data.Username).first():
        raise HTTPException(400, "Username đã tồn tại")
    if not db.query(Specialty).filter(Specialty.specialty_id == data.SpecialtyID).first():
        raise HTTPException(400, "Chuyên khoa không tồn tại")
    if data.ClinicID and not db.query(Clinic).filter(Clinic.clinic_id == data.ClinicID).first():
        raise HTTPException(400, "Phòng khám không tồn tại")
    if data.LicenseNumber and db.query(Doctor).filter(Doctor.license_number == data.LicenseNumber).first():
        raise HTTPException(400, "Số chứng chỉ hành nghề đã tồn tại")

    new_user = User(
        username=data.Username,
        password_hash=auth.hash_password(data.Password),
        full_name=data.FullName,
        phone=data.Phone,
        email=data.Email,
        role="DOCTOR",
    )
    db.add(new_user)
    db.flush()

    new_doctor = Doctor(
        user_id=new_user.user_id,
        specialty_id=data.SpecialtyID,
        clinic_id=data.ClinicID,
        license_number=data.LicenseNumber,
    )
    db.add(new_doctor)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Không thể tạo hồ sơ bác sĩ: {str(e)}")
    db.refresh(new_doctor)
    return _to_doctor_out(new_doctor)


@router.put("/{doctor_id}", response_model=schemas.DoctorOut)
def update_doctor(doctor_id: int, data: schemas.DoctorUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(404, "Không tìm thấy bác sĩ")

    if data.LicenseNumber and db.query(Doctor).filter(
        Doctor.license_number == data.LicenseNumber, Doctor.doctor_id != doctor_id
    ).first():
        raise HTTPException(400, "Số chứng chỉ hành nghề đã được sử dụng bởi bác sĩ khác")

    mapping = {
        "SpecialtyID": "specialty_id", "ClinicID": "clinic_id",
        "LicenseNumber": "license_number", "IsActive": "is_active",
    }
    for field, value in data.dict(exclude_unset=True).items():
        setattr(doctor, mapping.get(field, field), value)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"Không thể cập nhật hồ sơ bác sĩ: {str(e)}")
    db.refresh(doctor)
    return _to_doctor_out(doctor)


@router.delete("/{doctor_id}")
def delete_doctor(doctor_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(404, "Không tìm thấy bác sĩ")
    doctor.is_active = False
    if doctor.user:
        doctor.user.is_active = False
    db.commit()
    return {"message": "Đã vô hiệu hóa bác sĩ"}