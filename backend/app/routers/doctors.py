from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, auth
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/doctors", tags=["Doctors"])

def _to_doctor_out(d: models.Doctor) -> dict:
    return {
        "DoctorID": d.DoctorID,
        "UserID": d.UserID,
        "FullName": d.user.FullName,
        "SpecialtyID": d.SpecialtyID,
        "SpecialtyName": d.specialty.SpecialtyName if d.specialty else None,
        "ClinicID": d.ClinicID,
        "ClinicName": d.clinic.ClinicName if d.clinic else None,
        "LicenseNumber": d.LicenseNumber,
        "IsActive": d.IsActive,
    }

@router.get("/", response_model=list[schemas.DoctorOut])
def get_doctors(db: Session = Depends(get_db), admin=Depends(require_admin)):
    doctors = db.query(models.Doctor).all()
    return [_to_doctor_out(d) for d in doctors]

@router.post("/", response_model=schemas.DoctorOut)
def create_doctor(data: schemas.DoctorCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if db.query(models.User).filter(models.User.Username == data.Username).first():
        raise HTTPException(400, "Username đã tồn tại")
    if not db.query(models.Specialty).filter(models.Specialty.SpecialtyID == data.SpecialtyID).first():
        raise HTTPException(400, "Chuyên khoa không tồn tại")
    if data.ClinicID and not db.query(models.Clinic).filter(models.Clinic.ClinicID == data.ClinicID).first():
        raise HTTPException(400, "Phòng khám không tồn tại")

    new_user = models.User(
        Username=data.Username,
        PasswordHash=auth.hash_password(data.Password),
        FullName=data.FullName,
        Phone=data.Phone,
        Email=data.Email,
        Role="DOCTOR",
    )
    db.add(new_user)
    db.flush()

    new_doctor = models.Doctor(
        UserID=new_user.UserID,
        SpecialtyID=data.SpecialtyID,
        ClinicID=data.ClinicID,
        LicenseNumber=data.LicenseNumber,
    )
    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)
    return _to_doctor_out(new_doctor)

@router.put("/{doctor_id}", response_model=schemas.DoctorOut)
def update_doctor(doctor_id: int, data: schemas.DoctorUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    doctor = db.query(models.Doctor).filter(models.Doctor.DoctorID == doctor_id).first()
    if not doctor:
        raise HTTPException(404, "Không tìm thấy bác sĩ")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(doctor, field, value)
    db.commit(); db.refresh(doctor)
    return _to_doctor_out(doctor)

@router.delete("/{doctor_id}")
def delete_doctor(doctor_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    doctor = db.query(models.Doctor).filter(models.Doctor.DoctorID == doctor_id).first()
    if not doctor:
        raise HTTPException(404, "Không tìm thấy bác sĩ")
    doctor.IsActive = False
    if doctor.user:
        doctor.user.IsActive = False
    db.commit()
    return {"message": "Đã vô hiệu hóa bác sĩ"}