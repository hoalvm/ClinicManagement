from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator
from sqlalchemy.orm import Session

from backend.app.core.audit import record_audit_event
from backend.app.core.config import get_settings
from backend.app.core.phone import normalize_phone
from backend.app.core.security import revoke_user_sessions
from backend.app.models import Clinic, Specialty, User
from backend.app.models.staff_clinic_assignment import StaffClinicAssignment

from .. import auth, schemas
from ..database import get_db
from ..deps import require_admin
from ._admin_guards import (
    commit_or_error,
    flush_or_error,
    lock_active_admins,
    lock_catalog,
    lock_doctors,
    lock_patient,
    require_no_open_appointments,
)

router = APIRouter(prefix="/users", tags=["Users"])


class StaffClinicAccess(BaseModel):
    """Complete set of clinics where a receptionist may process patient data."""

    model_config = ConfigDict(extra="forbid")
    clinic_ids: list[PositiveInt] = Field(max_length=100)

    @field_validator("clinic_ids")
    @classmethod
    def unique_clinics(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Clinic IDs must be unique")
        return value


@router.get("/{user_id}/clinics", response_model=StaffClinicAccess)
def get_staff_clinics(
    user_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)
):
    user = db.get(User, user_id)
    if user is None or user.role != "STAFF":
        raise HTTPException(404, "Không tìm thấy tài khoản nhân viên.")
    assignments = (
        db.query(StaffClinicAssignment)
        .filter(
            StaffClinicAssignment.user_id == user_id,
            StaffClinicAssignment.is_active.is_(True),
        )
        .all()
    )
    return StaffClinicAccess(clinic_ids=sorted(item.clinic_id for item in assignments))


@router.put("/{user_id}/clinics", response_model=StaffClinicAccess)
def replace_staff_clinics(
    user_id: int,
    body: StaffClinicAccess,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None or user.role != "STAFF" or not user.is_active:
        raise HTTPException(404, "Không tìm thấy tài khoản nhân viên đang hoạt động.")
    desired = set(body.clinic_ids)
    if desired:
        active = {
            row.clinic_id
            for row in db.query(Clinic)
            .filter(Clinic.clinic_id.in_(desired), Clinic.is_active.is_(True))
            .all()
        }
        if active != desired:
            raise HTTPException(422, "Cơ sở được phân quyền phải đang hoạt động.")
    existing = {
        item.clinic_id: item
        for item in db.query(StaffClinicAssignment)
        .filter(StaffClinicAssignment.user_id == user_id)
        .all()
    }
    for clinic_id, assignment in existing.items():
        assignment.is_active = clinic_id in desired
    for clinic_id in desired - existing.keys():
        db.add(StaffClinicAssignment(user_id=user_id, clinic_id=clinic_id, is_active=True))
    revoke_user_sessions(db, user_id)
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="STAFF_CLINICS_CHANGED",
        entity_type="User",
        entity_id=user_id,
        details={"clinic_count": len(desired)},
    )
    commit_or_error(db)
    return StaffClinicAccess(clinic_ids=sorted(desired))


@router.get("/", response_model=list[schemas.UserOut])
def get_users(db: Session = Depends(get_db), admin=Depends(require_admin)):
    users = db.query(User).all()
    return [
        {
            "UserID": u.user_id,
            "Username": u.username,
            "FullName": u.full_name,
            "Phone": u.phone,
            "Email": u.email,
            "Role": u.role,
            "IsActive": u.is_active,
            "CreatedAt": u.created_at,
        }
        for u in users
    ]


@router.post("/", response_model=schemas.UserOut)
def create_user(
    user: schemas.UserCreate, db: Session = Depends(get_db), admin=Depends(require_admin)
):
    if db.query(User).filter(User.username == user.Username).first():
        raise HTTPException(409, "Username đã tồn tại")

    if user.Role == "DOCTOR":
        raise HTTPException(
            422,
            "Vui lòng tạo tài khoản Bác sĩ tại mục 'Quản lý Bác sĩ' để thiết lập chuyên khoa và phòng khám.",
        )
    if get_settings().app_mode == "production" and user.Role == "PATIENT":
        raise HTTPException(
            422,
            "Chưa có quy trình cấp tài khoản bệnh nhân đã xác minh danh tính; "
            "tiếp đón tại quầy chỉ tạo hồ sơ khách vãng lai chưa đăng nhập.",
        )

    new_user = User(
        username=user.Username,
        password_hash=auth.hash_password(user.Password),
        full_name=user.FullName,
        phone=normalize_phone(user.Phone),
        email=user.Email,
        role=user.Role,
    )
    db.add(new_user)
    flush_or_error(db)

    if user.Role == "PATIENT":
        from backend.app.models import Patient

        patient = Patient(user_id=new_user.user_id)
        db.add(patient)

    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="USER_CREATED",
        entity_type="User",
        entity_id=new_user.user_id,
        details={"new_role": user.Role},
    )
    commit_or_error(db)
    db.refresh(new_user)
    return {
        "UserID": new_user.user_id,
        "Username": new_user.username,
        "FullName": new_user.full_name,
        "Phone": new_user.phone,
        "Email": new_user.email,
        "Role": new_user.role,
        "IsActive": new_user.is_active,
        "CreatedAt": new_user.created_at,
    }


@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    data: schemas.UserUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(404, "Không tìm thấy user")
    update_dict = data.model_dump(exclude_unset=True)
    old_role = user.role
    old_active = user.is_active
    new_role = update_dict.get("Role", user.role)
    new_active = update_dict.get("IsActive", user.is_active)
    if (
        get_settings().app_mode == "production"
        and user.role == "PATIENT"
        and not user.is_active
        and new_active
    ):
        raise HTTPException(
            409,
            "Không thể kích hoạt tài khoản bệnh nhân khi chưa có quy trình cấp thông tin đăng nhập đã xác minh.",
        )
    if get_settings().app_mode == "production" and new_role != user.role:
        raise HTTPException(
            409,
            "Không thể đổi role của tài khoản production; hãy khóa tài khoản cũ và cấp tài khoản đúng role.",
        )
    if user.doctor and ("Role" in update_dict or "IsActive" in update_dict):
        lock_catalog(db)
    if new_role == "PATIENT" and user.patient is None:
        raise HTTPException(409, "Tài khoản chưa có hồ sơ bệnh nhân.")
    if new_role == "DOCTOR" and (user.doctor is None or not user.doctor.is_active):
        raise HTTPException(409, "Tài khoản chưa có hồ sơ bác sĩ đang hoạt động.")
    if new_role == "DOCTOR" and new_active and ("Role" in update_dict or "IsActive" in update_dict):
        specialty = db.query(Specialty).filter(Specialty.specialty_id == user.doctor.specialty_id).first()
        clinic = db.query(Clinic).filter(Clinic.clinic_id == user.doctor.clinic_id).first()
        if not specialty or not getattr(specialty, "is_active", True):
            raise HTTPException(422, "Chuyên khoa của bác sĩ không hoạt động.")
        if not clinic or not getattr(clinic, "is_active", True):
            raise HTTPException(422, "Cơ sở của bác sĩ không hoạt động.")
    if user.role == "DOCTOR" and user.doctor and (new_role != "DOCTOR" or not new_active):
        lock_doctors(db, doctor_id=user.doctor.doctor_id)
        require_no_open_appointments(db, doctor_id=user.doctor.doctor_id)
    if user.role == "PATIENT" and user.patient and (new_role != "PATIENT" or not new_active):
        lock_patient(db, user.patient.patient_id)
        require_no_open_appointments(db, patient_id=user.patient.patient_id)
    if user.role == "ADMIN" and (new_role != "ADMIN" or not new_active):
        lock_active_admins(db)
        active_admin_count = db.query(User).filter(User.role == "ADMIN", User.is_active).count()
        if isinstance(active_admin_count, int) and active_admin_count <= 1:
            raise HTTPException(409, "Không thể gỡ quyền quản trị viên cuối cùng.")
    if "Username" in update_dict and update_dict["Username"] != user.username:
        duplicate = db.query(User).filter(User.username == update_dict["Username"]).first()
        if duplicate is not None:
            raise HTTPException(409, "Username đã tồn tại.")
    if "IsActive" in update_dict and not update_dict["IsActive"]:
        admin_id = getattr(admin, "user_id", None)
        admin_name = getattr(admin, "username", None)
        if user.username == "admin" or user.user_id == admin_id or (admin_name and user.username == admin_name):
            raise HTTPException(400, "Không thể khóa tài khoản quản trị viên hiện tại hoặc tài khoản admin hệ thống")
    mapping = {
        "Username": "username",
        "FullName": "full_name",
        "Phone": "phone",
        "Email": "email",
        "Role": "role",
        "IsActive": "is_active",
    }
    for field, value in update_dict.items():
        if field == "Phone":
            value = normalize_phone(value)
        setattr(user, mapping.get(field, field), value)
        if field == "IsActive" and user.doctor:
            user.doctor.is_active = bool(value)
    if user.role != old_role or user.is_active != old_active or "Username" in update_dict:
        revoke_user_sessions(db, user.user_id)
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="USER_UPDATED",
        entity_type="User",
        entity_id=user.user_id,
        details={
            "old_role": old_role,
            "new_role": user.role,
            "old_status": "ACTIVE" if old_active else "INACTIVE",
            "new_status": "ACTIVE" if user.is_active else "INACTIVE",
        },
    )
    commit_or_error(db)
    db.refresh(user)
    return {
        "UserID": user.user_id,
        "Username": user.username,
        "FullName": user.full_name,
        "Phone": user.phone,
        "Email": user.email,
        "Role": user.role,
        "IsActive": user.is_active,
        "CreatedAt": user.created_at,
    }


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(404, "Không tìm thấy user")
    admin_id = getattr(admin, "user_id", None)
    admin_name = getattr(admin, "username", None)
    if user.username == "admin" or user.user_id == admin_id or (admin_name and user.username == admin_name):
        raise HTTPException(400, "Không thể khóa tài khoản quản trị viên hiện tại hoặc tài khoản admin hệ thống")
    if user.role == "ADMIN":
        lock_active_admins(db)
        active_admin_count = db.query(User).filter(User.role == "ADMIN", User.is_active).count()
        if isinstance(active_admin_count, int) and active_admin_count <= 1:
            raise HTTPException(409, "Không thể khóa quản trị viên cuối cùng.")
    if user.role == "DOCTOR" and user.doctor:
        lock_catalog(db)
        lock_doctors(db, doctor_id=user.doctor.doctor_id)
        require_no_open_appointments(db, doctor_id=user.doctor.doctor_id)
    if user.role == "PATIENT" and user.patient:
        lock_patient(db, user.patient.patient_id)
        require_no_open_appointments(db, patient_id=user.patient.patient_id)
    user.is_active = False
    if user.doctor:
        user.doctor.is_active = False
    revoke_user_sessions(db, user.user_id)
    record_audit_event(
        db,
        actor_user_id=getattr(admin, "user_id", None),
        actor_role="ADMIN",
        action="USER_DEACTIVATED",
        entity_type="User",
        entity_id=user.user_id,
        details={"old_status": "ACTIVE", "new_status": "INACTIVE"},
    )
    commit_or_error(db)
    return {"message": "Đã vô hiệu hóa tài khoản"}
