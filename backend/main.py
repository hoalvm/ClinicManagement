from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.database import engine, Base, get_db
from backend.models import User, Doctor, Patient, Appointment, AppointmentStatus, MedicalRecord, Prescription, PrescriptionItem
from backend.schemas import (
    DoctorLoginRequest, DoctorLoginResponse,
    AppointmentResponse, CompleteExamRequest, PatientResponse
)
from backend.security import verify_password, create_access_token

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hệ Thống Phòng Khám - Phân Hệ Bác Sĩ", version="1.0.0")

@app.post("/api/v1/doctor/login", response_model=DoctorLoginResponse)
def login(payload: DoctorLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.Username == payload.username, User.Role == "DOCTOR").first()
    if not user or not verify_password(payload.password, user.PasswordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu Bác sĩ không chính xác!"
        )
    
    doctor = db.query(Doctor).filter(Doctor.UserID == user.UserID).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ bác sĩ của tài khoản này")

    token = create_access_token(data={"sub": str(doctor.DoctorID), "role": "DOCTOR"})
    return DoctorLoginResponse(
        access_token=token,
        doctor_id=doctor.DoctorID,
        doctor_name=user.FullName,
        license_number=doctor.LicenseNumber
    )

@app.get("/api/v1/doctor/schedule", response_model=List[AppointmentResponse])
def get_schedule(doctor_id: int, db: Session = Depends(get_db)):
    appts = db.query(Appointment).filter(
        Appointment.DoctorID == doctor_id,
        Appointment.Status.in_([AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_PROGRESS])
    ).order_by(Appointment.StartTime.asc()).all()

    result = []
    for a in appts:
        result.append(AppointmentResponse(
            AppointmentID=a.AppointmentID,
            AppointmentDate=a.AppointmentDate,
            StartTime=a.StartTime,
            EndTime=a.EndTime,
            Reason=a.Reason,
            Status=a.Status.value,
            Patient=PatientResponse(
                PatientID=a.patient.PatientID,
                FullName=a.patient.user.FullName,
                Phone=a.patient.user.Phone,
                DateOfBirth=a.patient.DateOfBirth,
                Gender=a.patient.Gender,
                Address=a.patient.Address
            )
        ))
    return result

@app.put("/api/v1/doctor/appointments/{appointment_id}/accept")
def accept_patient(appointment_id: int, doctor_id: int, db: Session = Depends(get_db)):
    appt = db.query(Appointment).filter(
        Appointment.AppointmentID == appointment_id,
        Appointment.DoctorID == doctor_id
    ).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc hẹn")
    if appt.Status != AppointmentStatus.CHECKED_IN:
        raise HTTPException(status_code=400, detail=f"Cuộc hẹn đang ở trạng thái: {appt.Status}")

    appt.Status = AppointmentStatus.IN_PROGRESS
    db.commit()
    return {"message": "Đã tiếp nhận bệnh nhân thành công"}

@app.post("/api/v1/doctor/appointments/{appointment_id}/complete")
def complete_examination(appointment_id: int, payload: CompleteExamRequest, db: Session = Depends(get_db)):
    appt = db.query(Appointment).filter(Appointment.AppointmentID == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc hẹn")
    if appt.Status != AppointmentStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Cuộc hẹn phải ở trạng thái IN_PROGRESS mới có thể hoàn tất")

    try:
        # 1. Ghi nhận Medical Record
        record = MedicalRecord(
            AppointmentID=appt.AppointmentID,
            Symptoms=payload.symptoms,
            Diagnosis=payload.diagnosis,
            Notes=payload.notes
        )
        db.add(record)
        db.flush()

        # 2. Kê đơn thuốc
        if payload.prescription_items:
            pres = Prescription(MedicalRecordID=record.MedicalRecordID)
            db.add(pres)
            db.flush()

            for item in payload.prescription_items:
                p_item = PrescriptionItem(
                    PrescriptionID=pres.PrescriptionID,
                    MedicineName=item.medicine_name,
                    Quantity=item.quantity,
                    Dosage=item.dosage,
                    Instructions=item.instructions
                )
                db.add(p_item)

        # 3. Chuyển trạng thái sang COMPLETED
        appt.Status = AppointmentStatus.COMPLETED
        db.commit()
        return {"status": "success", "message": "Hoàn tất ca khám thành công!"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi cơ sở dữ liệu: {str(e)}")