"""Idempotent demonstration data for the existing SQL Server schema.

Run with::

    python -m backend.app.db.seed

This module never creates, drops, or alters database objects.
It seeds rich, realistic, Vietnamese-localized medical clinic data covering:
- Administrator (ADMIN)
- Reception / Cashier Staff (STAFF)
- Multi-specialty certified Doctors (DOCTOR)
- Patients with diverse age, gender, medical history (PATIENT)
- Real-world Clinical Diagnoses (ICD-10 aligned), Symptoms, Doctor Advice
- Realistic Prescriptions with exact dosages and patient instructions
- Comprehensive Itemized Invoices with both PAID (Cash/Card) and UNPAID states
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

ADMIN_PASSWORD = "Admin123!"
DOCTOR_PASSWORD = "Doctor123!"
DEMO_PASSWORD = "Password123!"
STAFF_PASSWORD = "Staff123!"


def _first(session: Session, statement):
    return session.execute(statement).scalars().first()


def _ensure_specialty(
    session: Session,
    name: str,
    description: str,
    legacy_name: str | None = None,
) -> Specialty:
    specialty = None
    if legacy_name:
        specialty = _first(session, select(Specialty).where(Specialty.specialty_name == legacy_name))
    if specialty is None:
        specialty = _first(session, select(Specialty).where(Specialty.specialty_name == name))
    if specialty is None:
        specialty = Specialty(specialty_name=name)
        session.add(specialty)
    specialty.specialty_name = name
    specialty.description = description
    specialty.is_active = True
    session.flush()
    return specialty


def _ensure_clinic(
    session: Session,
    name: str,
    address: str,
    phone: str,
    legacy_name: str | None = None,
) -> Clinic:
    clinic = None
    if legacy_name:
        clinic = _first(session, select(Clinic).where(Clinic.clinic_name == legacy_name))
    if clinic is None:
        clinic = _first(session, select(Clinic).where(Clinic.clinic_name == name))
    if clinic is None:
        clinic = Clinic(clinic_name=name)
        session.add(clinic)
    clinic.clinic_name = name
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
    slot_duration: int = 30,
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
    schedule.slot_duration = slot_duration
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
    legacy_reason: str | None = None,
) -> Appointment:
    stmt = select(Appointment).where(
        Appointment.patient_id == patient.patient_id,
        Appointment.doctor_id == doctor.doctor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.start_time == start_time,
    )
    appointment = _first(session, stmt)
    if appointment is None and legacy_reason:
        stmt_legacy = select(Appointment).where(
            Appointment.patient_id == patient.patient_id,
            Appointment.doctor_id == doctor.doctor_id,
            Appointment.reason == legacy_reason,
        )
        appointment = _first(session, stmt_legacy)
    if appointment is None:
        stmt_reason = select(Appointment).where(
            Appointment.patient_id == patient.patient_id,
            Appointment.doctor_id == doctor.doctor_id,
            Appointment.reason == reason,
        )
        appointment = _first(session, stmt_reason)
    if appointment is None:
        appointment = Appointment(patient_id=patient.patient_id, reason=reason)
        session.add(appointment)
    appointment.doctor_id = doctor.doctor_id
    appointment.clinic_id = clinic.clinic_id
    appointment.appointment_date = appointment_date
    appointment.start_time = start_time
    appointment.end_time = end_time
    appointment.reason = reason
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

    existing_items = list(
        session.execute(
            select(PrescriptionItem)
            .where(PrescriptionItem.prescription_id == prescription.prescription_id)
            .order_by(PrescriptionItem.prescription_item_id)
        ).scalars().all()
    )

    for idx, data in enumerate(items):
        if idx < len(existing_items):
            item = existing_items[idx]
            item.medicine_name = data["medicine_name"]
            item.quantity = data["quantity"]
            item.dosage = data["dosage"]
            item.instructions = data["instructions"]
        else:
            item = PrescriptionItem(
                prescription_id=prescription.prescription_id,
                medicine_name=data["medicine_name"],
                quantity=data["quantity"],
                dosage=data["dosage"],
                instructions=data["instructions"],
            )
            session.add(item)
    if len(existing_items) > len(items):
        for extra in existing_items[len(items):]:
            session.delete(extra)
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

    existing_items = list(
        session.execute(
            select(InvoiceItem)
            .where(InvoiceItem.invoice_id == invoice.invoice_id)
            .order_by(InvoiceItem.invoice_item_id)
        ).scalars().all()
    )

    for idx, (item_name, quantity, unit_price) in enumerate(items):
        if idx < len(existing_items):
            item = existing_items[idx]
            item.item_name = item_name
            item.quantity = quantity
            item.unit_price = unit_price
        else:
            item = InvoiceItem(
                invoice_id=invoice.invoice_id,
                item_name=item_name,
                quantity=quantity,
                unit_price=unit_price,
            )
            session.add(item)
    if len(existing_items) > len(items):
        for extra in existing_items[len(items):]:
            session.delete(extra)
    session.flush()

    # Sum only the active items for this invoice
    active_items = session.execute(
        select(InvoiceItem)
        .where(InvoiceItem.invoice_id == invoice.invoice_id)
        .order_by(InvoiceItem.invoice_item_id)
    ).scalars().all()

    invoice.total_amount = sum(
        (item.unit_price * item.quantity for item in active_items), start=Decimal("0.00")
    )
    invoice.status = status
    completed_at = datetime.combine(appointment.appointment_date, appointment.end_time)
    invoice.created_at = completed_at + timedelta(minutes=10)
    session.flush()

    payment = _first(session, select(Payment).where(Payment.invoice_id == invoice.invoice_id))
    if status == "PAID" and payment_method is not None:
        if payment is None:
            payment = Payment(invoice_id=invoice.invoice_id)
            session.add(payment)
        payment.amount = invoice.total_amount
        payment.payment_method = payment_method
        payment.payment_date = completed_at + timedelta(minutes=15)
    elif payment is not None:
        session.delete(payment)
    session.flush()
    return invoice


def seed_database(session: Session) -> None:
    """Insert or update the deterministic, realistic demonstration dataset in one transaction."""

    today = clinic_today()

    # ── 1. Quản trị viên (ADMIN) ──────────────────────────────────────────────
    _ensure_user(
        session,
        username="admin",
        password=ADMIN_PASSWORD,
        full_name="Quản trị viên hệ thống",
        phone="0900000000",
        email="admin@clinicmed.vn",
        role="ADMIN",
    )

    # ── 2. Nhân viên tiếp đón & Thu ngân (STAFF) ───────────────────────────────
    _ensure_user(
        session,
        username="reception01",
        password=STAFF_PASSWORD,
        full_name="Nguyễn Thị Mai",
        phone="0908123456",
        email="mai.nguyen@clinicmed.vn",
        role="STAFF",
    )
    _ensure_user(
        session,
        username="reception02",
        password=STAFF_PASSWORD,
        full_name="Lê Hồng Hạnh",
        phone="0908654321",
        email="hanh.le@clinicmed.vn",
        role="STAFF",
    )

    # ── 3. Danh mục chuyên khoa (Specialties) ──────────────────────────────────
    internal = _ensure_specialty(
        session,
        "Nội tổng quát",
        "Khám và điều trị các bệnh lý nội khoa người lớn, theo dõi sức khỏe tổng quát định kỳ",
        legacy_name="Internal Medicine",
    )
    dermatology = _ensure_specialty(
        session,
        "Da liễu",
        "Chẩn đoán và điều trị bệnh ngoài da, dị ứng, mụn trứng cá và phục hồi tổn thương da",
        legacy_name="Dermatology",
    )
    cardiology = _ensure_specialty(
        session,
        "Tim mạch",
        "Tầm soát và điều trị tăng huyết áp, bệnh mạch vành, rối loạn nhịp tim và suy tim",
        legacy_name="Cardiology",
    )
    gastro = _ensure_specialty(
        session,
        "Tiêu hóa - Gan mật",
        "Chẩn đoán và điều trị viêm loét dạ dày, trào ngược GERD, đại tràng và men gan cao",
    )
    ent = _ensure_specialty(
        session,
        "Tai Mũi Họng",
        "Khám và điều trị viêm họng, viêm xoang mũi, viêm amidan và bệnh lý tai giữa",
    )
    ortho = _ensure_specialty(
        session,
        "Cơ Xương Khớp",
        "Khám và điều trị thoái hóa khớp, thoát vị đĩa đệm, gout, loãng xương và đau cơ",
    )

    # ── 4. Danh mục cơ sở phòng khám (Clinics) ─────────────────────────────────
    central = _ensure_clinic(
        session,
        "Phòng khám Đa khoa Sài Gòn Med (Cơ sở Quận 1)",
        "123 Nguyễn Huệ, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh",
        "02838220001",
        legacy_name="Central Clinic",
    )
    riverside = _ensure_clinic(
        session,
        "Phòng khám Đa khoa CarePlus (Cơ sở Tân Bình)",
        "107 Tân Hải, Phường 13, Quận Tân Bình, TP. Hồ Chí Minh",
        "02838220002",
        legacy_name="Riverside Clinic",
    )
    happiness = _ensure_clinic(
        session,
        "Phòng khám Đa khoa Hạnh Phúc (Cơ sở Bình Thạnh)",
        "45 Bạch Đằng, Phường 15, Quận Bình Thạnh, TP. Hồ Chí Minh",
        "02838220003",
    )

    # ── 5. Danh sách Bác sĩ chuyên khoa (DOCTOR) ──────────────────────────────
    doctor_specs = (
        (
            "doctor01",
            "BS. CKI Nguyễn Minh Anh",
            "0901000001",
            "bs.minhanh@clinicmed.vn",
            internal,
            central,
            "001245/HCM-CCHN",
        ),
        (
            "doctor02",
            "ThS. BS Trần Thu Hà",
            "0901000002",
            "bs.thuha@clinicmed.vn",
            dermatology,
            riverside,
            "003489/HCM-CCHN",
        ),
        (
            "doctor03",
            "BSCKII Lê Quang Huy",
            "0901000003",
            "bs.quanghuy@clinicmed.vn",
            cardiology,
            central,
            "005612/HCM-CCHN",
        ),
        (
            "doctor04",
            "ThS. BS Phạm Hoàng Nam",
            "0901000004",
            "bs.hoangnam@clinicmed.vn",
            gastro,
            happiness,
            "007834/HCM-CCHN",
        ),
        (
            "doctor05",
            "BS. CKI Đỗ Bích Thủy",
            "0901000005",
            "bs.bichthuy@clinicmed.vn",
            ent,
            central,
            "009123/HCM-CCHN",
        ),
        (
            "doctor06",
            "BSCKII Hoàng Văn Thái",
            "0901000006",
            "bs.vanthai@clinicmed.vn",
            ortho,
            riverside,
            "011456/HCM-CCHN",
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

    # ── 6. Lịch làm việc định kỳ của Bác sĩ (DoctorSchedules) ─────────────────
    for doc in doctors:
        # Ca sáng: Thứ 2, 3, 4, 5, 6, 7 (08:00 - 12:00)
        for day in (1, 2, 3, 4, 5, 6):
            _ensure_schedule(
                session,
                doc,
                day_of_week=day,
                start_time=time(8, 0),
                end_time=time(12, 0),
                slot_duration=30,
            )
        # Ca chiều: Thứ 2, 3, 4, 5 (13:30 - 17:30)
        for day in (1, 2, 3, 4, 5):
            _ensure_schedule(
                session,
                doc,
                day_of_week=day,
                start_time=time(13, 30),
                end_time=time(17, 30),
                slot_duration=30,
            )

    # ── 7. Bệnh nhân mẫu (Patients) ──────────────────────────────────────────
    patient_raw = (
        ("patient01", "Nguyễn Văn An", "0900000001", "patient01@example.com", date(1995, 5, 12), "MALE", "158/4 Điện Biên Phủ, Phường 15, Bình Thạnh, TP.HCM"),
        ("patient02", "Trần Thị Bình", "0900000002", "patient02@example.com", date(1998, 11, 8), "FEMALE", "42/3 Võ Văn Ngân, Phường Linh Chiểu, TP. Thủ Đức, TP.HCM"),
        ("patient03", "Lê Hoàng Long", "0900000003", "patient03@example.com", date(1982, 8, 20), "MALE", "79 Lê Thị Riêng, Phường Bến Thành, Quận 1, TP.HCM"),
        ("patient04", "Phạm Thùy Linh", "0900000004", "patient04@example.com", date(2001, 3, 15), "FEMALE", "312 Cách Mạng Tháng 8, Phường 10, Quận 3, TP.HCM"),
        ("patient05", "Vũ Đình Trọng", "0900000005", "patient05@example.com", date(1965, 10, 2), "MALE", "88 Hoàng Hoa Thám, Phường 12, Tân Bình, TP.HCM"),
    )
    patients: list[Patient] = []
    for username, name, phone, email, dob, gender, addr in patient_raw:
        user = _ensure_user(
            session,
            username=username,
            password=DEMO_PASSWORD,
            full_name=name,
            phone=phone,
            email=email,
            role="PATIENT",
        )
        patients.append(
            _ensure_patient(
                session,
                user=user,
                date_of_birth=dob,
                gender=gender,
                address=addr,
            )
        )

    p1, p2, p3, p4, p5 = patients
    d1, d2, d3, d4, d5, d6 = doctors

    # ── 8. Lịch hẹn khám chữa bệnh (Appointments) ────────────────────────────
    # Cấu trúc: (patient, doctor, clinic, day_delta, start_time, reason, status, legacy_reason)
    appointment_specs = (
        # -- Patient 1 (Nguyễn Văn An) --
        (p1, d1, central, -90, time(8, 0), "Khám sức khỏe tổng quát định kỳ và xét nghiệm máu", "COMPLETED", "Annual health check"),
        (p1, d2, riverside, -60, time(9, 0), "Nổi mẩn đỏ ngứa vùng mu bàn tay và cẳng tay sau tiếp xúc hóa chất", "COMPLETED", "Skin allergy consultation"),
        (p1, d3, central, -30, time(10, 0), "Hồi hộp, đánh trống ngực từng cơn và đau đầu vùng gáy", "COMPLETED", "Cardiovascular screening"),
        (p1, d5, central, -7, time(14, 0), "Đau rát họng, sốt nhẹ và nuốt vướng tái phát", "COMPLETED", "Post-treatment follow-up"),
        (p1, d1, central, 3, time(9, 0), "Tái khám theo dõi chỉ số huyết áp và lipid máu định kỳ", "CONFIRMED", "Follow-up examination"),
        (p1, d2, riverside, 10, time(10, 30), "Tái khám kiểm tra đáp ứng tổn thương viêm da tiếp xúc", "PENDING", "Recurring skin irritation"),
        (p1, d3, central, -2, time(15, 0), "Tức ngực nhẹ khi leo cầu thang (đã chuyển lịch khám bệnh viện)", "CANCELLED", "Cancelled heart consultation"),
        # -- Patient 2 (Trần Thị Bình) --
        (p2, d5, central, -45, time(8, 30), "Ho kéo dài có đờm, ngạt mũi và đau nhức vùng trán", "COMPLETED", "Persistent cough"),
        (p2, d4, happiness, 0, time(11, 0), "Đau quặn thượng vị âm ỉ, ợ chua và buồn nôn sau khi ăn đồ cay", "CHECKED_IN", "Chest discomfort assessment"),
        (p2, d2, riverside, -15, time(14, 30), "Mụn trứng cá viêm đỏ vùng má và cằm kéo dài", "COMPLETED", None),
        # -- Patient 3 (Lê Hoàng Long) --
        (p3, d3, central, -20, time(9, 30), "Chóng mặt khi thay đổi tư thế, huyết áp đo tại nhà dao động 150/95", "COMPLETED", None),
        (p3, d3, central, 0, time(14, 0), "Đo điện tâm đồ và kiểm tra chức năng tim định kỳ", "IN_PROGRESS", None),
        # -- Patient 4 (Phạm Thùy Linh) --
        (p4, d4, happiness, -12, time(10, 0), "Đầy bụng, khó tiêu và trào ngược thức ăn lên họng khi nằm", "COMPLETED", None),
        (p4, d6, riverside, 5, time(15, 0), "Đau mỏi vùng cổ vai gáy và tê nhẹ dọc cánh tay phải khi ngồi máy tính", "PENDING", None),
        # -- Patient 5 (Vũ Đình Trọng) --
        (p5, d6, riverside, -25, time(8, 0), "Đau khớp gối hai bên khi đi lại, lục cục khớp khi đứng lên ngồi xuống", "COMPLETED", None),
        (p5, d1, central, 7, time(8, 30), "Khám định kỳ bệnh lý tim mạch và kiểm tra chức năng gan thận", "CONFIRMED", None),
    )

    created_appointments: dict[int, Appointment] = {}
    for idx, (patient, doctor, clinic, day_delta, starts_at, reason, status, legacy_reason) in enumerate(appointment_specs):
        end_datetime = datetime.combine(today, starts_at) + timedelta(minutes=30)
        appt = _ensure_appointment(
            session,
            patient=patient,
            doctor=doctor,
            clinic=clinic,
            appointment_date=today + timedelta(days=day_delta),
            start_time=starts_at,
            end_time=end_datetime.time(),
            reason=reason,
            status=status,
            legacy_reason=legacy_reason,
        )
        created_appointments[idx] = appt

    # ── 9. Hồ sơ bệnh án điện tử (MedicalRecords) ──────────────────────────────
    # Cấu trúc: (appointment_idx, symptoms, diagnosis, notes)
    medical_specs = (
        (
            0,
            "Bệnh nhân tỉnh táo, tiếp xúc tốt. Thể trạng trung bình. Than phiền mệt mỏi nhẹ sau giờ làm việc, không sốt, ăn uống bình thường. Huyết áp: 120/80 mmHg, Mạch: 76 l/p.",
            "Khám sức khỏe tổng quát định kỳ - Rối loạn lipid máu nhẹ (E78.0)",
            "Chế độ ăn giảm chất béo bão hòa và nội tạng động vật. Tăng cường rau xanh, duy trì đi bộ 30 phút/ngày. Uống đủ 2 lít nước.",
        ),
        (
            1,
            "Nhiều dát đỏ rải rác kèm sẩn ngứa vùng mu bàn tay và cẳng tay hai bên. Vùng da tổn thương có dấu hiệu rỉ dịch nhẹ do gãi, không loét sâu. Xuất hiện sau khi dọn nhà dùng hóa chất tẩy rửa.",
            "Viêm da tiếp xúc dị ứng do hóa chất gia dụng (L23.8)",
            "Tránh tiếp xúc trực tiếp với nước rửa chén, chất tẩy rửa. Đeo găng tay cao su lót vải cotton khi làm việc nhà. Không gãi chà xát mạnh gây bội nhiễm.",
        ),
        (
            2,
            "Hồi hộp, thỉnh thoảng đánh trống ngực khi căng thẳng công việc. Đau âm ỉ vùng chẩm gáy vào buổi sáng. Huyết áp đo tại phòng khám: 146/92 mmHg, nhịp tim đều 82 l/p. Tiếng tim T1 T2 rõ.",
            "Tăng huyết áp nguyên phát độ 1 (I10) - Rối loạn thần kinh tim nhẹ",
            "Hạn chế ăn mặn (dưới 5g muối/ngày), kiêng rượu bia, cà phê. Đo huyết áp mỗi ngày lúc 7h sáng ghi nhật ký. Tái khám sau 1 tháng.",
        ),
        (
            3,
            "Niêm mạc họng đỏ xung huyết, amidan hai bên phì đại độ I, có vài chấm mủ trắng nhỏ. Sốt nhẹ 38.1°C, ho rát họng có đờm vàng đục, nuốt đau.",
            "Viêm amidan mủ cấp tính (J03.9)",
            "Uống đủ liều kháng sinh 7 ngày, tuyệt đối không tự ý ngưng thuốc. Súc họng nước muối sinh lý 0.9% 4 lần/ngày. Uống nhiều nước ấm, tránh uống nước đá.",
        ),
        (
            7,
            "Ho khan từng cơn kéo dài 2 tuần, ngạt mũi luân phiên hai bên, dịch mũi trong sau chuyển vàng. Đau tức vùng trán và hốc mắt khi cúi đầu. Sốt nhẹ về chiều.",
            "Viêm mũi xoang cấp xuất tiết mủ (J01.9)",
            "Xịt rửa mũi bằng nước muối biển sâu trước khi xịt thuốc. Giữ ấm vùng cổ và mũi khi ra gió hoặc nằm điều hòa nhiệt độ dưới 26°C.",
        ),
        (
            9,
            "Tổn thương da dạng mụn sẩn, mụn mủ kích thước 2-4mm tập trung vùng má và cằm, nền da nhờn nhiều bóng dầu. Không ngứa nhưng đau rát khi sờ.",
            "Trứng cá mủ mức độ trung bình (L70.0)",
            "Rửa mặt ngày 2 lần bằng sữa rửa mặt dịu nhẹ kiềm dầu. Không tự ý nặn mụn. Bôi kem chống nắng phổ rộng khi ra ngoài trời.",
        ),
        (
            10,
            "Hoa mắt chóng mặt từng cơn khi thay đổi tư thế từ ngồi sang đứng dậy nhanh. Huyết áp đo tại khám: 152/96 mmHg. Không yếu liệt chi, không rối loạn ngôn ngữ.",
            "Tăng huyết áp vô căn độ 1 (I10) - Thiểu năng tuần hoàn não (G45.9)",
            "Uống thuốc hạ áp đều đặn mỗi sáng trước bữa ăn. Không thay đổi tư thế đột ngột. Tránh thức khuya và làm việc quá sức.",
        ),
        (
            12,
            "Đau âm ỉ rát bỏng vùng thượng vị xuất hiện sau bữa ăn 1-2 giờ, ợ chua, cảm giác nghẹn vướng vùng cổ họng khi nằm ngủ ban đêm.",
            "Trào ngược dạ dày - thực quản độ A (K21.0) - Viêm dạ dày trợt nông",
            "Chia nhỏ bữa ăn, không ăn quá no. Tránh nằm ngay sau khi ăn ít nhất 2 giờ. Kê cao đầu giường 15cm khi ngủ. Kiêng đồ ăn chua cay, nước ngọt có ga.",
        ),
        (
            14,
            "Đau khớp gối hai bên nhiều tháng nay, đau tăng khi đi bộ lâu hoặc lên xuống cầu thang. Khớp có tiếng lạo xạo khi vận động, cứng khớp buổi sáng khoảng 15 phút.",
            "Thoái hóa khớp gối nguyên phát hai bên giai đoạn II (M17.0)",
            "Hạn chế leo cầu thang, không ngồi xổm hoặc mang vác nặng. Tập đạp xe nhẹ nhàng tại chỗ hoặc bơi lội để tăng cường cơ quanh gối.",
        ),
    )

    records: dict[int, MedicalRecord] = {}
    for appt_idx, symptoms, diagnosis, notes in medical_specs:
        appt = created_appointments[appt_idx]
        record = _ensure_medical_record(
            session,
            appt,
            symptoms=symptoms,
            diagnosis=diagnosis,
            notes=notes,
        )
        records[appt_idx] = record

    # ── 10. Đơn thuốc điện tử chi tiết (Prescriptions & Items) ────────────────
    # Đơn thuốc cho Appointment 0 (patient01 - Rối loạn lipid máu)
    _ensure_prescription(
        session,
        records[0],
        [
            {
                "medicine_name": "Atorvastatin (Lipitor) 10mg",
                "quantity": 30,
                "dosage": "10 mg",
                "instructions": "Uống 1 viên vào buổi tối trước khi đi ngủ",
            },
            {
                "medicine_name": "Vitamin 3B (B1, B6, B12)",
                "quantity": 60,
                "dosage": "1 viên",
                "instructions": "Uống 1 viên/lần, ngày 2 lần sau bữa ăn sáng và tối",
            },
        ],
    )

    # Đơn thuốc cho Appointment 1 (patient01 - Viêm da tiếp xúc dị ứng)
    _ensure_prescription(
        session,
        records[1],
        [
            {
                "medicine_name": "Fexofenadine (Telfast) 180mg",
                "quantity": 10,
                "dosage": "180 mg",
                "instructions": "Uống 1 viên vào buổi sáng sau ăn",
            },
            {
                "medicine_name": "Kem bôi Fucicort 15g (Fusidic acid + Betamethasone)",
                "quantity": 1,
                "dosage": "Tuýp 15g",
                "instructions": "Thoa một lớp mỏng lên vùng da tổn thương ngày 2 lần sáng và tối",
            },
            {
                "medicine_name": "Kem dưỡng ẩm Cerave Moisturizing 50ml",
                "quantity": 1,
                "dosage": "Tuýp 50ml",
                "instructions": "Thoa dưỡng ẩm toàn thân ngày 2-3 lần sau khi tắm sạch",
            },
        ],
    )

    # Đơn thuốc cho Appointment 2 (patient01 - Tăng huyết áp độ 1)
    _ensure_prescription(
        session,
        records[2],
        [
            {
                "medicine_name": "Amlodipine (Amlor) 5mg",
                "quantity": 30,
                "dosage": "5 mg",
                "instructions": "Uống 1 viên vào buổi sáng sau khi ăn",
            },
            {
                "medicine_name": "Magne-B6 Corbiere",
                "quantity": 30,
                "dosage": "1 viên",
                "instructions": "Uống 1 viên/lần, ngày 2 lần sau ăn trưa và tối",
            },
        ],
    )

    # Đơn thuốc cho Appointment 3 (patient01 - Viêm amidan mủ cấp)
    _ensure_prescription(
        session,
        records[3],
        [
            {
                "medicine_name": "Klamentin (Amoxicillin/Clavulanic acid) 1000mg",
                "quantity": 14,
                "dosage": "1 g",
                "instructions": "Uống 1 viên/lần, ngày 2 lần ngay trước bữa ăn sáng và tối (đủ 7 ngày)",
            },
            {
                "medicine_name": "Paracetamol (Panadol Extra) 500mg",
                "quantity": 10,
                "dosage": "500 mg",
                "instructions": "Uống 1 viên khi sốt trên 38.5 độ C hoặc rát họng nhiều, cách ít nhất 4-6 giờ",
            },
            {
                "medicine_name": "Siro ho thảo dược Prospan 100ml",
                "quantity": 1,
                "dosage": "Chai 100ml",
                "instructions": "Uống 5ml/lần, ngày 3 lần sau bữa ăn",
            },
        ],
    )

    # Đơn thuốc cho Appointment 7 (patient02 - Viêm mũi xoang cấp)
    _ensure_prescription(
        session,
        records[7],
        [
            {
                "medicine_name": "Cefuroxime (Zinnat) 500mg",
                "quantity": 14,
                "dosage": "500 mg",
                "instructions": "Uống 1 viên/lần, ngày 2 lần sau ăn sáng và tối",
            },
            {
                "medicine_name": "Xịt mũi Avamys (Fluticasone furoate)",
                "quantity": 1,
                "dosage": "Chai xịt 120 liều",
                "instructions": "Xịt mỗi bên mũi 1 nhát vào buổi sáng sau khi rửa mũi sạch",
            },
        ],
    )

    # Đơn thuốc cho Appointment 14 (patient05 - Thoái hóa khớp gối)
    _ensure_prescription(
        session,
        records[14],
        [
            {
                "medicine_name": "Celecoxib (Celebrex) 200mg",
                "quantity": 20,
                "dosage": "200 mg",
                "instructions": "Uống 1 viên vào buổi sáng sau bữa ăn no",
            },
            {
                "medicine_name": "Glucosamine sulfate 1500mg",
                "quantity": 30,
                "dosage": "1500 mg",
                "instructions": "Uống 1 gói pha nước uống mỗi ngày trong bữa ăn",
            },
            {
                "medicine_name": "Esomeprazole (Nexium) 40mg",
                "quantity": 20,
                "dosage": "40 mg",
                "instructions": "Uống 1 viên vào buổi sáng trước ăn 30 phút để bảo vệ dạ dày",
            },
        ],
    )

    # ── 11. Hóa đơn viện phí & Giao dịch thanh toán (Invoices & Payments) ──────
    # Hóa đơn 0: patient01 - Đã thanh toán qua THẺ (CARD)
    _ensure_invoice(
        session,
        created_appointments[0],
        status="PAID",
        items=[
            ("Khám chuyên khoa Nội tổng quát", 1, Decimal("200000.00")),
            ("Xét nghiệm công thức máu toàn phần (CBC)", 1, Decimal("150000.00")),
            ("Xét nghiệm bộ mỡ máu toàn phần (Lipid panel)", 1, Decimal("250000.00")),
        ],
        payment_method="CARD",
    )

    # Hóa đơn 1: patient01 - Đã thanh toán bằng TIỀN MẶT (CASH)
    _ensure_invoice(
        session,
        created_appointments[1],
        status="PAID",
        items=[
            ("Khám chuyên khoa Da liễu", 1, Decimal("250000.00")),
            ("Soi tươi tìm vi nấm bề mặt da", 1, Decimal("120000.00")),
        ],
        payment_method="CASH",
    )

    # Hóa đơn 2: patient01 - Đã thanh toán qua THẺ (CARD)
    _ensure_invoice(
        session,
        created_appointments[2],
        status="PAID",
        items=[
            ("Khám chuyên khoa Tim mạch", 1, Decimal("300000.00")),
            ("Điện tâm đồ (ECG) 12 chuyển đạo", 1, Decimal("150000.00")),
            ("Siêu âm tim màu Doppler", 1, Decimal("450000.00")),
        ],
        payment_method="CARD",
    )

    # Hóa đơn 3: patient01 - CHƯA THANH TOÁN (UNPAID) - Đợt khám gần nhất
    _ensure_invoice(
        session,
        created_appointments[3],
        status="UNPAID",
        items=[
            ("Khám chuyên khoa Tai Mũi Họng", 1, Decimal("250000.00")),
            ("Nội soi Tai Mũi Họng ống mềm chẩn đoán", 1, Decimal("300000.00")),
        ],
    )

    # Hóa đơn 7: patient02 - Đã thanh toán bằng TIỀN MẶT (CASH)
    _ensure_invoice(
        session,
        created_appointments[7],
        status="PAID",
        items=[
            ("Khám chuyên khoa Tai Mũi Họng", 1, Decimal("250000.00")),
            ("Nội soi vòm mũi họng", 1, Decimal("200000.00")),
        ],
        payment_method="CASH",
    )

    # Hóa đơn 10: patient03 - Đã thanh toán qua THẺ (CARD)
    _ensure_invoice(
        session,
        created_appointments[10],
        status="PAID",
        items=[
            ("Khám chuyên khoa Tim mạch", 1, Decimal("300000.00")),
            ("Điện tâm đồ (ECG) 12 chuyển đạo", 1, Decimal("150000.00")),
            ("Siêu âm Doppler động mạch cảnh", 1, Decimal("350000.00")),
        ],
        payment_method="CARD",
    )

    # Hóa đơn 14: patient05 - Đã thanh toán bằng TIỀN MẶT (CASH)
    _ensure_invoice(
        session,
        created_appointments[14],
        status="PAID",
        items=[
            ("Khám chuyên khoa Cơ Xương Khớp", 1, Decimal("250000.00")),
            ("Chụp X-quang khớp gối hai tư thế thẳng/nghiêng", 1, Decimal("180000.00")),
            ("Siêu âm khớp gối khảo sát tràn dịch", 1, Decimal("200000.00")),
        ],
        payment_method="CASH",
    )

    session.commit()


def main() -> None:
    try:
        with SessionLocal() as session:
            seed_database(session)
    except SQLAlchemyError as exc:
        raise SystemExit(
            f"Seed failed: {exc}. Verify SQL Server, ClinicManagementDB, credentials, and ODBC Driver 18."
        ) from None
    print("Seed completed successfully. Database populated with realistic clinical demonstration dataset.")


if __name__ == "__main__":
    main()
