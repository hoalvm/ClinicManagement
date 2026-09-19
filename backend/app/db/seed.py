"""Idempotent demonstration data for the existing SQL Server schema.

Run with::

    python -m backend.app.db.seed

This module never creates, drops, or alters database objects.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.clock import clinic_today
from backend.app.core.security import hash_password, verify_password
from backend.app.db.session import SessionLocal
from backend.app.models import (
    Appointment,
    Clinic,
    Doctor,
    DoctorSchedule,
    Invoice,
    InvoiceItem,
    MedicalRecord,
    Patient,
    Payment,
    Prescription,
    PrescriptionItem,
    Specialty,
    User,
)

DEMO_PASSWORD = "Password123!"
DOCTOR_PASSWORD = "Doctor123!"


def _first(session: Session, statement):
    return session.execute(statement).scalars().first()


def _ensure_specialty(session: Session, name: str, description: str) -> Specialty:
    specialty = _first(session, select(Specialty).where(Specialty.specialty_name == name))
    if specialty is None:
        specialty = Specialty(specialty_name=name)
        session.add(specialty)
    specialty.description = description
    specialty.is_active = True
    session.flush()
    return specialty


def _ensure_clinic(session: Session, name: str, address: str, phone: str) -> Clinic:
    clinic = _first(session, select(Clinic).where(Clinic.clinic_name == name))
    if clinic is None:
        clinic = Clinic(clinic_name=name)
        session.add(clinic)
    clinic.address = address
    clinic.phone = phone
    clinic.is_active = True
    session.flush()
    return clinic


def _ensure_user(
    session: Session,
    *,
    username: str,
    password: str,
    full_name: str,
    phone: str,
    email: str,
    role: str,
) -> User:
    user = _first(session, select(User).where(User.username == username))
    if user is None:
        user = User(username=username, password_hash=hash_password(password))
        session.add(user)
    elif not verify_password(password, user.password_hash):
        user.password_hash = hash_password(password)
    user.full_name = full_name
    user.phone = phone
    user.email = email
    user.role = role
    user.is_active = True
    session.flush()
    return user


def _ensure_doctor(
    session: Session,
    *,
    user: User,
    specialty: Specialty,
    clinic: Clinic,
    license_number: str,
) -> Doctor:
    doctor = _first(session, select(Doctor).where(Doctor.user_id == user.user_id))
    if doctor is None:
        doctor = Doctor(user_id=user.user_id, specialty_id=specialty.specialty_id)
        session.add(doctor)
    doctor.specialty_id = specialty.specialty_id
    doctor.clinic_id = clinic.clinic_id
    doctor.license_number = license_number
    doctor.is_active = True
    session.flush()
    return doctor


def _ensure_patient(
    session: Session,
    *,
    user: User,
    date_of_birth: date,
    gender: str,
    address: str,
) -> Patient:
    patient = _first(session, select(Patient).where(Patient.user_id == user.user_id))
    if patient is None:
        patient = Patient(user_id=user.user_id)
        session.add(patient)
    patient.date_of_birth = date_of_birth
    patient.gender = gender
    patient.address = address
    session.flush()
    return patient


def _ensure_schedule(
    session: Session,
    doctor: Doctor,
    *,
    day_of_week: int,
    start_time: time,
    end_time: time,
) -> DoctorSchedule:
    schedule = _first(
        session,
        select(DoctorSchedule).where(
            DoctorSchedule.doctor_id == doctor.doctor_id,
            DoctorSchedule.day_of_week == day_of_week,
            DoctorSchedule.start_time == start_time,
            DoctorSchedule.end_time == end_time,
        ),
    )
    if schedule is None:
        schedule = DoctorSchedule(
            doctor_id=doctor.doctor_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
        )
        session.add(schedule)
    schedule.slot_duration = 30
    schedule.is_active = True
    session.flush()
    return schedule


def _ensure_appointment(
    session: Session,
    *,
    patient: Patient,
    doctor: Doctor,
    clinic: Clinic,
    appointment_date: date,
    start_time: time,
    end_time: time,
    reason: str,
    status: str,
) -> Appointment:
    appointment = _first(
        session,
        select(Appointment).where(
            Appointment.patient_id == patient.patient_id,
            Appointment.doctor_id == doctor.doctor_id,
            Appointment.clinic_id == clinic.clinic_id,
            Appointment.start_time == start_time,
            Appointment.reason == reason,
        ),
    )
    if appointment is None:
        appointment = Appointment(patient_id=patient.patient_id, reason=reason)
        session.add(appointment)
    appointment.doctor_id = doctor.doctor_id
    appointment.clinic_id = clinic.clinic_id
    appointment.appointment_date = appointment_date
    appointment.start_time = start_time
    appointment.end_time = end_time
    appointment.status = status
    scheduled_for = datetime.combine(appointment_date, start_time)
    appointment.created_at = min(
        scheduled_for - timedelta(days=7),
        datetime.combine(clinic_today(), time(7, 0)),
    )
    session.flush()
    return appointment


def _ensure_medical_record(
    session: Session,
    appointment: Appointment,
    *,
    symptoms: str,
    diagnosis: str,
    notes: str,
) -> MedicalRecord:
    record = _first(
        session,
        select(MedicalRecord).where(MedicalRecord.appointment_id == appointment.appointment_id),
    )
    if record is None:
        record = MedicalRecord(appointment_id=appointment.appointment_id)
        session.add(record)
    record.symptoms = symptoms
    record.diagnosis = diagnosis
    record.notes = notes
    record.examination_date = datetime.combine(appointment.appointment_date, appointment.end_time)
    session.flush()
    return record


def _ensure_prescription(
    session: Session,
    record: MedicalRecord,
    items: list[dict[str, Any]],
) -> Prescription:
    prescription = _first(
        session,
        select(Prescription).where(Prescription.medical_record_id == record.medical_record_id),
    )
    if prescription is None:
        prescription = Prescription(medical_record_id=record.medical_record_id)
        session.add(prescription)
        session.flush()
    prescription.created_at = record.examination_date + timedelta(minutes=5)

    for data in items:
        item = _first(
            session,
            select(PrescriptionItem).where(
                PrescriptionItem.prescription_id == prescription.prescription_id,
                PrescriptionItem.medicine_name == data["medicine_name"],
            ),
        )
        if item is None:
            item = PrescriptionItem(
                prescription_id=prescription.prescription_id,
                medicine_name=data["medicine_name"],
            )
            session.add(item)
        item.quantity = data["quantity"]
        item.dosage = data["dosage"]
        item.instructions = data["instructions"]
    session.flush()
    return prescription


def _ensure_invoice(
    session: Session,
    appointment: Appointment,
    *,
    status: str,
    items: list[tuple[str, int, Decimal]],
    payment_method: str | None = None,
) -> Invoice:
    invoice = _first(
        session,
        select(Invoice).where(Invoice.appointment_id == appointment.appointment_id),
    )
    if invoice is None:
        invoice = Invoice(appointment_id=appointment.appointment_id)
        session.add(invoice)
        session.flush()

    for item_name, quantity, unit_price in items:
        item = _first(
            session,
            select(InvoiceItem).where(
                InvoiceItem.invoice_id == invoice.invoice_id,
                InvoiceItem.item_name == item_name,
            ),
        )
        if item is None:
            item = InvoiceItem(invoice_id=invoice.invoice_id, item_name=item_name)
            session.add(item)
        item.quantity = quantity
        item.unit_price = unit_price
    session.flush()

    all_items = session.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.invoice_id)
    ).scalars()
    invoice.total_amount = sum(
        (item.unit_price * item.quantity for item in all_items), start=Decimal("0.00")
    )
    invoice.status = status
    completed_at = datetime.combine(appointment.appointment_date, appointment.end_time)
    invoice.created_at = completed_at + timedelta(minutes=10)
    session.flush()

    if status == "PAID" and payment_method is not None:
        payment = _first(session, select(Payment).where(Payment.invoice_id == invoice.invoice_id))
        if payment is None:
            payment = Payment(invoice_id=invoice.invoice_id)
            session.add(payment)
        payment.amount = invoice.total_amount
        payment.payment_method = payment_method
        payment.payment_date = completed_at + timedelta(minutes=15)
    session.flush()
    return invoice


def seed_database(session: Session) -> None:
    """Insert or update the deterministic demo dataset in one transaction."""

    internal = _ensure_specialty(
        session, "Internal Medicine", "General adult medicine and follow-up care"
    )
    dermatology = _ensure_specialty(
        session, "Dermatology", "Diagnosis and treatment of skin conditions"
    )
    cardiology = _ensure_specialty(session, "Cardiology", "Heart and cardiovascular care")

    central = _ensure_clinic(
        session,
        "Central Clinic",
        "123 Nguyen Hue, District 1, Ho Chi Minh City",
        "02838220001",
    )
    riverside = _ensure_clinic(
        session,
        "Riverside Clinic",
        "45 Bach Dang, Binh Thanh, Ho Chi Minh City",
        "02838220002",
    )

    doctor_specs = (
        (
            "doctor01",
            "Dr. Nguyen Minh Anh",
            "0901000001",
            "doctor01@example.com",
            internal,
            central,
            "LIC-001",
        ),
        (
            "doctor02",
            "Dr. Tran Thu Ha",
            "0901000002",
            "doctor02@example.com",
            dermatology,
            riverside,
            "LIC-002",
        ),
        (
            "doctor03",
            "Dr. Le Quang Huy",
            "0901000003",
            "doctor03@example.com",
            cardiology,
            central,
            "LIC-003",
        ),
    )
    doctors: list[Doctor] = []
    for username, name, phone, email, specialty, clinic, license_number in doctor_specs:
        user = _ensure_user(
            session,
            username=username,
            password=DOCTOR_PASSWORD,
            full_name=name,
            phone=phone,
            email=email,
            role="DOCTOR",
        )
        doctors.append(
            _ensure_doctor(
                session,
                user=user,
                specialty=specialty,
                clinic=clinic,
                license_number=license_number,
            )
        )

    for doctor in doctors:
        _ensure_schedule(
            session,
            doctor,
            day_of_week=2,
            start_time=time(8, 0),
            end_time=time(12, 0),
        )
        _ensure_schedule(
            session,
            doctor,
            day_of_week=4,
            start_time=time(13, 0),
            end_time=time(17, 0),
        )

    patient_users = (
        _ensure_user(
            session,
            username="patient01",
            password=DEMO_PASSWORD,
            full_name="Nguyen Van An",
            phone="0900000001",
            email="patient01@example.com",
            role="PATIENT",
        ),
        _ensure_user(
            session,
            username="patient02",
            password=DEMO_PASSWORD,
            full_name="Tran Thi Binh",
            phone="0900000002",
            email="patient02@example.com",
            role="PATIENT",
        ),
    )
    patients = (
        _ensure_patient(
            session,
            user=patient_users[0],
            date_of_birth=date(1995, 5, 12),
            gender="MALE",
            address="District 3, Ho Chi Minh City",
        ),
        _ensure_patient(
            session,
            user=patient_users[1],
            date_of_birth=date(1998, 11, 8),
            gender="FEMALE",
            address="Thu Duc City, Ho Chi Minh City",
        ),
    )

    today = clinic_today()
    appointment_specs = (
        (patients[0], doctors[0], central, -90, time(8, 0), "Annual health check", "COMPLETED"),
        (
            patients[0],
            doctors[1],
            riverside,
            -60,
            time(9, 0),
            "Skin allergy consultation",
            "COMPLETED",
        ),
        (
            patients[0],
            doctors[2],
            central,
            -30,
            time(10, 0),
            "Cardiovascular screening",
            "COMPLETED",
        ),
        (
            patients[0],
            doctors[0],
            central,
            -7,
            time(14, 0),
            "Post-treatment follow-up",
            "COMPLETED",
        ),
        (patients[0], doctors[0], central, 3, time(9, 0), "Follow-up examination", "CONFIRMED"),
        (
            patients[0],
            doctors[1],
            riverside,
            10,
            time(10, 30),
            "Recurring skin irritation",
            "PENDING",
        ),
        (
            patients[0],
            doctors[2],
            central,
            -2,
            time(15, 0),
            "Cancelled heart consultation",
            "CANCELLED",
        ),
        (patients[1], doctors[0], central, -45, time(8, 30), "Persistent cough", "COMPLETED"),
        (
            patients[1],
            doctors[2],
            central,
            0,
            time(11, 0),
            "Chest discomfort assessment",
            "CHECKED_IN",
        ),
    )
    appointments: list[Appointment] = []
    for patient, doctor, clinic, day_delta, starts_at, reason, status in appointment_specs:
        end_datetime = datetime.combine(today, starts_at) + timedelta(minutes=30)
        appointments.append(
            _ensure_appointment(
                session,
                patient=patient,
                doctor=doctor,
                clinic=clinic,
                appointment_date=today + timedelta(days=day_delta),
                start_time=starts_at,
                end_time=end_datetime.time(),
                reason=reason,
                status=status,
            )
        )

    medical_specs = (
        (
            appointments[0],
            "Fatigue",
            "Routine examination - stable health",
            "Continue healthy lifestyle",
        ),
        (appointments[1], "Itchy red patches", "Contact dermatitis", "Avoid suspected allergens"),
        (
            appointments[2],
            "Occasional palpitations",
            "Mild hypertension",
            "Monitor blood pressure daily",
        ),
        (
            appointments[3],
            "Improved symptoms",
            "Resolved acute pharyngitis",
            "Complete medication course",
        ),
        (
            appointments[7],
            "Dry cough and sore throat",
            "Acute pharyngitis",
            "Rest and drink warm fluids",
        ),
    )
    records = [
        _ensure_medical_record(
            session,
            appointment,
            symptoms=symptoms,
            diagnosis=diagnosis,
            notes=notes,
        )
        for appointment, symptoms, diagnosis, notes in medical_specs
    ]

    _ensure_prescription(
        session,
        records[1],
        [
            {
                "medicine_name": "Cetirizine",
                "quantity": 10,
                "dosage": "10 mg",
                "instructions": "Take once daily in the evening",
            },
            {
                "medicine_name": "Hydrocortisone cream",
                "quantity": 1,
                "dosage": "1%",
                "instructions": "Apply a thin layer twice daily",
            },
        ],
    )
    _ensure_prescription(
        session,
        records[2],
        [
            {
                "medicine_name": "Amlodipine",
                "quantity": 30,
                "dosage": "5 mg",
                "instructions": "Take once daily after breakfast",
            }
        ],
    )
    _ensure_prescription(
        session,
        records[3],
        [
            {
                "medicine_name": "Paracetamol",
                "quantity": 10,
                "dosage": "500 mg",
                "instructions": "Take twice daily after meals if needed",
            }
        ],
    )
    _ensure_prescription(
        session,
        records[4],
        [
            {
                "medicine_name": "Paracetamol",
                "quantity": 10,
                "dosage": "500 mg",
                "instructions": "Take twice daily after meals",
            },
            {
                "medicine_name": "Lozenges",
                "quantity": 12,
                "dosage": "1 lozenge",
                "instructions": "Dissolve slowly every 4 to 6 hours",
            },
        ],
    )

    _ensure_invoice(
        session,
        appointments[0],
        status="PAID",
        items=[("General consultation", 1, Decimal("200000.00"))],
        payment_method="CARD",
    )
    _ensure_invoice(
        session,
        appointments[1],
        status="PAID",
        items=[
            ("Dermatology consultation", 1, Decimal("250000.00")),
            ("Skin test", 1, Decimal("150000.00")),
        ],
        payment_method="CASH",
    )
    _ensure_invoice(
        session,
        appointments[2],
        status="PAID",
        items=[
            ("Cardiology consultation", 1, Decimal("300000.00")),
            ("ECG", 1, Decimal("200000.00")),
        ],
        payment_method="CARD",
    )
    _ensure_invoice(
        session,
        appointments[3],
        status="UNPAID",
        items=[("Follow-up consultation", 1, Decimal("150000.00"))],
    )
    _ensure_invoice(
        session,
        appointments[7],
        status="PAID",
        items=[
            ("General consultation", 1, Decimal("200000.00")),
            ("Throat test", 1, Decimal("100000.00")),
        ],
        payment_method="CASH",
    )

    session.commit()


def main() -> None:
    try:
        with SessionLocal() as session:
            seed_database(session)
    except SQLAlchemyError:
        raise SystemExit(
            "Seed failed. Verify SQL Server, ClinicManagementDB, credentials, and ODBC Driver 18."
        ) from None
    print("Seed completed successfully.")


if __name__ == "__main__":
    main()
