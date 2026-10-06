"""API router for Doctor Portal operations: schedule, examination, prescription."""


from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, or_, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from backend.app.core.audit import record_audit_event
from backend.app.core.clock import clinic_naive_now, clinic_today
from backend.app.core.config import get_settings
from backend.app.core.login_throttle import login_throttle
from backend.app.core.security import create_access_token, verify_password
from backend.app.database import get_db
from backend.app.deps import get_current_user
from backend.app.models import (
    Appointment,
    Doctor,
    MedicalRecord,
    Prescription,
    PrescriptionItem,
    User,
)
from backend.app.services.auth_service import DUMMY_PASSWORD_HASH

router = APIRouter(prefix="/api/v1/doctor", tags=["Doctor Portal"])


# ------------------- Schemas -------------------
class PrescriptionItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    medicine_name: str = Field(..., min_length=1, max_length=150)
    dosage: str | None = Field(None, max_length=255)
    quantity: int = Field(..., gt=0, le=10_000, description="Số lượng thuốc phải lớn hơn 0")
    instructions: str | None = Field(None, max_length=500)

    @field_validator("medicine_name", "dosage", "instructions")
    @classmethod
    def nonblank_if_present(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("A provided text field cannot be blank")
        return value


class CompleteExamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    symptoms: str = Field(..., min_length=1, max_length=1000)
    diagnosis: str = Field(..., min_length=1, max_length=1000)
    notes: str | None = Field(None, max_length=2000)
    late_entry_reason: str | None = Field(None, max_length=500)
    prescription_items: list[PrescriptionItemIn] = Field(default_factory=list, max_length=30)

    @field_validator("symptoms", "diagnosis", "notes", "late_entry_reason")
    @classmethod
    def nonblank_if_present(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("A provided text field cannot be blank")
        return value


class DoctorLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalized_username(cls, value: str) -> str:
        return value.lower()


class DoctorLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    doctor_id: int
    doctor_name: str
    license_number: str | None = "N/A"


class PriorPrescriptionItem(BaseModel):
    medicine_name: str
    quantity: int
    dosage: str | None
    instructions: str | None


class PriorClinicalRecord(BaseModel):
    medical_record_id: int
    appointment_id: int
    examination_date: datetime
    doctor_name: str
    symptoms: str | None
    diagnosis: str | None
    notes: str | None
    late_entry_reason: str | None = None
    prescription_items: list[PriorPrescriptionItem]


class ClinicalContextResponse(BaseModel):
    appointment_id: int
    patient_id: int
    patient_name: str
    date_of_birth: date | None
    gender: str | None
    allergy_status: Literal["NOT_DOCUMENTED"] = "NOT_DOCUMENTED"
    history_scope: Literal["THIS_SYSTEM_ONLY"] = "THIS_SYSTEM_ONLY"
    prior_records_has_more: bool
    prior_records: list[PriorClinicalRecord]


# ------------------- RBAC Dependency -------------------
def require_doctor(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> tuple[User, Doctor]:
    """Only an active doctor may access clinical operations."""
    if current_user.role != "DOCTOR" or not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ bác sĩ đang hoạt động mới có quyền truy cập.",
        )
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.user_id).first()
    if not doctor or not getattr(doctor, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hồ sơ bác sĩ của tài khoản này.",
        )
    return current_user, doctor


# ------------------- Endpoints -------------------
@router.post("/login", response_model=DoctorLoginResponse)
def doctor_login(payload: DoctorLoginRequest, request: Request, db: Session = Depends(get_db)):
    login_throttle.check(request, payload.username)
    user = (
        db.query(User)
        .filter(User.username == payload.username, User.role == "DOCTOR")
        .first()
    )
    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    password_valid = verify_password(payload.password, password_hash)
    if not user or not password_valid:
        login_throttle.failed(request, payload.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu Bác sĩ không chính xác!",
        )

    doctor = db.query(Doctor).filter(Doctor.user_id == user.user_id).first()
    if not user.is_active or not doctor or not doctor.is_active:
        login_throttle.failed(request, payload.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu Bác sĩ không chính xác!",
        )

    login_throttle.succeeded(request, payload.username)
    token = create_access_token(user_id=user.user_id, role="DOCTOR", session=db)
    return DoctorLoginResponse(
        access_token=token,
        doctor_id=doctor.doctor_id,
        doctor_name=user.full_name,
        license_number=doctor.license_number or "N/A",
    )


@router.get("/profile")
def get_doctor_profile(
    auth_info: tuple[User, Doctor] = Depends(require_doctor),
):
    current_user, doctor = auth_info
    return {
        "doctor_id": doctor.doctor_id,
        "doctor_name": current_user.full_name,
        "license_number": doctor.license_number or "N/A",
        "specialty_name": doctor.specialty.specialty_name if doctor.specialty else None,
        "clinic_name": doctor.clinic.clinic_name if doctor.clinic else None,
    }


@router.get("/schedule")
def get_schedule(
    doctor_id: int | None = Query(None, description="Doctor ID"),
    auth_info: tuple[User, Doctor] = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    _current_user, current_doctor = auth_info

    # Determine which doctor's schedule to view
    target_doctor_id = doctor_id
    if target_doctor_id is None:
        target_doctor_id = current_doctor.doctor_id

    # Enforce RBAC: doctor can only see their own schedule; admin can see any
    if current_doctor.doctor_id != target_doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem lịch làm việc của bác sĩ khác.",
        )

    today = clinic_today()
    if get_settings().app_mode == "production":
        queue_filter = or_(
            and_(
                Appointment.appointment_date == today,
                Appointment.status == "CHECKED_IN",
            ),
            and_(
                Appointment.appointment_date <= today,
                Appointment.status == "IN_PROGRESS",
            ),
        )
    else:
        queue_filter = and_(
            Appointment.appointment_date == today,
            Appointment.status.in_(["CHECKED_IN", "IN_PROGRESS"]),
        )

    appts = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == target_doctor_id,
            queue_filter,
        )
        .order_by(Appointment.appointment_date.asc(), Appointment.start_time.asc())
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
                "QueueNumber": getattr(a, "queue_number", None),
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


@router.get(
    "/appointments/{appointment_id}/clinical-context",
    response_model=ClinicalContextResponse,
)
def get_clinical_context(
    appointment_id: int,
    auth_info: tuple[User, Doctor] = Depends(require_doctor),
    db: Session = Depends(get_db),
) -> ClinicalContextResponse:
    """Show prior encounters for the doctor's active patient in this system only."""

    current_user, current_doctor = auth_info
    _lock_appointment(db, appointment_id)
    appt = db.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()
    if appt is None:
        raise HTTPException(404, "Không tìm thấy cuộc hẹn")
    if appt.doctor_id != current_doctor.doctor_id:
        raise HTTPException(403, "Bạn không có quyền xem hồ sơ của ca khám này.")
    today = clinic_today()
    if not (
        (appt.status == "CHECKED_IN" and appt.appointment_date == today)
        or (appt.status == "IN_PROGRESS" and appt.appointment_date <= today)
    ):
        raise HTTPException(409, "Chỉ được xem hồ sơ cho ca chờ khám hôm nay hoặc ca đang khám chưa hoàn tất.")
    context_loaded_at = clinic_naive_now()
    if get_settings().app_mode == "production" and (
        appt.check_in_at is None or context_loaded_at < appt.check_in_at
    ):
        raise HTTPException(409, "Ca khám cần thời điểm check-in hợp lệ trước khi xem lịch sử khám.")

    try:
        patient = appt.patient
        if patient is None or patient.user is None:
            raise HTTPException(409, "Ca khám thiếu hồ sơ bệnh nhân hợp lệ.")
        records = (
            db.query(MedicalRecord)
            .join(Appointment, MedicalRecord.appointment_id == Appointment.appointment_id)
            .options(
                joinedload(MedicalRecord.appointment)
                .joinedload(Appointment.doctor)
                .joinedload(Doctor.user),
                joinedload(MedicalRecord.prescription).selectinload(Prescription.items),
            )
            .filter(
                Appointment.patient_id == appt.patient_id,
                Appointment.appointment_id != appointment_id,
                Appointment.status == "COMPLETED",
                MedicalRecord.examination_date <= clinic_naive_now(),
            )
            .order_by(MedicalRecord.examination_date.desc(), MedicalRecord.medical_record_id.desc())
            .limit(11)
            .all()
        )
        response = ClinicalContextResponse(
            appointment_id=appt.appointment_id,
            patient_id=patient.patient_id,
            patient_name=patient.user.full_name,
            date_of_birth=patient.date_of_birth,
            gender=patient.gender,
            prior_records_has_more=len(records) > 10,
            prior_records=[
                PriorClinicalRecord(
                    medical_record_id=record.medical_record_id,
                    appointment_id=record.appointment_id,
                    examination_date=record.examination_date,
                    doctor_name=record.appointment.doctor.user.full_name,
                    symptoms=record.symptoms,
                    diagnosis=record.diagnosis,
                    notes=record.notes,
                    late_entry_reason=getattr(record, "late_entry_reason", None),
                    prescription_items=[
                        PriorPrescriptionItem(
                            medicine_name=item.medicine_name,
                            quantity=item.quantity,
                            dosage=item.dosage,
                            instructions=item.instructions,
                        )
                        for item in (record.prescription.items if record.prescription else [])
                    ],
                )
                for record in records[:10]
            ],
        )
        if get_settings().app_mode == "production":
            appt.clinical_context_loaded_at = context_loaded_at
            appt.clinical_context_loaded_by_user_id = current_user.user_id
        record_audit_event(
            db,
            actor_user_id=current_user.user_id,
            actor_role="DOCTOR",
            action="CLINICAL_CONTEXT_VIEWED",
            entity_type="Appointment",
            entity_id=appointment_id,
            clinic_id=appt.clinic_id,
            details={"doctor_id": current_doctor.doctor_id},
        )
        db.commit()
        return response
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(500, "Không thể tải lịch sử khám lúc này.") from exc


@router.put("/appointments/{appointment_id}/accept")
def accept_patient(
    appointment_id: int,
    doctor_id: int | None = None,
    auth_info: tuple[User, Doctor] = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    _current_user, current_doctor = auth_info
    if doctor_id is not None and doctor_id != current_doctor.doctor_id:
        raise HTTPException(status_code=403, detail="Bác sĩ chỉ được nhận ca của chính mình.")
    _lock_appointment(db, appointment_id)
    appt = db.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()

    if not appt:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc hẹn")

    # Check ownership: doctor can only accept their own appointment
    if appt.doctor_id != current_doctor.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền tiếp nhận ca khám của bác sĩ khác.",
        )

    # State validation
    if appt.status != "CHECKED_IN":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Không thể tiếp nhận ca khám có trạng thái {appt.status}.",
        )
    if appt.appointment_date != clinic_today():
        raise HTTPException(409, "Chỉ được tiếp nhận lịch khám trong ngày hôm nay.")

    appt.status = "IN_PROGRESS"
    try:
        record_audit_event(
            db,
            actor_user_id=_current_user.user_id,
            actor_role="DOCTOR",
            action="APPOINTMENT_ACCEPTED",
            entity_type="Appointment",
            entity_id=appt.appointment_id,
            clinic_id=getattr(appt, "clinic_id", None),
            details={
                "old_status": "CHECKED_IN",
                "new_status": "IN_PROGRESS",
                "doctor_id": current_doctor.doctor_id,
            },
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(500, "Không thể tiếp nhận ca khám lúc này.") from exc
    return {"message": "Đã tiếp nhận bệnh nhân thành công"}


@router.post("/appointments/{appointment_id}/complete")
def complete_examination(
    appointment_id: int,
    payload: CompleteExamRequest,
    auth_info: tuple[User, Doctor] = Depends(require_doctor),
    db: Session = Depends(get_db),
):
    _current_user, current_doctor = auth_info
    _lock_appointment(db, appointment_id)
    appt = (
        db.query(Appointment)
        .filter(Appointment.appointment_id == appointment_id)
        .first()
    )
    if not appt:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc hẹn")

    # Check ownership
    if appt.doctor_id != current_doctor.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền hoàn tất ca khám của bác sĩ khác.",
        )

    # State validation
    if appt.status == "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cuộc hẹn này đã được hoàn tất trước đó.",
        )
    if appt.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Chỉ có thể hoàn tất ca đang khám IN_PROGRESS (hiện tại: {appt.status}).",
        )
    today = clinic_today()
    if appt.appointment_date > today:
        raise HTTPException(409, "Không thể hoàn tất ca khám có ngày hẹn ở tương lai.")
    if get_settings().app_mode == "production":
        if appt.appointment_date < today and not payload.late_entry_reason:
            raise HTTPException(422, "Ca khám từ ngày trước cần lý do nhập hồ sơ muộn.")
        if appt.appointment_date == today and payload.late_entry_reason:
            raise HTTPException(422, "Lý do nhập muộn chỉ dùng cho ca khám từ ngày trước.")
        if (
            appt.check_in_at is None
            or appt.clinical_context_loaded_at is None
            or appt.clinical_context_loaded_by_user_id != _current_user.user_id
            or appt.clinical_context_loaded_at < appt.check_in_at
        ):
            raise HTTPException(
                409,
                "Bác sĩ cần tải lịch sử khám cho chính ca này sau check-in trước khi hoàn tất.",
            )
        if payload.prescription_items:
            raise HTTPException(
                409,
                "Kê đơn qua hệ thống chưa được bật ở chế độ production; ca khám có thể hoàn tất không kèm thuốc.",
            )

    # Check if medical record already exists
    existing_record = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.appointment_id == appt.appointment_id)
        .first()
    )
    if existing_record:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hồ sơ bệnh án cho cuộc hẹn này đã tồn tại.",
        )

    try:
        # 1. Ghi nhận Medical Record
        record = MedicalRecord(
            appointment_id=appt.appointment_id,
            symptoms=payload.symptoms,
            diagnosis=payload.diagnosis,
            notes=payload.notes or "",
            late_entry_reason=payload.late_entry_reason,
            examination_date=clinic_naive_now(),
        )
        db.add(record)
        db.flush()

        # 2. Kê đơn thuốc
        if payload.prescription_items:
            pres = Prescription(
                medical_record_id=record.medical_record_id,
                created_at=clinic_naive_now(),
            )
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
        record_audit_event(
            db,
            actor_user_id=_current_user.user_id,
            actor_role="DOCTOR",
            action="MEDICAL_RECORD_CREATED",
            entity_type="MedicalRecord",
            entity_id=record.medical_record_id,
            clinic_id=getattr(appt, "clinic_id", None),
            details={
                "doctor_id": current_doctor.doctor_id,
                "late_entry": appt.appointment_date < today,
            },
        )
        if payload.prescription_items:
            record_audit_event(
                db,
                actor_user_id=_current_user.user_id,
                actor_role="DOCTOR",
                action="PRESCRIPTION_CREATED",
                entity_type="Prescription",
                entity_id=pres.prescription_id,
                clinic_id=getattr(appt, "clinic_id", None),
                details={"doctor_id": current_doctor.doctor_id},
            )
        record_audit_event(
            db,
            actor_user_id=_current_user.user_id,
            actor_role="DOCTOR",
            action="APPOINTMENT_COMPLETED",
            entity_type="Appointment",
            entity_id=appt.appointment_id,
            clinic_id=getattr(appt, "clinic_id", None),
            details={
                "old_status": "IN_PROGRESS",
                "new_status": "COMPLETED",
                "doctor_id": current_doctor.doctor_id,
            },
        )
        db.commit()
        return {"status": "success", "message": "Hoàn tất ca khám thành công!"}

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Hồ sơ khám hoặc đơn thuốc đã tồn tại.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(500, "Không thể lưu hồ sơ khám lúc này.") from exc


def _lock_appointment(db: Session, appointment_id: int) -> None:
    """Serialize clinical transitions for the same SQL Server appointment."""

    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "mssql":
        db.execute(
            text(
                "SELECT AppointmentID FROM Appointments WITH (UPDLOCK, HOLDLOCK) "
                "WHERE AppointmentID = :appointment_id"
            ),
            {"appointment_id": appointment_id},
        )
