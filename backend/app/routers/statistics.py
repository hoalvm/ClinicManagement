from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models import Clinic, Doctor, DoctorSchedule, Specialty, User

from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/statistics", tags=["Statistics"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), admin=Depends(require_admin)):
    total_users = db.query(func.count(User.user_id)).scalar() or 0
    total_doctors = (
        db.query(func.count(Doctor.doctor_id)).filter(Doctor.is_active).scalar() or 0
    )
    total_clinics = (
        db.query(func.count(Clinic.clinic_id)).filter(Clinic.is_active).scalar() or 0
    )
    total_specialties = (
        db.query(func.count(Specialty.specialty_id))
        .filter(Specialty.is_active)
        .scalar() or 0
    )
    total_schedules = (
        db.query(func.count(DoctorSchedule.schedule_id))
        .filter(DoctorSchedule.is_active)
        .scalar() or 0
    )

    doctors_by_specialty = (
        db.query(Specialty.specialty_name, func.count(Doctor.doctor_id))
        .join(Doctor, Doctor.specialty_id == Specialty.specialty_id)
        .filter(Doctor.is_active)
        .group_by(Specialty.specialty_name)
        .all()
    )

    doctors_by_clinic = (
        db.query(Clinic.clinic_name, func.count(Doctor.doctor_id))
        .join(Doctor, Doctor.clinic_id == Clinic.clinic_id)
        .filter(Doctor.is_active)
        .group_by(Clinic.clinic_name)
        .all()
    )

    return {
        "total_users": total_users,
        "total_doctors": total_doctors,
        "total_clinics": total_clinics,
        "total_specialties": total_specialties,
        "total_schedules": total_schedules,
        "doctors_by_specialty": [{"name": name, "count": count} for name, count in doctors_by_specialty],
        "doctors_by_clinic": [{"name": name, "count": count} for name, count in doctors_by_clinic],
    }
