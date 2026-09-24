"""Schemas for Receptionist and Clinic Staff workflows."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

from backend.app.schemas.common import APIModel, AppointmentStatus, InvoiceStatus, Money, Page


class ReceptionPatientSummary(APIModel):
    patient_id: int
    user_id: int
    full_name: str
    phone: str | None = None
    email: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    address: str | None = None


class ReceptionAppointmentItem(APIModel):
    appointment_id: int
    appointment_date: date
    start_time: time
    end_time: time
    reason: str | None = None
    status: str
    created_at: datetime
    patient: ReceptionPatientSummary
    doctor: dict
    clinic: dict | None = None
    invoice_id: int | None = None


class ReceptionAppointmentPage(Page[ReceptionAppointmentItem]):
    """Paginated appointments for reception view."""


class ConfirmAppointmentRequest(APIModel):
    note: str | None = None


class CheckInRequest(APIModel):
    queue_number: str | None = None
    notes: str | None = None


class CancelAppointmentRequest(APIModel):
    cancellation_reason: str = Field(min_length=3, max_length=500)


class RescheduleAppointmentRequest(APIModel):
    appointment_date: date
    start_time: time
    end_time: time
    doctor_id: int | None = None
    reason: str | None = None


class BookForPatientRequest(APIModel):
    # Either existing patient_id or new patient info
    patient_id: int | None = None
    full_name: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    address: str | None = None

    doctor_id: int
    clinic_id: int | None = None
    appointment_date: date
    start_time: time
    end_time: time
    reason: str | None = None
    auto_confirm: bool = True


class InvoiceItemCreate(APIModel):
    item_name: str = Field(min_length=1, max_length=200)
    quantity: int = Field(ge=1, default=1)
    unit_price: Decimal = Field(ge=0)


class CreateInvoiceRequest(APIModel):
    appointment_id: int
    items: list[InvoiceItemCreate] = Field(min_length=1)


class ReceptionInvoiceItem(APIModel):
    invoice_id: int
    appointment_id: int
    created_at: datetime
    total_amount: Money
    status: str
    patient_name: str
    patient_phone: str | None = None
    doctor_name: str
    appointment_date: date
    payment_method: str | None = None
    paid_at: datetime | None = None


class ReceptionInvoicePage(Page[ReceptionInvoiceItem]):
    """Paginated reception invoice list."""


class ProcessPaymentRequest(APIModel):
    payment_method: str = Field(pattern="^(CASH|CARD)$")
    amount: Decimal = Field(gt=0)
    notes: str | None = None


class PaymentRecordItem(APIModel):
    payment_id: int
    invoice_id: int
    amount: Money
    payment_method: str
    payment_date: datetime
    patient_name: str
    patient_phone: str | None = None
    doctor_name: str
    total_invoice_amount: Money


class PaymentRecordPage(Page[PaymentRecordItem]):
    """Paginated payment transactions history."""


class ReceptionDashboardStats(APIModel):
    today_total_appointments: int
    today_pending_confirm: int
    today_confirmed: int
    today_checked_in: int
    today_completed: int
    today_cancelled: int
    unpaid_invoices_count: int
    unpaid_invoices_amount: Money
    today_collected_amount: Money
    recent_checked_in: list[ReceptionAppointmentItem]
