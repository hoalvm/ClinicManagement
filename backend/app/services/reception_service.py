"""Receptionist and Clinic Staff business logic."""

from collections import Counter
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy import func, inspect, or_, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, aliased, joinedload

from backend.app.core.audit import record_audit_event
from backend.app.core.clock import clinic_naive_now, clinic_now, clinic_today
from backend.app.core.config import get_settings
from backend.app.core.exceptions import (
    AuthorizationError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    ValidationError,
)
from backend.app.core.phone import normalize_phone
from backend.app.core.security import hash_password
from backend.app.models import (
    Appointment,
    ChargeCatalog,
    Doctor,
    Invoice,
    InvoiceItem,
    MedicalRecord,
    Patient,
    Payment,
    StaffClinicAssignment,
    User,
)
from backend.app.schemas.reception import (
    BookForPatientRequest,
    CreateInvoiceRequest,
    InvoicePreview,
    PaymentRecordItem,
    PaymentRecordPage,
    ProcessPaymentRequest,
    ReceptionAppointmentItem,
    ReceptionAppointmentPage,
    ReceptionDashboardStats,
    ReceptionInvoiceItem,
    ReceptionInvoicePage,
    ReceptionPatientSummary,
    VerifiedPatientIdentity,
    VerifyPatientIdentityRequest,
)
from backend.app.services.booking_service import BookingService


class ReceptionService:
    def __init__(self, session: Session, *, staff_user_id: int | None = None) -> None:
        self.session = session
        self.staff_user_id = staff_user_id
        self.production = get_settings().app_mode == "production"
        self.allowed_clinic_ids: frozenset[int] | None = None
        if self.production:
            if staff_user_id is None:
                raise AuthorizationError("Nhân viên cần được xác định trước khi truy cập dữ liệu cơ sở.")
            clinic_ids = self.session.scalars(
                select(StaffClinicAssignment.clinic_id).where(
                    StaffClinicAssignment.user_id == staff_user_id,
                    StaffClinicAssignment.is_active,
                )
            ).all()
            self.allowed_clinic_ids = frozenset(int(clinic_id) for clinic_id in clinic_ids)
            if not self.allowed_clinic_ids:
                raise AuthorizationError("Nhân viên chưa được phân quyền cho cơ sở khám nào.")

    def _require_clinic_access(self, clinic_id: int | None) -> None:
        if self.allowed_clinic_ids is not None and clinic_id not in self.allowed_clinic_ids:
            raise AuthorizationError("Bạn không được phân quyền thao tác tại cơ sở này.")

    def _lock_row(self, table: str, key: str, value: int) -> None:
        """Hold a SQL Server row lock through the current transaction."""

        bind = self.session.get_bind()
        if bind is not None and bind.dialect.name == "mssql":
            if (table, key) not in {
                ("Appointments", "AppointmentID"),
                ("Invoices", "InvoiceID"),
                ("Clinics", "ClinicID"),
            }:
                raise ValueError("Unexpected lock target")
            self.session.execute(
                text(f"SELECT {key} FROM {table} WITH (UPDLOCK, HOLDLOCK) WHERE {key}=:id"),
                {"id": value},
            )

    def _to_appointment_item(self, appt: Appointment) -> ReceptionAppointmentItem:
        patient = appt.patient
        patient_user = patient.user if patient else None
        doctor = appt.doctor
        doctor_user = doctor.user if doctor else None
        specialty = doctor.specialty if doctor else None
        clinic = appt.clinic

        return ReceptionAppointmentItem(
            appointment_id=appt.appointment_id,
            appointment_date=appt.appointment_date,
            start_time=appt.start_time,
            end_time=appt.end_time,
            reason=appt.reason,
            status=appt.status,
            created_at=appt.created_at,
            patient=ReceptionPatientSummary(
                patient_id=patient.patient_id if patient else 0,
                user_id=patient.user_id if patient else 0,
                full_name=patient_user.full_name
                if patient_user
                else (f"Patient #{patient.patient_id}" if patient else "Patient"),
                phone=patient_user.phone if patient_user else None,
                email=patient_user.email if patient_user else None,
                date_of_birth=patient.date_of_birth if patient else None,
                gender=patient.gender if patient else None,
                address=patient.address if patient else None,
            ),
            doctor={
                "doctor_id": doctor.doctor_id if doctor else 0,
                "full_name": doctor_user.full_name if doctor_user else "Doctor",
                "specialty": specialty.specialty_name if specialty else "General",
            },
            clinic=(
                {
                    "clinic_id": clinic.clinic_id,
                    "clinic_name": clinic.clinic_name,
                    "address": clinic.address,
                }
                if clinic
                else None
            ),
            invoice_id=appt.invoice.invoice_id if appt.invoice else None,
            queue_number=getattr(appt, "queue_number", None),
            check_in_at=getattr(appt, "check_in_at", None),
            check_in_note=getattr(appt, "check_in_note", None),
            cancellation_reason=getattr(appt, "cancellation_reason", None),
            last_reschedule_reason=getattr(appt, "last_reschedule_reason", None),
            no_show_at=getattr(appt, "no_show_at", None),
            no_show_by_user_id=getattr(appt, "no_show_by_user_id", None),
            no_show_reason_code=getattr(appt, "no_show_reason_code", None),
        )

    def get_dashboard_stats(self) -> ReceptionDashboardStats:
        now = clinic_now()
        today = now.date()

        # Appointments today query
        base_today = select(Appointment).where(Appointment.appointment_date == today)
        if self.allowed_clinic_ids is not None:
            base_today = base_today.where(Appointment.clinic_id.in_(self.allowed_clinic_ids))
        today_appts = list(self.session.execute(base_today).scalars().all())

        total_today = len(today_appts)
        pending = sum(1 for a in today_appts if a.status == "PENDING")
        confirmed = sum(1 for a in today_appts if a.status == "CONFIRMED")
        checked_in = sum(1 for a in today_appts if a.status == "CHECKED_IN")
        completed = sum(1 for a in today_appts if a.status == "COMPLETED")
        cancelled = sum(1 for a in today_appts if a.status == "CANCELLED")
        no_show = sum(1 for a in today_appts if a.status == "NO_SHOW")

        # Unpaid invoices
        unpaid_invoices_stmt = select(
            func.count(Invoice.invoice_id),
            func.coalesce(func.sum(Invoice.total_amount), 0),
        ).where(Invoice.status == "UNPAID")
        if self.allowed_clinic_ids is not None:
            unpaid_invoices_stmt = unpaid_invoices_stmt.join(Invoice.appointment).where(
                Appointment.clinic_id.in_(self.allowed_clinic_ids)
            )
        unpaid_count, unpaid_amount = self.session.execute(unpaid_invoices_stmt).one()

        # Today's collected revenue from Payments
        start_of_today = datetime.combine(today, time.min)
        end_of_today = datetime.combine(today, time.max)
        payments_today_stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.payment_date >= start_of_today, Payment.payment_date <= end_of_today
        )
        if self.allowed_clinic_ids is not None:
            payments_today_stmt = (
                payments_today_stmt.join(Payment.invoice)
                .join(Invoice.appointment)
                .where(Appointment.clinic_id.in_(self.allowed_clinic_ids))
            )
        collected_today = self.session.scalar(payments_today_stmt) or Decimal(0)

        # Recent checked in appointments today
        recent_checked_stmt = (
            select(Appointment)
            .options(
                joinedload(Appointment.patient).joinedload(Patient.user),
                joinedload(Appointment.doctor).joinedload(Doctor.user),
                joinedload(Appointment.doctor).joinedload(Doctor.specialty),
                joinedload(Appointment.clinic),
                joinedload(Appointment.invoice),
            )
            .where(Appointment.status == "CHECKED_IN")
            .where(Appointment.appointment_date == today)
            .order_by(Appointment.appointment_date.desc(), Appointment.start_time.asc())
            .limit(5)
        )
        if self.allowed_clinic_ids is not None:
            recent_checked_stmt = recent_checked_stmt.where(
                Appointment.clinic_id.in_(self.allowed_clinic_ids)
            )
        recent_checked = [
            self._to_appointment_item(a)
            for a in self.session.execute(recent_checked_stmt).unique().scalars().all()
        ]

        return ReceptionDashboardStats(
            today_total_appointments=total_today,
            today_pending_confirm=pending,
            today_confirmed=confirmed,
            today_checked_in=checked_in,
            today_completed=completed,
            today_cancelled=cancelled,
            today_no_show=no_show,
            unpaid_invoices_count=int(unpaid_count),
            unpaid_invoices_amount=Decimal(unpaid_amount),
            today_collected_amount=Decimal(collected_today),
            recent_checked_in=recent_checked,
        )

    def list_appointments(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        status: str | None = None,
        appointment_date: date | None = None,
        doctor_id: int | None = None,
        unbilled_only: bool = False,
    ) -> ReceptionAppointmentPage:
        pu = aliased(User, name="pu")
        du = aliased(User, name="du")

        base = (
            select(Appointment)
            .join(Appointment.patient)
            .join(pu, Patient.user_id == pu.user_id)
            .join(Appointment.doctor)
            .join(du, Doctor.user_id == du.user_id)
            .options(
                joinedload(Appointment.patient).joinedload(Patient.user),
                joinedload(Appointment.doctor).joinedload(Doctor.user),
                joinedload(Appointment.doctor).joinedload(Doctor.specialty),
                joinedload(Appointment.clinic),
                joinedload(Appointment.invoice),
            )
        )
        count_stmt = (
            select(func.count(Appointment.appointment_id))
            .select_from(Appointment)
            .join(Appointment.patient)
            .join(pu, Patient.user_id == pu.user_id)
            .join(Appointment.doctor)
            .join(du, Doctor.user_id == du.user_id)
        )

        if self.allowed_clinic_ids is not None:
            scope = Appointment.clinic_id.in_(self.allowed_clinic_ids)
            base = base.where(scope)
            count_stmt = count_stmt.where(scope)

        if status and status != "ALL":
            base = base.where(Appointment.status == status)
            count_stmt = count_stmt.where(Appointment.status == status)

        if unbilled_only:
            ready_to_bill = (
                (Appointment.status == "COMPLETED")
                & Appointment.medical_record.has()
                & ~Appointment.invoice.has()
            )
            base = base.where(ready_to_bill)
            count_stmt = count_stmt.where(ready_to_bill)

        if appointment_date:
            base = base.where(Appointment.appointment_date == appointment_date)
            count_stmt = count_stmt.where(Appointment.appointment_date == appointment_date)

        if doctor_id:
            base = base.where(Appointment.doctor_id == doctor_id)
            count_stmt = count_stmt.where(Appointment.doctor_id == doctor_id)

        if keyword and keyword.strip():
            raw_kw = keyword.strip()
            pat = f"%{raw_kw}%"
            normalized_phone = normalize_phone(raw_kw) or raw_kw
            normalized_phone_column = func.replace(
                func.replace(func.replace(pu.phone, " ", ""), "-", ""), ".", ""
            )
            conds = [
                pu.full_name.ilike(pat),
                pu.phone.ilike(pat),
                normalized_phone_column.ilike(f"%{normalized_phone}%"),
                du.full_name.ilike(pat),
                Appointment.reason.ilike(pat),
            ]
            clean_digits = raw_kw.lstrip("#").strip()
            if clean_digits.isdigit():
                conds.append(Appointment.appointment_id == int(clean_digits))
            filter_or = or_(*conds)
            base = base.where(filter_or)
            count_stmt = count_stmt.where(filter_or)

        total = int(self.session.scalar(count_stmt) or 0)
        total_pages = max(1, (total + page_size - 1) // page_size)

        stmt = (
            base.order_by(Appointment.appointment_date.desc(), Appointment.start_time.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        appts = self.session.execute(stmt).unique().scalars().all()

        items = [self._to_appointment_item(a) for a in appts]
        return ReceptionAppointmentPage(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    def get_appointment(self, appointment_id: int) -> ReceptionAppointmentItem:
        statement = (
            select(Appointment)
            .where(Appointment.appointment_id == appointment_id)
            .options(
                joinedload(Appointment.patient).joinedload(Patient.user),
                joinedload(Appointment.doctor).joinedload(Doctor.user),
                joinedload(Appointment.doctor).joinedload(Doctor.specialty),
                joinedload(Appointment.clinic),
                joinedload(Appointment.invoice),
            )
        )
        appt = self.session.execute(statement).unique().scalar_one_or_none()
        if appt is None:
            raise NotFoundError("Appointment not found.")
        self._require_clinic_access(appt.clinic_id)
        return self._to_appointment_item(appt)

    def confirm_appointment(self, appointment_id: int) -> ReceptionAppointmentItem:
        self._lock_row("Appointments", "AppointmentID", appointment_id)
        appt = self.session.get(Appointment, appointment_id)
        if not appt:
            raise NotFoundError("Appointment not found.")
        self._require_clinic_access(appt.clinic_id)
        if appt.status != "PENDING":
            raise ConflictError(
                f"Only pending appointments can be confirmed (current status: {appt.status})."
            )
        if appt.appointment_date < clinic_today():
            raise ConflictError("Cannot confirm an appointment from a past date.")
        if self.production and appt.appointment_date == clinic_today() and appt.end_time <= clinic_now().time().replace(tzinfo=None):
            raise ConflictError("Khung giờ khám đã kết thúc; không thể xác nhận lịch.")
        appt.status = "CONFIRMED"
        try:
            record_audit_event(
                self.session,
                actor_user_id=self.staff_user_id,
                actor_role="STAFF",
                action="APPOINTMENT_CONFIRMED",
                entity_type="Appointment",
                entity_id=appt.appointment_id,
                clinic_id=appt.clinic_id,
                details={"old_status": "PENDING", "new_status": "CONFIRMED"},
            )
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Không thể xác nhận lịch khám lúc này.") from exc
        return self._to_appointment_item(appt)

    def check_in_patient(
        self, appointment_id: int, notes: str | None = None
    ) -> ReceptionAppointmentItem:
        self._lock_row("Appointments", "AppointmentID", appointment_id)
        appt = self.session.get(Appointment, appointment_id)
        if not appt:
            raise NotFoundError("Appointment not found.")
        self._require_clinic_access(appt.clinic_id)
        if appt.status != "CONFIRMED":
            raise ConflictError(f"Cannot check in appointment with status {appt.status}.")
        if appt.appointment_date != clinic_today():
            raise ConflictError("Check-in is allowed only on the appointment date.")
        if self.production:
            cutoff = datetime.combine(appt.appointment_date, appt.end_time) + timedelta(
                minutes=get_settings().appointment_grace_minutes
            )
            if clinic_naive_now() > cutoff:
                raise ConflictError("Đã hết thời gian check-in; hãy đặt lịch khám mới.")
        if appt.clinic_id is None:
            raise ConflictError("The appointment has no clinic for queue assignment.")
        self._lock_row("Clinics", "ClinicID", appt.clinic_id)
        existing_numbers = self.session.scalars(
            select(Appointment.queue_number).where(
                Appointment.clinic_id == appt.clinic_id,
                Appointment.appointment_date == appt.appointment_date,
                Appointment.queue_number.is_not(None),
            )
        ).all()
        used = [
            int(number[2:])
            for number in existing_numbers
            if isinstance(number, str) and number.startswith("A-") and number[2:].isdigit()
        ]
        next_number = max(used, default=0) + 1
        if next_number > 99_999_999:
            raise ConflictError("Clinic queue is full for this date.")
        appt.queue_number = f"A-{next_number:03d}"
        appt.check_in_at = clinic_naive_now()
        appt.check_in_note = notes
        appt.status = "CHECKED_IN"
        try:
            record_audit_event(
                self.session,
                actor_user_id=self.staff_user_id,
                actor_role="STAFF",
                action="APPOINTMENT_CHECKED_IN",
                entity_type="Appointment",
                entity_id=appt.appointment_id,
                clinic_id=appt.clinic_id,
                details={"old_status": "CONFIRMED", "new_status": "CHECKED_IN"},
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Queue number was assigned concurrently; please retry.") from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Unable to check in this appointment.") from exc
        return self._to_appointment_item(appt)

    def mark_no_show(self, appointment_id: int) -> ReceptionAppointmentItem:
        if not self.production:
            raise ConflictError("Trạng thái vắng mặt chỉ áp dụng trong vận hành production.")
        self._lock_row("Appointments", "AppointmentID", appointment_id)
        appt = self.session.get(Appointment, appointment_id)
        if appt is None:
            raise NotFoundError("Không tìm thấy lịch khám.")
        self._require_clinic_access(appt.clinic_id)
        if appt.status != "CONFIRMED":
            raise ConflictError("Chỉ lịch đã xác nhận mới được đánh dấu bệnh nhân vắng mặt.")
        cutoff = datetime.combine(appt.appointment_date, appt.end_time) + timedelta(
            minutes=get_settings().appointment_grace_minutes
        )
        now = clinic_naive_now()
        if now <= cutoff:
            raise ConflictError("Chưa hết thời gian chờ check-in của ca khám.")
        previous_status = appt.status
        appt.status = "NO_SHOW"
        appt.no_show_at = now
        appt.no_show_by_user_id = self.staff_user_id
        appt.no_show_reason_code = "NO_ARRIVAL"
        try:
            record_audit_event(
                self.session,
                actor_user_id=self.staff_user_id,
                actor_role="STAFF",
                action="APPOINTMENT_NO_SHOW",
                entity_type="Appointment",
                entity_id=appt.appointment_id,
                clinic_id=appt.clinic_id,
                details={
                    "old_status": previous_status,
                    "new_status": "NO_SHOW",
                    "reason_code": "NO_ARRIVAL",
                },
            )
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Không thể ghi nhận bệnh nhân vắng mặt lúc này.") from exc
        return self._to_appointment_item(appt)

    def cancel_appointment(
        self, appointment_id: int, reason: str, *, care_not_started: bool = False
    ) -> ReceptionAppointmentItem:
        self._lock_row("Appointments", "AppointmentID", appointment_id)
        appt = self.session.get(Appointment, appointment_id)
        if not appt:
            raise NotFoundError("Appointment not found.")
        self._require_clinic_access(appt.clinic_id)
        if appt.status not in ("PENDING", "CONFIRMED", "CHECKED_IN"):
            raise ConflictError(f"Cannot cancel an appointment with status {appt.status}.")
        if not reason.strip() or len(reason) > 500:
            raise ValidationError("Lý do hủy phải có nội dung và không quá 500 ký tự.")
        if self.production and appt.status == "CONFIRMED":
            cutoff = datetime.combine(appt.appointment_date, appt.end_time) + timedelta(
                minutes=get_settings().appointment_grace_minutes
            )
            if clinic_naive_now() > cutoff:
                raise ConflictError(
                    "Ca đã xác nhận và quá thời gian chờ; hãy ghi nhận vắng mặt thay vì hủy."
                )
        late_check_in = (
            self.production
            and appt.status == "CHECKED_IN"
            and appt.appointment_date < clinic_today()
        )
        if self.production and appt.status == "CHECKED_IN" and appt.appointment_date > clinic_today():
            raise ConflictError("Ngày check-in của ca khám không hợp lệ.")
        if late_check_in and (not care_not_started or len(reason.strip()) < 10):
            raise ValidationError(
                "Ca check-in từ ngày trước cần xác nhận chưa được khám và lý do hủy ít nhất 10 ký tự."
            )
        previous_status = appt.status
        appt.status = "CANCELLED"
        appt.cancellation_reason = reason
        audit_details = {"old_status": previous_status, "new_status": "CANCELLED"}
        if late_check_in:
            audit_details["care_not_started"] = True
        try:
            record_audit_event(
                self.session,
                actor_user_id=self.staff_user_id,
                actor_role="STAFF",
                action=(
                    "APPOINTMENT_LATE_CHECKIN_CANCELLED"
                    if late_check_in
                    else "APPOINTMENT_CANCELLED"
                ),
                entity_type="Appointment",
                entity_id=appt.appointment_id,
                clinic_id=appt.clinic_id,
                details=audit_details,
            )
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Không thể hủy lịch khám lúc này.") from exc
        return self._to_appointment_item(appt)

    def reschedule_appointment(
        self,
        appointment_id: int,
        appointment_date: date,
        start_time: time,
        end_time: time,
        doctor_id: int | None = None,
        reason: str | None = None,
    ) -> ReceptionAppointmentItem:
        appt = self.session.get(Appointment, appointment_id)
        if not appt:
            raise NotFoundError("Appointment not found.")
        self._require_clinic_access(appt.clinic_id)
        if appt.status not in ("PENDING", "CONFIRMED"):
            raise ConflictError(f"Cannot reschedule an appointment with status {appt.status}.")
        target_doctor = self.session.get(Doctor, doctor_id or appt.doctor_id)
        if target_doctor is None:
            raise NotFoundError("Không tìm thấy bác sĩ mới.")
        self._require_clinic_access(target_doctor.clinic_id)
        def authorize_and_audit(changed: Appointment) -> None:
            # BookingService has now locked and refreshed the appointment row.
            # Its pending clinic_id change retains the refreshed source clinic
            # in SQLAlchemy history. The initial read above may have been stale
            # while a patient concurrently moved the visit to another clinic.
            clinic_history = inspect(changed).attrs.clinic_id.history
            source_clinic_id = (
                clinic_history.deleted[0]
                if clinic_history.deleted
                else changed.clinic_id
            )
            self._require_clinic_access(source_clinic_id)
            self._require_clinic_access(changed.clinic_id)
            status_history = inspect(changed).attrs.status.history
            actual_previous_status = (
                status_history.deleted[0]
                if status_history.deleted
                else changed.status
            )
            record_audit_event(
                self.session,
                actor_user_id=self.staff_user_id,
                actor_role="STAFF",
                action="APPOINTMENT_RESCHEDULED",
                entity_type="Appointment",
                entity_id=changed.appointment_id,
                clinic_id=changed.clinic_id,
                details={
                    "old_status": actual_previous_status,
                    "new_status": changed.status,
                    "doctor_id": changed.doctor_id,
                },
            )

        try:
            BookingService(self.session).reschedule_for_patient(
                appt,
                appointment_date,
                start_time,
                end_time,
                doctor_id or appt.doctor_id,
                status="CONFIRMED",
                reason=reason,
                allow_inactive_patient=True,
                before_commit=authorize_and_audit,
            )
        except AuthorizationError:
            self.session.rollback()
            raise
        return self._to_appointment_item(appt)

    def book_for_patient(self, req: BookForPatientRequest) -> ReceptionAppointmentItem:
        patient_id = req.patient_id
        if self.production and patient_id is None and req.date_of_birth is None:
            raise ValidationError("Khách vãng lai cần ngày sinh để xác minh danh tính khi quay lại.")
        if self.production and patient_id is None and not req.identity_checked:
            raise ValidationError(
                "Cần xác nhận đã kiểm tra giấy tờ và danh tính khách vãng lai tại quầy."
            )
        doctor = self.session.get(Doctor, req.doctor_id)
        if doctor is None:
            raise NotFoundError("Không tìm thấy bác sĩ.")
        self._require_clinic_access(doctor.clinic_id)
        if req.clinic_id is not None and doctor is not None and req.clinic_id != doctor.clinic_id:
            raise ValidationError("Clinic must match the selected doctor's clinic.")
        if self.production and patient_id is not None:
            if not req.identity_checked or req.date_of_birth is None:
                raise ValidationError("Cần ngày sinh và xác nhận đã kiểm tra danh tính bệnh nhân.")
            existing_patient = self.session.get(Patient, patient_id)
            if existing_patient is None or existing_patient.date_of_birth != req.date_of_birth:
                raise NotFoundError("Không tìm thấy hồ sơ khớp mã bệnh nhân và ngày sinh.")
        if patient_id is None:
            normalized_phone = normalize_phone(req.phone)
            if normalized_phone is None:
                raise ValidationError("A valid phone number is required.")
            new_user = User(
                username=f"walkin{uuid4().hex[:24]}",
                password_hash=hash_password(token_urlsafe(48)),
                full_name=req.full_name,
                phone=normalized_phone,
                role="PATIENT",
                is_active=False,
                created_at=clinic_naive_now(),
            )
            self.session.add(new_user)
            self.session.flush()
            new_patient = Patient(
                user_id=new_user.user_id,
                date_of_birth=req.date_of_birth,
                gender=req.gender,
                address=req.address,
                is_walk_in=True,
            )
            self.session.add(new_patient)
            self.session.flush()
            patient_id = new_patient.patient_id

        def audit_booking(booked: Appointment) -> None:
            if self.production and req.patient_id is not None:
                record_audit_event(
                    self.session,
                    actor_user_id=self.staff_user_id,
                    actor_role="STAFF",
                    action="PATIENT_IDENTITY_VERIFIED",
                    entity_type="Patient",
                    entity_id=req.patient_id,
                    clinic_id=booked.clinic_id,
                )
            record_audit_event(
                self.session,
                actor_user_id=self.staff_user_id,
                actor_role="STAFF",
                action="APPOINTMENT_STAFF_BOOKED",
                entity_type="Appointment",
                entity_id=booked.appointment_id,
                clinic_id=booked.clinic_id,
                details={"new_status": booked.status, "doctor_id": booked.doctor_id},
            )

        appt = BookingService(self.session).create_appointment_for_patient(
            patient_id,
            req.doctor_id,
            req.appointment_date,
            req.start_time,
            req.end_time,
            req.reason or "Khám tại quầy tiếp tân",
            status="CONFIRMED" if req.auto_confirm else "PENDING",
            allow_inactive_patient=True,
            before_commit=audit_booking,
        )
        return self._to_appointment_item(appt)

    def list_invoices(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        keyword: str | None = None,
    ) -> ReceptionInvoicePage:
        pu = aliased(User, name="pu")
        du = aliased(User, name="du")

        base = (
            select(Invoice)
            .join(Invoice.appointment)
            .join(Appointment.patient)
            .join(pu, Patient.user_id == pu.user_id)
            .join(Appointment.doctor)
            .join(du, Doctor.user_id == du.user_id)
            .options(
                joinedload(Invoice.appointment)
                .joinedload(Appointment.patient)
                .joinedload(Patient.user),
                joinedload(Invoice.appointment)
                .joinedload(Appointment.doctor)
                .joinedload(Doctor.user),
                joinedload(Invoice.payment),
            )
        )
        count_stmt = (
            select(func.count(Invoice.invoice_id))
            .select_from(Invoice)
            .join(Invoice.appointment)
            .join(Appointment.patient)
            .join(pu, Patient.user_id == pu.user_id)
            .join(Appointment.doctor)
            .join(du, Doctor.user_id == du.user_id)
        )

        if self.allowed_clinic_ids is not None:
            scope = Appointment.clinic_id.in_(self.allowed_clinic_ids)
            base = base.where(scope)
            count_stmt = count_stmt.where(scope)

        if status and status != "ALL":
            base = base.where(Invoice.status == status)
            count_stmt = count_stmt.where(Invoice.status == status)

        if keyword and keyword.strip():
            raw_kw = keyword.strip()
            pat = f"%{raw_kw}%"
            conds = [
                pu.full_name.ilike(pat),
                pu.phone.ilike(pat),
                du.full_name.ilike(pat),
            ]
            clean_digits = raw_kw.lstrip("#").upper().replace("INV-", "").replace("INV", "").strip()
            if clean_digits.isdigit():
                num_val = int(clean_digits)
                conds.append(Invoice.invoice_id == num_val)
                conds.append(Invoice.appointment_id == num_val)
            filt = or_(*conds)
            base = base.where(filt)
            count_stmt = count_stmt.where(filt)

        total = int(self.session.scalar(count_stmt) or 0)
        total_pages = max(1, (total + page_size - 1) // page_size)

        stmt = (
            base.order_by(Invoice.created_at.desc(), Invoice.invoice_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        invoices = self.session.execute(stmt).unique().scalars().all()

        items = []
        for inv in invoices:
            appt = inv.appointment
            pt_user = appt.patient.user if appt and appt.patient else None
            dr_user = appt.doctor.user if appt and appt.doctor else None
            payment = inv.payment

            items.append(
                ReceptionInvoiceItem(
                    invoice_id=inv.invoice_id,
                    appointment_id=inv.appointment_id,
                    created_at=inv.created_at,
                    total_amount=inv.total_amount,
                    status=inv.status,
                    patient_name=pt_user.full_name if pt_user else "Patient",
                    patient_phone=pt_user.phone if pt_user else None,
                    doctor_name=dr_user.full_name if dr_user else "Doctor",
                    appointment_date=appt.appointment_date if appt else date.today(),
                    payment_method=payment.payment_method if payment else None,
                    paid_at=payment.payment_date if payment else None,
                    amount_received=getattr(payment, "amount_received", None) if payment else None,
                    change_due=getattr(payment, "change_due", None) if payment else None,
                    recorded_by_user_id=getattr(payment, "recorded_by_user_id", None) if payment else None,
                    external_reference=getattr(payment, "external_reference", None) if payment else None,
                    verified_at=getattr(payment, "verified_at", None) if payment else None,
                )
            )

        return ReceptionInvoicePage(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    def get_invoice(self, invoice_id: int) -> ReceptionInvoiceItem:
        stmt = (
            select(Invoice)
            .where(Invoice.invoice_id == invoice_id)
            .options(
                joinedload(Invoice.appointment)
                .joinedload(Appointment.patient)
                .joinedload(Patient.user),
                joinedload(Invoice.appointment)
                .joinedload(Appointment.doctor)
                .joinedload(Doctor.user),
                joinedload(Invoice.payment),
            )
        )
        inv = self.session.execute(stmt).unique().scalar_one_or_none()
        if not inv:
            raise NotFoundError(f"Invoice #{invoice_id} not found.")
        appt = inv.appointment
        self._require_clinic_access(appt.clinic_id if appt else None)
        pt_user = appt.patient.user if appt and appt.patient else None
        dr_user = appt.doctor.user if appt and appt.doctor else None
        payment = inv.payment

        return ReceptionInvoiceItem(
            invoice_id=inv.invoice_id,
            appointment_id=inv.appointment_id,
            created_at=inv.created_at,
            total_amount=inv.total_amount,
            status=inv.status,
            patient_name=pt_user.full_name if pt_user else "Patient",
            patient_phone=pt_user.phone if pt_user else None,
            doctor_name=dr_user.full_name if dr_user else "Doctor",
            appointment_date=appt.appointment_date if appt else date.today(),
            payment_method=payment.payment_method if payment else None,
            paid_at=payment.payment_date if payment else None,
            amount_received=getattr(payment, "amount_received", None) if payment else None,
            change_due=getattr(payment, "change_due", None) if payment else None,
            recorded_by_user_id=getattr(payment, "recorded_by_user_id", None) if payment else None,
            external_reference=getattr(payment, "external_reference", None) if payment else None,
            verified_at=getattr(payment, "verified_at", None) if payment else None,
        )

    def _resolve_consultation_charge(self, appt: Appointment) -> ChargeCatalog:
        specialty_id = getattr(appt, "specialty_id", None)
        if specialty_id is None:
            raise ConflictError("Ca khám chưa có chuyên khoa được ghi nhận tại thời điểm đặt lịch.")
        # Price at the scheduled service time. Retiring a catalog row later must not
        # rewrite an already completed encounter's consultation price.
        service_time = datetime.combine(appt.appointment_date, appt.start_time)
        charges = self.session.scalars(
            select(ChargeCatalog).where(
                ChargeCatalog.category == "CONSULTATION",
                ChargeCatalog.specialty_id == specialty_id,
                ChargeCatalog.effective_from <= service_time,
                or_(
                    ChargeCatalog.effective_to.is_(None),
                    ChargeCatalog.effective_to > service_time,
                ),
            )
        ).all()
        if len(charges) != 1:
            raise ConflictError(
                "Chuyên khoa chưa có đúng một mức phí khám đang hiệu lực; quản trị viên cần cấu hình bảng giá."
            )
        return charges[0]

    @staticmethod
    def _record_is_complete(record: MedicalRecord | None) -> bool:
        return bool(
            record is not None
            and str(getattr(record, "symptoms", "") or "").strip()
            and str(getattr(record, "diagnosis", "") or "").strip()
        )

    def invoice_preview(self, appointment_id: int) -> InvoicePreview:
        appt = self.session.get(Appointment, appointment_id)
        if appt is None:
            raise NotFoundError("Không tìm thấy ca khám.")
        self._require_clinic_access(appt.clinic_id)
        if appt.status != "COMPLETED" or not self._record_is_complete(appt.medical_record):
            raise ConflictError("Chỉ có thể xem phí cho ca đã hoàn tất và có bệnh án.")
        if appt.invoice is not None:
            raise ConflictError("Ca khám này đã có hóa đơn.")
        charge = self._resolve_consultation_charge(appt)
        prescription = getattr(appt.medical_record, "prescription", None)
        specialty = getattr(appt.doctor, "specialty", None)
        billing_item_name = (
            f"Khám {specialty.specialty_name}"
            if specialty is not None else charge.display_name
        )
        prescribed_items = [
            {"medicine_name": item.medicine_name, "quantity": item.quantity}
            for item in (prescription.items if prescription is not None else [])
        ]
        return InvoicePreview(
            appointment_id=appt.appointment_id,
            patient_name=appt.patient.user.full_name,
            doctor_name=appt.doctor.user.full_name,
            appointment_status=appt.status,
            charge_id=charge.charge_id,
            charge_name=charge.display_name,
            billing_item_name=billing_item_name,
            unit_price=charge.unit_price,
            quantity=1,
            total_amount=charge.unit_price,
            medication_note=(
                "Thuốc trong đơn là chỉ định điều trị, chưa được giao hoặc thu tiền tại bước này."
                if self.production else
                "Chỉ thêm thuốc vào hóa đơn khi đã đối chiếu đơn và xác nhận đơn giá thực thu."
            ),
            prescribed_items=prescribed_items,
        )

    def create_invoice(self, req: CreateInvoiceRequest) -> ReceptionInvoiceItem:
        if self.production:
            return self._create_production_invoice(req)
        if not req.items or any(item.item_name is None or item.unit_price is None for item in req.items):
            raise ValidationError("Hóa đơn demo cần tên và đơn giá của từng dòng.")
        self._lock_row("Appointments", "AppointmentID", req.appointment_id)
        appt = self.session.get(Appointment, req.appointment_id)
        if not appt:
            raise NotFoundError("Appointment not found.")
        if appt.status != "COMPLETED":
            raise ConflictError("Chỉ có thể lập hóa đơn sau khi bác sĩ hoàn tất ca khám.")
        record = self.session.scalar(
            select(MedicalRecord).where(
                MedicalRecord.appointment_id == req.appointment_id
            )
        )
        if record is None:
            raise ConflictError("Ca khám phải có bệnh án trước khi lập hóa đơn.")

        existing_invoice = self.session.scalar(
            select(Invoice).where(Invoice.appointment_id == req.appointment_id)
        )
        if existing_invoice:
            raise ConflictError("Ca khám này đã có hóa đơn.")

        specialty = appt.doctor.specialty if appt.doctor else None
        if specialty is None:
            raise ConflictError("Ca khám chưa có chuyên khoa để xác định phí khám.")
        fee_names = {
            f"khám {specialty.specialty_name}".casefold(),
            f"phí khám {specialty.specialty_name}".casefold(),
        }
        prescribed = Counter()
        if record.prescription is not None:
            for medicine in record.prescription.items:
                prescribed[medicine.medicine_name.strip().casefold()] += medicine.quantity
        billed_medicines = Counter()
        fee_count = 0
        for item in req.items:
            name = item.item_name.strip().casefold()
            if name in fee_names:
                if item.quantity != 1:
                    raise ValidationError("Phí khám phải có số lượng bằng một.")
                fee_count += 1
            elif name in prescribed:
                billed_medicines[name] += item.quantity
            else:
                raise ValidationError("Dòng hóa đơn phải là phí khám hoặc thuốc đã được kê.")
        if fee_count != 1:
            raise ValidationError("Hóa đơn phải có đúng một dòng phí khám.")
        if any(quantity > prescribed[name] for name, quantity in billed_medicines.items()):
            raise ValidationError("Số lượng thuốc trên hóa đơn vượt quá đơn thuốc.")

        total_amount = sum(Decimal(item.unit_price) * Decimal(item.quantity) for item in req.items)
        if total_amount <= 0 or total_amount > Decimal("9999999999999999.99"):
            raise ValidationError("Tổng hóa đơn vượt phạm vi số tiền cho phép.")

        new_invoice = Invoice(
            appointment_id=req.appointment_id,
            total_amount=total_amount,
            status="UNPAID",
            created_at=clinic_naive_now(),
        )
        try:
            self.session.add(new_invoice)
            self.session.flush()
            for item in req.items:
                self.session.add(
                    InvoiceItem(
                        invoice_id=new_invoice.invoice_id,
                        item_name=item.item_name,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                    )
                )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Ca khám này đã có hóa đơn.") from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Không thể lập hóa đơn lúc này.") from exc

        # Reload for response
        pt_user = appt.patient.user if appt.patient else None
        dr_user = appt.doctor.user if appt.doctor else None

        return ReceptionInvoiceItem(
            invoice_id=new_invoice.invoice_id,
            appointment_id=new_invoice.appointment_id,
            created_at=new_invoice.created_at,
            total_amount=new_invoice.total_amount,
            status=new_invoice.status,
            patient_name=pt_user.full_name if pt_user else "Patient",
            patient_phone=pt_user.phone if pt_user else None,
            doctor_name=dr_user.full_name if dr_user else "Doctor",
            appointment_date=appt.appointment_date,
        )

    def _create_production_invoice(self, req: CreateInvoiceRequest) -> ReceptionInvoiceItem:
        if req.items is not None:
            raise ValidationError(
                "Hóa đơn production được tính từ bảng giá trên server; không nhận giá hoặc dòng phí từ client."
            )
        self._lock_row("Appointments", "AppointmentID", req.appointment_id)
        appt = self.session.get(Appointment, req.appointment_id)
        if appt is None:
            raise NotFoundError("Không tìm thấy ca khám.")
        self._require_clinic_access(appt.clinic_id)
        if appt.status != "COMPLETED":
            raise ConflictError("Chỉ lập hóa đơn khi bác sĩ đã hoàn tất ca khám.")
        record = self.session.scalar(
            select(MedicalRecord).where(MedicalRecord.appointment_id == req.appointment_id)
        )
        if not self._record_is_complete(record):
            raise ConflictError("Ca khám cần bệnh án có triệu chứng và chẩn đoán trước khi lập hóa đơn.")
        if self.session.scalar(
            select(Invoice.invoice_id).where(Invoice.appointment_id == req.appointment_id)
        ) is not None:
            raise ConflictError("Ca khám này đã có hóa đơn.")
        charge = self._resolve_consultation_charge(appt)
        price = Decimal(charge.unit_price)
        if price <= 0 or price > Decimal("9999999999999999.99"):
            raise ConflictError("Mức phí khám trên bảng giá không hợp lệ.")
        invoice = Invoice(
            appointment_id=appt.appointment_id,
            total_amount=price,
            status="UNPAID",
            created_at=clinic_naive_now(),
        )
        try:
            self.session.add(invoice)
            self.session.flush()
            self.session.add(
                InvoiceItem(
                    invoice_id=invoice.invoice_id,
                    charge_id=charge.charge_id,
                    item_name=charge.display_name,
                    quantity=1,
                    unit_price=price,
                )
            )
            record_audit_event(
                self.session,
                actor_user_id=self.staff_user_id,
                actor_role="STAFF",
                action="INVOICE_CREATED",
                entity_type="Invoice",
                entity_id=invoice.invoice_id,
                clinic_id=appt.clinic_id,
                details={"amount": price},
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Ca khám này đã có hóa đơn hoặc bảng giá đã thay đổi.") from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Không thể lập hóa đơn lúc này.") from exc
        return ReceptionInvoiceItem(
            invoice_id=invoice.invoice_id,
            appointment_id=invoice.appointment_id,
            created_at=invoice.created_at,
            total_amount=invoice.total_amount,
            status=invoice.status,
            patient_name=appt.patient.user.full_name,
            patient_phone=appt.patient.user.phone,
            doctor_name=appt.doctor.user.full_name,
            appointment_date=appt.appointment_date,
        )

    def process_payment(
        self,
        invoice_id: int,
        req: ProcessPaymentRequest,
        *,
        recorded_by_user_id: int | None = None,
    ) -> ReceptionInvoiceItem:
        if self.production and (
            recorded_by_user_id is None or recorded_by_user_id != self.staff_user_id
        ):
            raise AuthorizationError("Không xác định được nhân viên xác nhận thanh toán.")
        self._lock_row("Invoices", "InvoiceID", invoice_id)
        invoice = self.session.get(Invoice, invoice_id)
        if not invoice:
            raise NotFoundError("Không tìm thấy hóa đơn.")
        self._require_clinic_access(invoice.appointment.clinic_id)
        if invoice.status != "UNPAID":
            raise ConflictError("Chỉ có thể thu tiền cho hóa đơn chưa thanh toán.")
        if self.session.scalar(select(Payment.payment_id).where(Payment.invoice_id == invoice_id)):
            raise ConflictError("Hóa đơn này đã có giao dịch thanh toán.")
        total = Decimal(invoice.total_amount)
        tendered = Decimal(req.amount)
        if req.payment_method == "CASH":
            if tendered < total:
                raise ValidationError("Tiền khách đưa chưa đủ tổng hóa đơn.")
        elif req.payment_method == "TRANSFER":
            if tendered != total:
                raise ValidationError("Số tiền chuyển khoản phải bằng tổng hóa đơn.")
        else:
            raise ValidationError("Phương thức thanh toán không được hỗ trợ.")

        if self.production:
            if req.payment_method == "TRANSFER":
                if not req.manual_verified or not req.external_reference:
                    raise ValidationError(
                        "Chuyển khoản cần mã giao dịch ngoài hệ thống và xác nhận đã đối chiếu thủ công."
                    )
                if self.session.scalar(
                    select(Payment.payment_id).where(
                        Payment.payment_method == "TRANSFER",
                        Payment.external_reference == req.external_reference,
                    )
                ) is not None:
                    raise ConflictError("Mã giao dịch chuyển khoản đã được dùng cho hóa đơn khác.")
            elif req.external_reference is not None or req.manual_verified:
                raise ValidationError("Thanh toán tiền mặt không nhận mã giao dịch chuyển khoản.")

        payment = Payment(
            invoice_id=invoice_id,
            amount=total,
            payment_method=req.payment_method,
            payment_date=clinic_naive_now(),
            amount_received=tendered,
            change_due=tendered - total if req.payment_method == "CASH" else Decimal("0.00"),
            recorded_by_user_id=recorded_by_user_id,
            external_reference=req.external_reference if self.production else None,
            verified_at=clinic_naive_now()
            if self.production and req.payment_method == "TRANSFER"
            else None,
        )
        try:
            self.session.add(payment)
            invoice.status = "PAID"
            record_audit_event(
                self.session,
                actor_user_id=recorded_by_user_id,
                actor_role="STAFF",
                action="PAYMENT_RECORDED",
                entity_type="Invoice",
                entity_id=invoice_id,
                clinic_id=invoice.appointment.clinic_id,
                details={
                    "old_status": "UNPAID",
                    "new_status": "PAID",
                    "payment_method": req.payment_method,
                    "amount": total,
                    "amount_received": tendered,
                    "change_due": payment.change_due,
                },
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Hóa đơn này đã được thanh toán.") from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Không thể ghi nhận thanh toán lúc này.") from exc

        appt = invoice.appointment
        pt_user = appt.patient.user if appt and appt.patient else None
        dr_user = appt.doctor.user if appt and appt.doctor else None

        return ReceptionInvoiceItem(
            invoice_id=invoice.invoice_id,
            appointment_id=invoice.appointment_id,
            created_at=invoice.created_at,
            total_amount=invoice.total_amount,
            status=invoice.status,
            patient_name=pt_user.full_name if pt_user else "Patient",
            patient_phone=pt_user.phone if pt_user else None,
            doctor_name=dr_user.full_name if dr_user else "Doctor",
            appointment_date=appt.appointment_date if appt else date.today(),
            payment_method=payment.payment_method,
            paid_at=payment.payment_date,
            amount_received=payment.amount_received,
            change_due=payment.change_due,
            recorded_by_user_id=payment.recorded_by_user_id,
            external_reference=payment.external_reference,
            verified_at=payment.verified_at,
        )

    def list_payments(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        payment_method: str | None = None,
        keyword: str | None = None,
    ) -> PaymentRecordPage:
        pu = aliased(User, name="pu")
        du = aliased(User, name="du")

        base = (
            select(Payment)
            .join(Payment.invoice)
            .join(Invoice.appointment)
            .join(Appointment.patient)
            .join(pu, Patient.user_id == pu.user_id)
            .join(Appointment.doctor)
            .join(du, Doctor.user_id == du.user_id)
            .options(
                joinedload(Payment.invoice)
                .joinedload(Invoice.appointment)
                .joinedload(Appointment.patient)
                .joinedload(Patient.user),
                joinedload(Payment.invoice)
                .joinedload(Invoice.appointment)
                .joinedload(Appointment.doctor)
                .joinedload(Doctor.user),
            )
        )
        count_stmt = (
            select(func.count(Payment.payment_id))
            .select_from(Payment)
            .join(Payment.invoice)
            .join(Invoice.appointment)
            .join(Appointment.patient)
            .join(pu, Patient.user_id == pu.user_id)
            .join(Appointment.doctor)
            .join(du, Doctor.user_id == du.user_id)
        )

        if self.allowed_clinic_ids is not None:
            scope = Appointment.clinic_id.in_(self.allowed_clinic_ids)
            base = base.where(scope)
            count_stmt = count_stmt.where(scope)

        if payment_method and payment_method != "ALL":
            base = base.where(Payment.payment_method == payment_method)
            count_stmt = count_stmt.where(Payment.payment_method == payment_method)

        if keyword and keyword.strip():
            raw_kw = keyword.strip()
            pat = f"%{raw_kw}%"
            conds = [
                pu.full_name.ilike(pat),
                pu.phone.ilike(pat),
                du.full_name.ilike(pat),
            ]
            clean_digits = (
                raw_kw.lstrip("#")
                .upper()
                .replace("INV-", "")
                .replace("INV", "")
                .replace("PAY-", "")
                .strip()
            )
            if clean_digits.isdigit():
                num_val = int(clean_digits)
                conds.append(Payment.payment_id == num_val)
                conds.append(Invoice.invoice_id == num_val)
            filt = or_(*conds)
            base = base.where(filt)
            count_stmt = count_stmt.where(filt)

        total = int(self.session.scalar(count_stmt) or 0)
        total_pages = max(1, (total + page_size - 1) // page_size)

        stmt = (
            base.order_by(Payment.payment_date.desc(), Payment.payment_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        payments = self.session.execute(stmt).unique().scalars().all()

        items = []
        for p in payments:
            inv = p.invoice
            appt = inv.appointment if inv else None
            pt_user = appt.patient.user if appt and appt.patient else None
            dr_user = appt.doctor.user if appt and appt.doctor else None

            items.append(
                PaymentRecordItem(
                    payment_id=p.payment_id,
                    invoice_id=p.invoice_id,
                    amount=p.amount,
                    payment_method=p.payment_method,
                    payment_date=p.payment_date,
                    patient_name=pt_user.full_name if pt_user else "Patient",
                    patient_phone=pt_user.phone if pt_user else None,
                    doctor_name=dr_user.full_name if dr_user else "Doctor",
                    total_invoice_amount=inv.total_amount if inv else p.amount,
                    amount_received=getattr(p, "amount_received", None),
                    change_due=getattr(p, "change_due", None),
                    recorded_by_user_id=getattr(p, "recorded_by_user_id", None),
                    external_reference=getattr(p, "external_reference", None),
                    verified_at=getattr(p, "verified_at", None),
                )
            )

        return PaymentRecordPage(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    def search_patients(self, query: str) -> list[ReceptionPatientSummary]:
        if not query or len(query.strip()) < 2:
            return []
        raw_query = query.strip()
        pat = f"%{raw_query}%"
        normalized_phone = normalize_phone(raw_query) or raw_query
        normalized_phone_column = func.replace(
            func.replace(func.replace(User.phone, " ", ""), "-", ""), ".", ""
        )
        conditions = [
            User.full_name.ilike(pat),
            User.phone.ilike(pat),
            normalized_phone_column.ilike(f"%{normalized_phone}%"),
            User.email.ilike(pat),
        ]
        patient_code = raw_query.upper().removeprefix("PT-").lstrip("#")
        if patient_code.isdigit():
            conditions.extend(
                (Patient.patient_id == int(patient_code), User.user_id == int(patient_code))
            )
        stmt = (
            select(Patient)
            .join(Patient.user)
            .options(joinedload(Patient.user))
            .where(or_(*conditions))
            .limit(10)
        )
        if self.allowed_clinic_ids is not None:
            stmt = stmt.where(
                Patient.appointments.any(
                    Appointment.clinic_id.in_(self.allowed_clinic_ids)
                )
            )
        patients = self.session.execute(stmt).unique().scalars().all()
        return [
            ReceptionPatientSummary(
                patient_id=p.patient_id,
                user_id=p.user_id,
                full_name=p.user.full_name,
                phone=p.user.phone,
                email=p.user.email,
                date_of_birth=p.date_of_birth,
                gender=p.gender,
                address=p.address,
            )
            for p in patients
        ]

    def verify_patient_identity(
        self, request: VerifyPatientIdentityRequest
    ) -> VerifiedPatientIdentity:
        """Allow a cross-clinic lookup only after exact identity verification."""

        if not self.production:
            raise ConflictError("Tra cứu liên cơ sở chỉ áp dụng trong vận hành production.")
        self._require_clinic_access(request.clinic_id)
        if not request.identity_checked:
            raise ValidationError("Nhân viên phải xác nhận đã kiểm tra giấy tờ của bệnh nhân.")
        patient = self.session.get(Patient, request.patient_id)
        verified = (
            patient is not None
            and patient.date_of_birth == request.date_of_birth
            and patient.user is not None
            and patient.user.role == "PATIENT"
            and (patient.user.is_active or patient.is_walk_in)
        )
        try:
            record_audit_event(
                self.session,
                actor_user_id=self.staff_user_id,
                actor_role="STAFF",
                action="PATIENT_IDENTITY_LOOKUP",
                entity_type="Patient",
                entity_id=request.patient_id,
                clinic_id=request.clinic_id,
                outcome="SUCCESS" if verified else "DENIED",
            )
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Không thể ghi nhận lần xác minh danh tính.") from exc
        if not verified:
            raise NotFoundError("Không tìm thấy hồ sơ khớp mã bệnh nhân và ngày sinh.")
        assert patient is not None and patient.date_of_birth is not None
        return VerifiedPatientIdentity(
            patient_id=patient.patient_id,
            full_name=patient.user.full_name,
            date_of_birth=patient.date_of_birth,
        )
