"""API router for Doctor Portal operations: schedule, examination, prescription."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.deps import get_current_user
from backend.app.models import (
    Appointment,
    Doctor,
    MedicalRecord,
    Patient,
    Prescription,
    PrescriptionItem,
    User,
)
from backend.app.auth import verify_password, create_access_token

router = APIRouter(prefix="/api/v1/doctor", tags=["Doctor Portal"])


# ------------------- Schemas -------------------
class PrescriptionItemIn(BaseModel):
    medicine_name: str
    dosage: Optional[str] = None
    quantity: int
    instructions: Optional[str] = None


class CompleteExamRequest(BaseModel):
    symptoms: str
    diagnosis: str
    notes: Optional[str] = None
    prescription_items: Optional[List[PrescriptionItemIn]] = []


class DoctorLoginRequest(BaseModel):
    username: str
    password: str


class DoctorLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    doctor_id: int
    doctor_name: str
    license_number: Optional[str] = "N/A"


# ------------------- Endpoints -------------------
@router.post("/login", response_model=DoctorLoginResponse)
def doctor_login(payload: DoctorLoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.username == payload.username, User.role == "DOCTOR")
        .first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu Bác sĩ không chính xác!",
        )

    doctor = db.query(Doctor).filter(Doctor.user_id == user.user_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hồ sơ bác sĩ của tài khoản này.",
        )

    token = create_access_token(
        {"sub": str(user.user_id), "username": user.username, "role": "DOCTOR"}
    )
    return DoctorLoginResponse(
        access_token=token,
        doctor_id=doctor.doctor_id,
        doctor_name=user.full_name,
        license_number=doctor.license_number or "N/A",
    )


@router.get("/profile")
def get_doctor_profile(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.user_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ bác sĩ")
    return {
        "doctor_id": doctor.doctor_id,
        "doctor_name": current_user.full_name,
        "license_number": doctor.license_number or "N/A",
        "specialty_name": doctor.specialty.specialty_name if doctor.specialty else None,
        "clinic_name": doctor.clinic.clinic_name if doctor.clinic else None,
    }


@router.get("/schedule")
def get_schedule(doctor_id: int, db: Session = Depends(get_db)):
    appts = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_(["CHECKED_IN", "IN_PROGRESS", "CONFIRMED"]),
        )
        .order_by(Appointment.start_time.asc())
        .all()
    )

    result = []
    for a in appts:
        patient = a.patient
        patient_user = patient.user if patient else None
        result.append(
            {
                "AppointmentID": a.appointment_id,
                "AppointmentDate": str(a.appointment_date),
                "StartTime": str(a.start_time)[:5] if a.start_time else "",
                "EndTime": str(a.end_time)[:5] if a.end_time else "",
                "Reason": a.reason or "Khám bệnh",
                "Status": a.status,
                "Patient": {
                    "PatientID": patient.patient_id if patient else 0,
                    "FullName": patient_user.full_name if patient_user else "Bệnh nhân",
                    "Phone": patient_user.phone if patient_user else "—",
                    "DateOfBirth": str(patient.date_of_birth)
                    if (patient and patient.date_of_birth)
                    else "—",
                    "Gender": patient.gender if (patient and patient.gender) else "—",
                    "Address": patient.address if (patient and patient.address) else "—",
                },
            }
        )
    return result


@router.put("/appointments/{appointment_id}/accept")
def accept_patient(
    appointment_id: int, doctor_id: Optional[int] = None, db: Session = Depends(get_db)
):
    query = db.query(Appointment).filter(Appointment.appointment_id == appointment_id)
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)
    appt = query.first()

    if not appt:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc hẹn")
    appt.status = "IN_PROGRESS"
    db.commit()
    return {"message": "Đã tiếp nhận bệnh nhân thành công"}


@router.post("/appointments/{appointment_id}/complete")
def complete_examination(
    appointment_id: int, payload: CompleteExamRequest, db: Session = Depends(get_db)
):
    appt = (
        db.query(Appointment)
        .filter(Appointment.appointment_id == appointment_id)
        .first()
    )
    if not appt:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc hẹn")

    try:
        # 1. Ghi nhận Medical Record
        record = MedicalRecord(
            appointment_id=appt.appointment_id,
            symptoms=payload.symptoms,
            diagnosis=payload.diagnosis,
            notes=payload.notes or "",
        )
        db.add(record)
        db.flush()

        # 2. Kê đơn thuốc
        if payload.prescription_items:
            pres = Prescription(medical_record_id=record.medical_record_id)
            db.add(pres)
            db.flush()

            for item in payload.prescription_items:
                p_item = PrescriptionItem(
                    prescription_id=pres.prescription_id,
                    medicine_name=item.medicine_name,
                    quantity=item.quantity,
                    dosage=item.dosage or "",
                    instructions=item.instructions or "",
                )
                db.add(p_item)

        # 3. Chuyển trạng thái sang COMPLETED
        appt.status = "COMPLETED"
        db.commit()
        return {"status": "success", "message": "Hoàn tất ca khám thành công!"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi cơ sở dữ liệu: {str(e)}")
