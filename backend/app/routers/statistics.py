from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/statistics", tags=["Statistics"])

@router.get("/overview")
def overview(db: Session = Depends(get_db), admin=Depends(require_admin)):
    total_users = db.query(func.count(models.User.UserID)).scalar()
    total_doctors = db.query(func.count(models.Doctor.DoctorID)).filter(models.Doctor.IsActive == True).scalar()
    total_clinics = db.query(func.count(models.Clinic.ClinicID)).filter(models.Clinic.IsActive == True).scalar()
    total_specialties = db.query(func.count(models.Specialty.SpecialtyID)).filter(models.Specialty.IsActive == True).scalar()
    total_schedules = db.query(func.count(models.DoctorSchedule.ScheduleID)).filter(models.DoctorSchedule.IsActive == True).scalar()

    doctors_by_specialty = (
        db.query(models.Specialty.SpecialtyName, func.count(models.Doctor.DoctorID))
        .join(models.Doctor, models.Doctor.SpecialtyID == models.Specialty.SpecialtyID)
        .filter(models.Doctor.IsActive == True)
        .group_by(models.Specialty.SpecialtyName)
        .all()
    )

    doctors_by_clinic = (
        db.query(models.Clinic.ClinicName, func.count(models.Doctor.DoctorID))
        .join(models.Doctor, models.Doctor.ClinicID == models.Clinic.ClinicID)
        .filter(models.Doctor.IsActive == True)
        .group_by(models.Clinic.ClinicName)
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