"""Receptionist and Clinic Staff business logic."""

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from backend.app.core.clock import clinic_now
from backend.app.core.exceptions import ConflictError, NotFoundError, ValidationError
from backend.app.models import (
    Appointment,
    Doctor,
    Invoice,
    InvoiceItem,
    Patient,
    Payment,
    User,
)
from backend.app.schemas.reception import (
    BookForPatientRequest,
    CreateInvoiceRequest,
    PaymentRecordItem,
    PaymentRecordPage,
    ProcessPaymentRequest,
    ReceptionAppointmentItem,
    ReceptionAppointmentPage,
    ReceptionDashboardStats,
    ReceptionInvoiceItem,
    ReceptionInvoicePage,
    ReceptionPatientSummary,
)


class ReceptionService:
    def __init__(self, session: Session) -> None:
        self.session = session

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
                patient_id=patient.patient_id,
                user_id=patient.user_id,
                full_name=patient_user.full_name if patient_user else f"Patient #{patient.patient_id}",
                phone=patient_user.phone if patient_user else None,
                email=patient_user.email if patient_user else None,
                date_of_birth=patient.date_of_birth,
                gender=patient.gender,
                address=patient.address,
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
        )

    def get_dashboard_stats(self) -> ReceptionDashboardStats:
        now = clinic_now()
        today = now.date()

        # Appointments today query
        base_today = select(Appointment).where(Appointment.appointment_date == today)
        today_appts = list(self.session.execute(base_today).scalars().all())

        total_today = len(today_appts)
        pending = sum(1 for a in today_appts if a.status == "PENDING")
        confirmed = sum(1 for a in today_appts if a.status == "CONFIRMED")
        checked_in = sum(1 for a in today_appts if a.status == "CHECKED_IN")
        completed = sum(1 for a in today_appts if a.status == "COMPLETED")
        cancelled = sum(1 for a in today_appts if a.status == "CANCELLED")

        # Unpaid invoices
        unpaid_invoices_stmt = select(
            func.count(Invoice.invoice_id),
            func.coalesce(func.sum(Invoice.total_amount), 0),
        ).where(Invoice.status == "UNPAID")
        unpaid_count, unpaid_amount = self.session.execute(unpaid_invoices_stmt).one()

        # Today's collected revenue from Payments
        start_of_today = datetime.combine(today, time.min)
        end_of_today = datetime.combine(today, time.max)
        payments_today_stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.payment_date >= start_of_today, Payment.payment_date <= end_of_today
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
            .order_by(Appointment.appointment_date.desc(), Appointment.start_time.asc())
            .limit(5)
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
    ) -> ReceptionAppointmentPage:
        base = (
            select(Appointment)
            .join(Appointment.patient)
            .join(Patient.user)
            .join(Appointment.doctor)
            .join(Doctor.user)
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
            .join(Patient.user)
            .join(Appointment.doctor)
            .join(Doctor.user)
        )

        if status and status != "ALL":
            base = base.where(Appointment.status == status)
            count_stmt = count_stmt.where(Appointment.status == status)

        if appointment_date:
            base = base.where(Appointment.appointment_date == appointment_date)
            count_stmt = count_stmt.where(Appointment.appointment_date == appointment_date)

        if doctor_id:
            base = base.where(Appointment.doctor_id == doctor_id)
            count_stmt = count_stmt.where(Appointment.doctor_id == doctor_id)

        if keyword and keyword.strip():
            raw_kw = keyword.strip()
            pat = f"%{raw_kw}%"
            conds = [
                User.full_name.ilike(pat),
                User.phone.ilike(pat),
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

    def confirm_appointment(self, appointment_id: int) -> ReceptionAppointmentItem:
        appt = self.session.get(Appointment, appointment_id)
        if not appt:
            raise NotFoundError("Appointment not found.")
        if appt.status == "CANCELLED":
            raise ConflictError("Cannot confirm a cancelled appointment.")
        appt.status = "CONFIRMED"
        self.session.commit()
        return self._to_appointment_item(appt)

    def check_in_patient(
        self, appointment_id: int, queue_number: str | None = None, notes: str | None = None
    ) -> ReceptionAppointmentItem:
        appt = self.session.get(Appointment, appointment_id)
        if not appt:
            raise NotFoundError("Appointment not found.")
        if appt.status in ("COMPLETED", "CANCELLED"):
            raise ConflictError(f"Cannot check in appointment with status {appt.status}.")
        appt.status = "CHECKED_IN"
        if notes:
            appt.reason = f"{appt.reason or ''} [Check-in note: {notes}]".strip()
        self.session.commit()
        return self._to_appointment_item(appt)

    def cancel_appointment(self, appointment_id: int, reason: str) -> ReceptionAppointmentItem:
        appt = self.session.get(Appointment, appointment_id)
        if not appt:
            raise NotFoundError("Appointment not found.")
        if appt.status == "COMPLETED":
            raise ConflictError("Cannot cancel an already completed appointment.")
        appt.status = "CANCELLED"
        appt.reason = f"{appt.reason or ''} [Cancelled: {reason}]".strip()
        self.session.commit()
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
        if appt.status in ("COMPLETED", "CANCELLED"):
            raise ConflictError(f"Cannot reschedule an appointment with status {appt.status}.")
        appt.appointment_date = appointment_date
        appt.start_time = start_time
        appt.end_time = end_time
        if doctor_id:
            appt.doctor_id = doctor_id
        if reason:
            appt.reason = reason
        appt.status = "CONFIRMED"
        self.session.commit()
        return self._to_appointment_item(appt)

    def book_for_patient(self, req: BookForPatientRequest) -> ReceptionAppointmentItem:
        patient_id = req.patient_id

        # If patient_id not supplied, locate or create a new user & patient record
        if not patient_id:
            if not req.full_name or not req.phone:
                raise ValidationError("Full name and phone number are required for walk-in patient booking.")
            
            # Check if user already exists with this phone
            existing_user = self.session.scalar(select(User).where(User.phone == req.phone))
            if existing_user and existing_user.patient:
                patient_id = existing_user.patient.patient_id
            else:
                # Create user & patient
                username = f"pt_{req.phone.replace('+', '')[-8:]}_{int(datetime.now().timestamp()) % 10000}"
                new_user = User(
                    username=username,
                    password_hash="argon2id$v=19$m=65536,t=3,p=4$defaultwalkin$placeholder",
                    full_name=req.full_name,
                    phone=req.phone,
                    role="PATIENT",
                    is_active=True,
                )
                self.session.add(new_user)
                self.session.flush()

                new_patient = Patient(
                    user_id=new_user.user_id,
                    date_of_birth=req.date_of_birth,
                    gender=req.gender or "OTHER",
                    address=req.address or "",
                )
                self.session.add(new_patient)
                self.session.flush()
                patient_id = new_patient.patient_id

        # Verify doctor exists
        doctor = self.session.get(Doctor, req.doctor_id)
        if not doctor:
            raise NotFoundError("Doctor not found.")

        clinic_id = req.clinic_id or doctor.clinic_id

        status = "CONFIRMED" if req.auto_confirm else "PENDING"
        appt = Appointment(
            patient_id=patient_id,
            doctor_id=req.doctor_id,
            clinic_id=clinic_id,
            appointment_date=req.appointment_date,
            start_time=req.start_time,
            end_time=req.end_time,
            reason=req.reason or "Walk-in registration via Reception desk",
            status=status,
        )
        self.session.add(appt)
        self.session.commit()
        return self._to_appointment_item(appt)

    def list_invoices(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        keyword: str | None = None,
    ) -> ReceptionInvoicePage:
        base = (
            select(Invoice)
            .join(Invoice.appointment)
            .join(Appointment.patient)
            .join(Patient.user)
            .join(Appointment.doctor)
            .join(Doctor.user)
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
            .join(Patient.user)
            .join(Appointment.doctor)
            .join(Doctor.user)
        )

        if status and status != "ALL":
            base = base.where(Invoice.status == status)
            count_stmt = count_stmt.where(Invoice.status == status)

        if keyword and keyword.strip():
            raw_kw = keyword.strip()
            pat = f"%{raw_kw}%"
            conds = [
                User.full_name.ilike(pat),
                User.phone.ilike(pat),
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
                joinedload(Invoice.appointment).joinedload(Appointment.patient).joinedload(Patient.user),
                joinedload(Invoice.appointment).joinedload(Appointment.doctor).joinedload(Doctor.user),
                joinedload(Invoice.payment),
            )
        )
        inv = self.session.execute(stmt).unique().scalar_one_or_none()
        if not inv:
            raise NotFoundError(f"Invoice #{invoice_id} not found.")
        appt = inv.appointment
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
        )

    def create_invoice(self, req: CreateInvoiceRequest) -> ReceptionInvoiceItem:
        appt = self.session.get(Appointment, req.appointment_id)
        if not appt:
            raise NotFoundError("Appointment not found.")

        # Check if invoice already exists
        existing_invoice = self.session.scalar(
            select(Invoice).where(Invoice.appointment_id == req.appointment_id)
        )
        if existing_invoice:
            raise ConflictError("An invoice already exists for this appointment.")

        total_amount = sum(
            Decimal(item.unit_price) * Decimal(item.quantity) for item in req.items
        )

        new_invoice = Invoice(
            appointment_id=req.appointment_id,
            total_amount=total_amount,
            status="UNPAID",
        )
        self.session.add(new_invoice)
        self.session.flush()

        for item in req.items:
            invoice_item = InvoiceItem(
                invoice_id=new_invoice.invoice_id,
                item_name=item.item_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            self.session.add(invoice_item)

        # Mark appointment completed if it was in-progress or checked in
        if appt.status in ("CHECKED_IN", "IN_PROGRESS"):
            appt.status = "COMPLETED"

        self.session.commit()

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

    def process_payment(self, invoice_id: int, req: ProcessPaymentRequest) -> ReceptionInvoiceItem:
        invoice = self.session.get(Invoice, invoice_id)
        if not invoice:
            raise NotFoundError("Invoice not found.")
        if invoice.status == "PAID":
            raise ConflictError("This invoice has already been paid.")

        # Create payment
        payment = Payment(
            invoice_id=invoice_id,
            amount=req.amount,
            payment_method=req.payment_method,
            payment_date=clinic_now(),
        )
        self.session.add(payment)
        invoice.status = "PAID"
        self.session.commit()

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
        )

    def list_payments(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        payment_method: str | None = None,
        keyword: str | None = None,
    ) -> PaymentRecordPage:
        base = (
            select(Payment)
            .join(Payment.invoice)
            .join(Invoice.appointment)
            .join(Appointment.patient)
            .join(Patient.user)
            .join(Appointment.doctor)
            .join(Doctor.user)
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
            .join(Patient.user)
        )

        if payment_method and payment_method != "ALL":
            base = base.where(Payment.payment_method == payment_method)
            count_stmt = count_stmt.where(Payment.payment_method == payment_method)

        if keyword and keyword.strip():
            raw_kw = keyword.strip()
            pat = f"%{raw_kw}%"
            conds = [
                User.full_name.ilike(pat),
                User.phone.ilike(pat),
            ]
            clean_digits = raw_kw.lstrip("#").upper().replace("INV-", "").replace("INV", "").replace("PAY-", "").strip()
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
        pat = f"%{query.strip()}%"
        stmt = (
            select(Patient)
            .join(Patient.user)
            .options(joinedload(Patient.user))
            .where(
                or_(
                    User.full_name.ilike(pat),
                    User.phone.ilike(pat),
                    User.email.ilike(pat),
                )
            )
            .limit(10)
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
