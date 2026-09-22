from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "Users"
    UserID = Column(Integer, primary_key=True, index=True)
    Username = Column(String(50), unique=True, nullable=False)
    PasswordHash = Column(String(255), nullable=False)
    FullName = Column(String(100), nullable=False)
    Phone = Column(String(15))
    Email = Column(String(100))
    Role = Column(String(20), nullable=False)
    IsActive = Column(Boolean, default=True)
    CreatedAt = Column(DateTime, server_default=func.now())

class Specialty(Base):
    __tablename__ = "Specialties"
    SpecialtyID = Column(Integer, primary_key=True, index=True)
    SpecialtyName = Column(String(100), unique=True, nullable=False)
    Description = Column(String(255))
    IsActive = Column(Boolean, default=True)

class Clinic(Base):
    __tablename__ = "Clinics"
    ClinicID = Column(Integer, primary_key=True, index=True)
    ClinicName = Column(String(150), nullable=False)
    Address = Column(String(255))
    Phone = Column(String(15))
    IsActive = Column(Boolean, default=True)

class Doctor(Base):
    __tablename__ = "Doctors"
    DoctorID = Column(Integer, primary_key=True, index=True)
    UserID = Column(Integer, ForeignKey("Users.UserID"), unique=True, nullable=False)
    SpecialtyID = Column(Integer, ForeignKey("Specialties.SpecialtyID"), nullable=False)
    ClinicID = Column(Integer, ForeignKey("Clinics.ClinicID"))
    LicenseNumber = Column(String(50), unique=True)
    IsActive = Column(Boolean, default=True)

    user = relationship("User")
    specialty = relationship("Specialty")
    clinic = relationship("Clinic")

class DoctorSchedule(Base):
    __tablename__ = "DoctorSchedules"
    ScheduleID = Column(Integer, primary_key=True, index=True)
    DoctorID = Column(Integer, ForeignKey("Doctors.DoctorID"), nullable=False)
    DayOfWeek = Column(Integer, nullable=False)
    StartTime = Column(Time, nullable=False)
    EndTime = Column(Time, nullable=False)
    SlotDuration = Column(Integer, default=30)
    IsActive = Column(Boolean, default=True)