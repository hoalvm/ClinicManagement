"""One-time synthetic fixture for the persistent academic project database.

The fixture is deliberately marked as training data. It is never permitted in
real production mode. Rerunning it leaves all later clinical and payment data
untouched, including when the demo clock has moved to another day.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.clock import clinic_now
from backend.app.core.config import get_settings
from backend.app.core.security import hash_password
from backend.app.db.session import SessionLocal
from backend.app.models import (
    Appointment,
    ChargeCatalog,
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
    StaffClinicAssignment,
    User,
)

PROJECT_DB_NAME = "ClinicManagementDB"
SEED_VERSION = "project-synthetic-seed-v2"
ADMIN_PASSWORD = "Admin123!"
DOCTOR_PASSWORD = "Doctor123!"
DEMO_PASSWORD = "Password123!"
STAFF_PASSWORD = "Staff123!"

# Names are the five group members. All specialty assignments, contact details,
# license identifiers and clinical cases below are fictional demonstration data.
DEMO_DOCTORS = (
    ("doctor01", "Lý Võ Mỹ Hoa", "Nội tổng quát", "Quận 1"),
    ("doctor02", "Nguyễn Thị Hoa", "Da liễu", "Tân Bình"),
    ("doctor03", "Phạm Quốc Duy", "Tim mạch", "Quận 1"),
    ("doctor04", "Nguyễn Hồ Phát", "Tai Mũi Họng", "Bình Thạnh"),
    ("doctor05", "Đỗ Minh Truyền", "Cơ Xương Khớp", "Tân Bình"),
)

DEMO_PATIENTS = (
    ("patient01", "Trần Minh Anh", date(1995, 4, 12), "FEMALE", "0900000201"),
    ("patient02", "Nguyễn Văn Bình", date(1986, 7, 21), "MALE", "0900000202"),
    ("patient03", "Lê Thu Hà", date(1991, 11, 3), "FEMALE", "0900000203"),
    ("patient04", "Phạm Quốc Khánh", date(1967, 2, 16), "MALE", "0900000204"),
    ("patient05", "Võ Ngọc Mai", date(2001, 8, 9), "FEMALE", "0900000205"),
    ("patient06", "Đặng Hoàng Long", date(1978, 6, 30), "MALE", "0900000206"),
    ("patient07", "Bùi Thanh Thảo", date(1993, 12, 14), "FEMALE", "0900000207"),
    ("patient08", "Huỳnh Gia Bảo", date(2004, 3, 25), "MALE", "0900000208"),
)

def _shift_workdays(start: date, count: int) -> date:
    """Move by a number of Monday-Friday business days."""
    if count == 0:
        return start
    day = start
    step = 1 if count > 0 else -1
    for _ in range(abs(count)):
        day += timedelta(days=step)
        while day.isoweekday() > 5:
            day += timedelta(days=step)
    return day


def _last_workday(day: date) -> date:
    while day.isoweekday() > 5:
        day -= timedelta(days=1)
    return day


def _next_workday(day: date) -> date:
    while day.isoweekday() > 5:
        day += timedelta(days=1)
    return day


def demo_live_slot(now: datetime | None = None) -> tuple[date, time]:
    """First unoccupied 30-minute weekday slot strictly after the clinic clock."""
    current = now or clinic_now()
    day = _next_workday(current.date())
    while True:
        for hour in (*range(8, 12), *range(13, 17)):
            for minute in (0, 30):
                candidate = datetime.combine(day, time(hour, minute), tzinfo=current.tzinfo)
                if candidate > current:
                    return day, candidate.time().replace(tzinfo=None)
        day = _shift_workdays(day, 1)


def build_demo_appointments(
    now: datetime | None = None,
) -> tuple[tuple[str, str, str, date, time, str, str], ...]:
    """Make the twelve-case story relative to the current clinic business date.

    In off-hours the live booking moves to the next available workday. Existing
    CHECKED_IN/IN_PROGRESS samples remain on the last elapsed workday, never on
    a future date. The fixed demonstration clock restores the single-case
    same-day walkthrough without changing these rules.
    """
    current = now or clinic_now()
    live_day, live_start = demo_live_slot(current)
    current_day = _last_workday(current.date())
    # A check-in at 09:20 may only exist once that time has passed.
    if current_day == current.date() and current.time() < time(9, 30):
        current_day = _shift_workdays(current_day, -1)
    previous = tuple(_shift_workdays(current_day, -offset) for offset in range(5, 0, -1))
    # Keep today's pending/confirmed cases for the 09:59 runbook, but do not
    # create a pending appointment already in the past on an evening init.
    upcoming_day = (
        current_day
        if current_day == current.date() and current.time() < time(11) and live_start != time(11)
        else _shift_workdays(live_day, 1)
    )
    future_day = _shift_workdays(live_day, 1)
    second_future_day = _shift_workdays(live_day, 2)
    return (
        ("A01", "patient01", "doctor01", previous[0], time(9), "COMPLETED", "Đầy bụng sau ăn, khó tiêu"),
        ("A02", "patient02", "doctor02", previous[1], time(9), "COMPLETED", "Ngứa và đỏ da bàn tay sau tiếp xúc chất tẩy"),
        ("A03", "patient01", "doctor03", previous[2], time(9), "COMPLETED", "Tái khám theo dõi huyết áp"),
        ("A04", "patient03", "doctor04", previous[3], time(9), "COMPLETED", "Nghẹt mũi và hắt hơi buổi sáng"),
        ("A05", "patient04", "doctor05", previous[4], time(9), "COMPLETED", "Đau khớp gối khi đi lại"),
        ("A06", "patient05", "doctor01", upcoming_day, time(11), "PENDING", "Đau đầu nhẹ hai ngày"),
        ("A07", "patient06", "doctor02", upcoming_day, time(11), "CONFIRMED", "Mẩn đỏ vùng cẳng tay"),
        ("A08", "patient07", "doctor03", current_day, time(9, 30), "CHECKED_IN", "Hồi hộp từng cơn"),
        ("A09", "patient08", "doctor04", current_day, time(9, 30), "IN_PROGRESS", "Đau tai phải"),
        ("A10", "patient01", "doctor02", future_day, time(10), "CONFIRMED", "Tư vấn da liễu"),
        ("A11", "patient02", "doctor05", second_future_day, time(10), "PENDING", "Đau vai khi vận động"),
        ("A12", "patient05", "doctor05", current_day, time(8, 30), "CANCELLED", "Tư vấn đau gối"),
    )


# Symptoms, diagnosis, guidance and prescriptions deliberately match each
# appointment and its invoice. Monetary values are VND with two SQL decimals.
DEMO_RECORDS = {
    "A01": (
        "Đầy bụng sau bữa ăn, không nôn, không sụt cân.",
        "Khó tiêu chức năng (K30).",
        "Ăn bữa nhỏ, theo dõi triệu chứng; tái khám nếu đau tăng hoặc xuất hiện dấu hiệu báo động.",
        (("Omeprazole 20 mg", 14, "1 viên/ngày", "Uống trước bữa sáng theo đơn mẫu."),),
    ),
    "A02": (
        "Mảng đỏ ngứa khu trú hai bàn tay sau dùng chất tẩy mới.",
        "Viêm da tiếp xúc kích ứng (L24.9).",
        "Tránh tác nhân nghi ngờ, dưỡng ẩm và tái khám nếu tổn thương lan rộng.",
        (("Kem hydrocortisone 1%", 1, "Bôi lớp mỏng", "Dùng ngắn ngày theo đơn mẫu."),),
    ),
    "A03": (
        "Tự đo huyết áp tại nhà dao động 130–145/80–90 mmHg, không đau ngực.",
        "Theo dõi tăng huyết áp (R03.0).",
        "Ghi nhật ký huyết áp 7 ngày, giảm muối và mang kết quả khi tái khám.",
        (),
    ),
    "A04": (
        "Hắt hơi, chảy mũi trong và nghẹt mũi buổi sáng; không sốt.",
        "Viêm mũi dị ứng (J30.4).",
        "Tránh dị nguyên nghi ngờ, vệ sinh mũi; tái khám nếu khó thở hoặc sốt.",
        (("Nước muối sinh lý xịt mũi", 1, "2 nhát mỗi bên", "Rửa mũi theo hướng dẫn mẫu."),),
    ),
    "A05": (
        "Đau gối phải khi lên cầu thang, không sưng nóng đỏ.",
        "Đau khớp gối, cần theo dõi (M25.56).",
        "Giảm tải khớp tạm thời, tập vận động phù hợp và tái khám nếu sưng hoặc đau tăng.",
        (("Paracetamol 500 mg", 10, "1 viên khi đau", "Dùng theo đơn mẫu, không vượt liều được bác sĩ hướng dẫn."),),
    ),
}

DEMO_INVOICES = {
    "A01": ("PAID", "CASH", (("Khám Nội tổng quát", 1, "200000.00"), ("Omeprazole 20 mg", 14, "2500.00"))),
    "A02": ("PAID", "TRANSFER", (("Khám Da liễu", 1, "250000.00"), ("Kem hydrocortisone 1%", 1, "45000.00"))),
    "A03": ("UNPAID", None, (("Khám Tim mạch", 1, "300000.00"),)),
    "A05": ("UNPAID", None, (("Khám Cơ Xương Khớp", 1, "250000.00"), ("Paracetamol 500 mg", 10, "1000.00"))),
}


def validate_demo_fixture(
    appointments: tuple[tuple[str, str, str, date, time, str, str], ...] | None = None,
    *,
    live_slot: tuple[date, time] | None = None,
) -> None:
    """Check the scenario before any database write."""
    current = clinic_now()
    rows = appointments if appointments is not None else build_demo_appointments(current)
    reserved_slot = live_slot if live_slot is not None else demo_live_slot(current)
    if len(DEMO_DOCTORS) != 5 or len(DEMO_PATIENTS) != 8 or len(rows) != 12:
        raise ValueError("Demo fixture has an unexpected number of doctors, patients or visits")
    statuses = Counter(row[5] for row in rows)
    if statuses != {"COMPLETED": 5, "PENDING": 2, "CONFIRMED": 2,
                    "CHECKED_IN": 1, "IN_PROGRESS": 1, "CANCELLED": 1}:
        raise ValueError(f"Demo appointment stages are incorrect: {statuses}")
    doctors = {row[0]: row for row in DEMO_DOCTORS}
    patients = {row[0] for row in DEMO_PATIENTS}
    seen_doctor_slots: set[tuple[str, date, time]] = set()
    seen_patient_slots: set[tuple[str, date, time]] = set()
    seen_specialty_days: set[tuple[str, date, str]] = set()
    for code, patient, doctor, day, starts, status, reason in rows:
        if patient not in patients or doctor not in doctors or not reason.strip():
            raise ValueError(f"Invalid appointment {code}")
        if day.isoweekday() > 5 or starts.minute not in {0, 30} or not time(8) <= starts < time(17):
            raise ValueError(f"Appointment {code} is outside a weekday 30-minute shift")
        if time(12) <= starts < time(13):
            raise ValueError(f"Appointment {code} is in the lunch break")
        if status != "CANCELLED":
            doctor_slot = (doctor, day, starts)
            patient_slot = (patient, day, starts)
            specialty_day = (patient, day, doctors[doctor][2])
            if (doctor_slot in seen_doctor_slots or patient_slot in seen_patient_slots
                    or specialty_day in seen_specialty_days):
                raise ValueError(f"Appointment {code} conflicts with another active appointment")
            seen_doctor_slots.add(doctor_slot)
            seen_patient_slots.add(patient_slot)
            seen_specialty_days.add(specialty_day)
    if ("doctor01", reserved_slot[0], reserved_slot[1]) in seen_doctor_slots:
        raise ValueError("The live demo slot must remain open")
    if set(DEMO_RECORDS) != {row[0] for row in rows if row[5] == "COMPLETED"}:
        raise ValueError("Every completed demo visit must have exactly one clinical record")
    if not set(DEMO_INVOICES).issubset(DEMO_RECORDS):
        raise ValueError("Invoices require a completed clinical record")
    for code, (status, method, items) in DEMO_INVOICES.items():
        total = sum((Decimal(price) * quantity for _, quantity, price in items), Decimal("0.00"))
        if total <= 0 or any(quantity <= 0 or Decimal(price) < 0 for _, quantity, price in items):
            raise ValueError(f"Invalid invoice for {code}")
        if (status == "PAID") != (method in {"CASH", "TRANSFER"}):
            raise ValueError(f"Payment status and method disagree for {code}")


def _add_user(
    session: Session, username: str, password: str, full_name: str,
    phone: str, role: str, created_at: datetime,
) -> User:
    user = User(
        username=username, password_hash=hash_password(password), full_name=full_name,
        phone=phone, email=f"{username}@example.com", role=role, is_active=True,
        created_at=created_at,
    )
    session.add(user)
    session.flush()
    return user


def _add_catalog_and_people(
    session: Session, user_created_at: datetime,
) -> tuple[dict[str, Doctor], dict[str, Patient]]:
    _add_user(session, "admin", ADMIN_PASSWORD, "Quản trị viên (đào tạo)",
              "0900000001", "ADMIN", user_created_at)
    staff_users = []
    for index, name in enumerate(("Nguyễn Ngọc Lan", "Trần Thanh Tâm"), start=1):
        staff_users.append(_add_user(session, f"reception{index:02d}", STAFF_PASSWORD, name,
                                     f"090000001{index}", "STAFF", user_created_at))

    specialties = {}
    for name in ("Nội tổng quát", "Da liễu", "Tim mạch", "Tai Mũi Họng", "Cơ Xương Khớp"):
        specialty = Specialty(specialty_name=name, description=f"Chuyên khoa {name} (dữ liệu demo)", is_active=True)
        session.add(specialty)
        specialties[name] = specialty
    clinics = {}
    for name, address in (
        ("Quận 1", "Đường Nguyễn Du, Quận 1, TP. Hồ Chí Minh (địa chỉ giả lập)"),
        ("Tân Bình", "Đường Cộng Hòa, Quận Tân Bình, TP. Hồ Chí Minh (địa chỉ giả lập)"),
        ("Bình Thạnh", "Đường Điện Biên Phủ, Quận Bình Thạnh, TP. Hồ Chí Minh (địa chỉ giả lập)"),
    ):
        clinic = Clinic(clinic_name=name, address=address, phone=None, is_active=True)
        session.add(clinic)
        clinics[name] = clinic
    session.flush()

    # Reception01 covers the full fictional network; reception02 is assigned
    # to the Tân Bình branch. The authorization model remains demonstrable.
    for clinic in clinics.values():
        session.add(StaffClinicAssignment(user_id=staff_users[0].user_id,
                                          clinic_id=clinic.clinic_id, is_active=True))
    session.add(StaffClinicAssignment(user_id=staff_users[1].user_id,
                                      clinic_id=clinics["Tân Bình"].clinic_id,
                                      is_active=True))

    # Include the same immutable consultation-fee catalog used by production
    # invoice validation; all entries are synthetic training prices.
    charge_specs = (
        ("GENERAL", "Nội tổng quát", "200000.00"),
        ("DERM", "Da liễu", "250000.00"),
        ("CARDIO", "Tim mạch", "300000.00"),
        ("ENT", "Tai Mũi Họng", "220000.00"),
        ("MSK", "Cơ Xương Khớp", "250000.00"),
    )
    for code, specialty_name, price in charge_specs:
        session.add(ChargeCatalog(
            code=f"CONSULT-{code}",
            display_name=f"Khám {specialty_name}",
            category="CONSULTATION",
            specialty_id=specialties[specialty_name].specialty_id,
            unit_price=Decimal(price),
            is_active=True,
            effective_from=datetime(2020, 1, 1),
        ))

    doctors = {}
    for index, (username, full_name, specialty, clinic_name) in enumerate(DEMO_DOCTORS, start=1):
        user = _add_user(session, username, DOCTOR_PASSWORD, full_name,
                         f"090000010{index}", "DOCTOR", user_created_at)
        doctor = Doctor(user_id=user.user_id, specialty_id=specialties[specialty].specialty_id,
                        clinic_id=clinics[clinic_name].clinic_id,
                        license_number=f"DEMO-BS-{index:03d}", is_active=True)
        session.add(doctor)
        session.flush()
        doctors[username] = doctor
        for weekday in range(1, 6):
            for begins, ends in ((time(8), time(12)), (time(13), time(17))):
                session.add(DoctorSchedule(doctor_id=doctor.doctor_id, day_of_week=weekday,
                                           start_time=begins, end_time=ends,
                                           slot_duration=30, is_active=True))

    patients = {}
    for username, full_name, birthday, gender, phone in DEMO_PATIENTS:
        user = _add_user(session, username, DEMO_PASSWORD, full_name, phone,
                         "PATIENT", user_created_at)
        patient = Patient(user_id=user.user_id, date_of_birth=birthday, gender=gender,
                          address="TP. Hồ Chí Minh (dữ liệu giả lập)")
        session.add(patient)
        session.flush()
        patients[username] = patient
    return doctors, patients


def _add_appointments(
    session: Session, doctors: dict[str, Doctor], patients: dict[str, Patient],
    rows: tuple[tuple[str, str, str, date, time, str, str], ...],
    now: datetime,
) -> dict[str, Appointment]:
    appointments = {}
    today = now.date()
    for code, patient_name, doctor_name, day, starts, status, reason in rows:
        doctor = doctors[doctor_name]
        ends = (datetime.combine(day, starts) + timedelta(minutes=30)).time()
        created_at = (
            datetime.combine(day - timedelta(days=1), time(8))
            if day < today else now.replace(tzinfo=None)
        )
        queue = None
        check_in_at = None
        if status == "COMPLETED":
            queue = "A-001"
            check_in_at = datetime.combine(day, time(8, 55))
        elif status == "CHECKED_IN":
            queue = "A-001"
            check_in_at = datetime.combine(day, time(9, 20))
        elif status == "IN_PROGRESS":
            queue = "A-001"
            check_in_at = datetime.combine(day, time(9, 21))
        appointment = Appointment(
            patient_id=patients[patient_name].patient_id, doctor_id=doctor.doctor_id,
            clinic_id=doctor.clinic_id, specialty_id=doctor.specialty_id,
            appointment_date=day, start_time=starts,
            end_time=ends, reason=reason, status=status, created_at=created_at,
            queue_number=queue, check_in_at=check_in_at,
            clinical_context_loaded_at=(
                datetime.combine(day, time(9, 25)) if status == "IN_PROGRESS" else None
            ),
            clinical_context_loaded_by_user_id=(
                doctor.user_id if status == "IN_PROGRESS" else None
            ),
            check_in_note="Đã xác nhận có mặt tại quầy." if check_in_at else None,
            cancellation_reason="Bệnh nhân thay đổi kế hoạch cá nhân." if status == "CANCELLED" else None,
        )
        session.add(appointment)
        session.flush()
        appointments[code] = appointment
    return appointments


def _add_clinical_and_billing(session: Session, appointments: dict[str, Appointment]) -> None:
    consultation_charges = {
        charge.display_name: charge
        for charge in session.scalars(
            select(ChargeCatalog).where(ChargeCatalog.category == "CONSULTATION")
        )
    }
    reception_user_id = session.scalar(select(User.user_id).where(User.username == "reception01"))
    for code, (symptoms, diagnosis, notes, medicines) in DEMO_RECORDS.items():
        appointment = appointments[code]
        examined_at = datetime.combine(appointment.appointment_date, time(9, 20))
        record = MedicalRecord(appointment_id=appointment.appointment_id, symptoms=symptoms,
                               diagnosis=diagnosis, notes=notes, examination_date=examined_at)
        session.add(record)
        session.flush()
        if medicines:
            prescription = Prescription(medical_record_id=record.medical_record_id,
                                        created_at=examined_at + timedelta(minutes=5))
            session.add(prescription)
            session.flush()
            for name, quantity, dosage, instructions in medicines:
                session.add(PrescriptionItem(prescription_id=prescription.prescription_id,
                                             medicine_name=name, quantity=quantity,
                                             dosage=dosage, instructions=instructions))

    for code, (status, method, rows) in DEMO_INVOICES.items():
        appointment = appointments[code]
        total = sum((Decimal(price) * quantity for _, quantity, price in rows), Decimal("0.00"))
        created_at = datetime.combine(appointment.appointment_date, time(9, 30))
        invoice = Invoice(appointment_id=appointment.appointment_id, total_amount=total,
                          status=status, created_at=created_at)
        session.add(invoice)
        session.flush()
        for name, quantity, price in rows:
            charge = consultation_charges.get(name)
            session.add(InvoiceItem(invoice_id=invoice.invoice_id,
                                    charge_id=charge.charge_id if charge else None,
                                    item_name=name, quantity=quantity,
                                    unit_price=Decimal(price)))
        if method:
            received = total + Decimal("15000.00") if method == "CASH" else total
            verified_at = created_at + timedelta(minutes=5)
            session.add(Payment(invoice_id=invoice.invoice_id, amount=total,
                                payment_method=method,
                                amount_received=received,
                                change_due=received - total,
                                recorded_by_user_id=reception_user_id,
                                external_reference="TRAINING-A02-TRANSFER" if method == "TRANSFER" else None,
                                verified_at=verified_at,
                                payment_date=verified_at))


def _verify_written_seed(
    session: Session,
    rows: tuple[tuple[str, str, str, date, time, str, str], ...],
) -> None:
    """Catch inconsistent fixture writes before committing the seed marker."""
    session.flush()
    appointments = session.execute(select(Appointment)).scalars().all()
    records = session.execute(select(MedicalRecord)).scalars().all()
    invoices = session.execute(select(Invoice)).scalars().all()
    payments = session.execute(select(Payment)).scalars().all()
    if (len(appointments), len(records), len(invoices), len(payments)) != (12, 5, 4, 2):
        raise ValueError("Demo appointment/record/invoice/payment counts do not match")
    if Counter(item.status for item in appointments) != Counter(row[5] for row in rows):
        raise ValueError("Persisted appointment stages do not match the fixture")
    records_by_appointment = {item.appointment_id for item in records}
    if records_by_appointment != {item.appointment_id for item in appointments if item.status == "COMPLETED"}:
        raise ValueError("Completed appointments and records differ")
    if any(
        item.specialty_id is None
        or (item.status == "IN_PROGRESS" and (
            item.clinical_context_loaded_at is None
            or item.clinical_context_loaded_by_user_id is None
        ))
        for item in appointments
    ):
        raise ValueError("Specialty snapshot or in-progress clinical context is missing")
    items = session.execute(select(InvoiceItem)).scalars().all()
    for invoice in invoices:
        amount = sum((item.unit_price * item.quantity for item in items
                      if item.invoice_id == invoice.invoice_id), Decimal("0.00"))
        payment = next((p for p in payments if p.invoice_id == invoice.invoice_id), None)
        if amount != invoice.total_amount or (invoice.status == "PAID") != (payment is not None):
            raise ValueError(f"Invoice {invoice.invoice_id} is inconsistent")
        if payment is not None and payment.amount != amount:
            raise ValueError(f"Payment for invoice {invoice.invoice_id} is inconsistent")
        if payment is not None and (
            payment.recorded_by_user_id is None
            or payment.verified_at is None
            or payment.amount_received is None
            or payment.change_due != payment.amount_received - amount
        ):
            raise ValueError(f"Payment verification for invoice {invoice.invoice_id} is incomplete")
    charges = session.scalars(select(ChargeCatalog)).all()
    assignments = session.scalars(select(StaffClinicAssignment)).all()
    if len(charges) != 5 or len(assignments) != 4:
        raise ValueError("Synthetic charge catalog or staff clinic access is incomplete")


def seed_database(session: Session) -> bool:
    """Seed once; return False when this version was already applied."""
    settings = get_settings()
    if settings.db_name != PROJECT_DB_NAME or settings.app_mode != "demo":
        raise ValueError(f"Synthetic seed requires APP_MODE=demo and DB_NAME={PROJECT_DB_NAME}")
    if session.execute(text("SELECT DB_NAME()")).scalar_one() != PROJECT_DB_NAME:
        raise ValueError(f"Connection is not using {PROJECT_DB_NAME}")
    now = clinic_now()
    rows = build_demo_appointments(now)
    validate_demo_fixture(rows, live_slot=demo_live_slot(now))
    already_seeded = session.execute(
        text("SELECT 1 FROM dbo.SchemaMigrations WHERE MigrationID = :version"),
        {"version": SEED_VERSION},
    ).scalar_one_or_none()
    if already_seeded is not None:
        return False
    if any(
        session.execute(select(identifier).limit(1)).first() is not None
        for identifier in (
            User.user_id, Patient.patient_id, Doctor.doctor_id,
            Clinic.clinic_id, Specialty.specialty_id, Appointment.appointment_id,
            MedicalRecord.medical_record_id, Invoice.invoice_id, Payment.payment_id,
            ChargeCatalog.charge_id,
        )
    ):
        raise ValueError("Project DB already has data without the seed marker; no data was changed")
    try:
        first_visit = min(row[3] for row in rows)
        user_created_at = datetime.combine(first_visit - timedelta(days=7), time(8))
        doctors, patients = _add_catalog_and_people(session, user_created_at)
        appointments = _add_appointments(session, doctors, patients, rows, now)
        _add_clinical_and_billing(session, appointments)
        _verify_written_seed(session, rows)
        session.execute(
            text("INSERT INTO dbo.SchemaMigrations (MigrationID) VALUES (:version)"),
            {"version": SEED_VERSION},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return True


def main() -> None:
    from backend.app.db.init_db import ensure_database_initialized

    try:
        ensure_database_initialized()
        with SessionLocal() as session:
            created = seed_database(session)
    except SQLAlchemyError as exc:
        raise SystemExit(f"Project seed failed. Check SQL Server and project DB: {type(exc).__name__}") from None
    except Exception as exc:
        raise SystemExit(f"Project seed failed: {exc}") from None
    print("Synthetic project seed created." if created else "Seed already applied; existing data preserved.")


if __name__ == "__main__":
    main()
