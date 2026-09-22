import enum
from datetime import datetime, date, time
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    Enum, Boolean, Date, Time
)
from sqlalchemy.orm import relationship
from backend.database import Base

class AppointmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

# Bảng Users (Bảng cha chứa thông tin đăng nhập và họ tên)
class User(Base):
    __tablename__ = "Users"

    UserID = Column(Integer, primary_key=True, index=True)
    Username = Column(String(50), unique=True, nullable=False, index=True)
    PasswordHash = Column(String(255), nullable=False)
    FullName = Column(String(100), nullable=False)
    Phone = Column(String(15), nullable=True)
    Email = Column(String(100), nullable=True)
    Role = Column(String(20), nullable=False)  # 'DOCTOR', 'PATIENT', 'STAFF', 'ADMIN'
    IsActive = Column(Boolean, default=True, nullable=False)
    CreatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)

    doctor = relationship("Doctor", back_populates="user", uselist=False)
    patient = relationship("Patient", back_populates="user", uselist=False)

# Bảng Patients
class Patient(Base):
    __tablename__ = "Patients"

    PatientID = Column(Integer, primary_key=True, index=True)
    UserID = Column(Integer, ForeignKey("Users.UserID"), unique=True, nullable=False)
    DateOfBirth = Column(Date, nullable=True)
    Gender = Column(String(10), nullable=True)
    Address = Column(String(255), nullable=True)

    user = relationship("User", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")

# Bảng Doctors
class Doctor(Base):
    __tablename__ = "Doctors"

    DoctorID = Column(Integer, primary_key=True, index=True)
    UserID = Column(Integer, ForeignKey("Users.UserID"), unique=True, nullable=False)
    SpecialtyID = Column(Integer, nullable=False)
    ClinicID = Column(Integer, nullable=True)
    LicenseNumber = Column(String(50), unique=True, nullable=True)
    IsActive = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")

# Bảng Appointments
class Appointment(Base):
    __tablename__ = "Appointments"

    AppointmentID = Column(Integer, primary_key=True, index=True)
    PatientID = Column(Integer, ForeignKey("Patients.PatientID"), nullable=False)
    DoctorID = Column(Integer, ForeignKey("Doctors.DoctorID"), nullable=False)
    ClinicID = Column(Integer, nullable=True)
    AppointmentDate = Column(Date, nullable=False, default=date.today)
    StartTime = Column(Time, nullable=False)
    EndTime = Column(Time, nullable=False)
    Reason = Column(String(500), nullable=True)
    Status = Column(Enum(AppointmentStatus), default=AppointmentStatus.CHECKED_IN, nullable=False)
    CreatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    medical_record = relationship("MedicalRecord", back_populates="appointment", uselist=False)

# Bảng MedicalRecords
class MedicalRecord(Base):
    __tablename__ = "MedicalRecords"

    MedicalRecordID = Column(Integer, primary_key=True, index=True)
    AppointmentID = Column(Integer, ForeignKey("Appointments.AppointmentID"), unique=True, nullable=False)
    Symptoms = Column(String(1000), nullable=True)
    Diagnosis = Column(String(1000), nullable=True)
    Notes = Column(String(2000), nullable=True)
    ExaminationDate = Column(DateTime, default=datetime.utcnow, nullable=False)

    appointment = relationship("Appointment", back_populates="medical_record")
    prescription = relationship("Prescription", back_populates="medical_record", uselist=False)

# Bảng Prescriptions
class Prescription(Base):
    __tablename__ = "Prescriptions"

    PrescriptionID = Column(Integer, primary_key=True, index=True)
    MedicalRecordID = Column(Integer, ForeignKey("MedicalRecords.MedicalRecordID"), unique=True, nullable=False)
    CreatedAt = Column(DateTime, default=datetime.utcnow, nullable=False)

    medical_record = relationship("MedicalRecord", back_populates="prescription")
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")

# Bảng PrescriptionItems
class PrescriptionItem(Base):
    __tablename__ = "PrescriptionItems"

    PrescriptionItemID = Column(Integer, primary_key=True, index=True)
    PrescriptionID = Column(Integer, ForeignKey("Prescriptions.PrescriptionID"), nullable=False)
    MedicineName = Column(String(150), nullable=False)
    Quantity = Column(Integer, nullable=False)
    Dosage = Column(String(255), nullable=True)
    Instructions = Column(String(500), nullable=True)

    prescription = relationship("Prescription", back_populates="items")