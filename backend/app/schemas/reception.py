"""Schemas for Receptionist and Clinic Staff workflows."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from backend.app.core.clock import clinic_today
from backend.app.schemas.common import APIModel, Money, Page


class ReceptionPatientSummary(APIModel):
    patient_id: int
    user_id: int
    full_name: str
    phone: str | None = None
    email: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    address: str | None = None


class VerifyPatientIdentityRequest(APIModel):
    patient_id: int = Field(ge=1)
    date_of_birth: date
    clinic_id: int = Field(ge=1)
    identity_checked: bool = Field(strict=True)

    @field_validator("date_of_birth")
    @classmethod
    def birth_date_not_future(cls, value: date) -> date:
        if value > clinic_today():
            raise ValueError("Date of birth cannot be in the future")
        return value


class VerifiedPatientIdentity(APIModel):
    patient_id: int
    full_name: str
    date_of_birth: date


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
    queue_number: str | None = None
    check_in_at: datetime | None = None
    check_in_note: str | None = None
    cancellation_reason: str | None = None
    last_reschedule_reason: str | None = None
    no_show_at: datetime | None = None
    no_show_by_user_id: int | None = None
    no_show_reason_code: str | None = None


class ReceptionAppointmentPage(Page[ReceptionAppointmentItem]):
    """Paginated appointments for reception view."""


class ConfirmAppointmentRequest(APIModel):
    note: str | None = None


class CheckInRequest(APIModel):
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("notes")
    @classmethod
    def nonblank_note(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Check-in note cannot be blank")
        return value


class CancelAppointmentRequest(APIModel):
    cancellation_reason: str = Field(min_length=3, max_length=500)
    care_not_started: bool = False


class RescheduleAppointmentRequest(APIModel):
    appointment_date: date
    start_time: time
    end_time: time
    doctor_id: int | None = Field(default=None, ge=1)
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Reschedule reason cannot be blank")
        return value

    @model_validator(mode="after")
    def check_interval(self) -> "RescheduleAppointmentRequest":
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be earlier than end time")
        return self


class BookForPatientRequest(APIModel):
    # Either existing patient_id or new patient info
    patient_id: int | None = Field(default=None, ge=1)
    full_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=15)
    date_of_birth: date | None = None
    gender: Literal["MALE", "FEMALE", "OTHER"] | None = None
    address: str | None = Field(default=None, max_length=255)
    identity_checked: bool = Field(default=False, strict=True)

    doctor_id: int = Field(ge=1)
    clinic_id: int | None = Field(default=None, ge=1)
    appointment_date: date
    start_time: time
    end_time: time
    reason: str | None = Field(default=None, max_length=500)
    auto_confirm: bool = True

    @field_validator("full_name", "address", "reason")
    @classmethod
    def nonblank_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("A provided text field cannot be blank")
        return value

    @field_validator("date_of_birth")
    @classmethod
    def birth_date_not_future(cls, value: date | None) -> date | None:
        if value is not None and value > clinic_today():
            raise ValueError("Date of birth cannot be in the future")
        return value

    @model_validator(mode="after")
    def check_patient_and_interval(self) -> "BookForPatientRequest":
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be earlier than end time")
        if self.patient_id is None and (not self.full_name or not self.phone):
            raise ValueError("Full name and phone are required for a walk-in patient")
        return self


class InvoiceItemCreate(APIModel):
    # Production invoices reference a configured charge. The legacy fields are
    # accepted only by the demo workflow and are never trusted in production.
    charge_id: int | None = Field(default=None, ge=1)
    item_name: str | None = Field(default=None, min_length=1, max_length=200)
    quantity: int = Field(ge=1, le=1_000_000, default=1)
    unit_price: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)

    @field_validator("item_name")
    @classmethod
    def nonblank_item_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Invoice item name cannot be blank")
        return value


class CreateInvoiceRequest(APIModel):
    appointment_id: int = Field(ge=1)
    # Production generates its consultation line from ChargeCatalog. The demo
    # workflow still accepts manually entered line items.
    items: list[InvoiceItemCreate] | None = Field(default=None, min_length=1, max_length=100)


class ReceptionInvoiceLine(APIModel):
    item_name: str
    quantity: int
    unit_price: Money
    line_total: Money


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
    clinic_name: str | None = None
    clinic_address: str | None = None
    items: list[ReceptionInvoiceLine] = Field(default_factory=list)
    payment_id: int | None = None
    payment_method: str | None = None
    paid_at: datetime | None = None
    amount_received: Money | None = None
    change_due: Money | None = None
    recorded_by_user_id: int | None = None
    external_reference: str | None = None
    verified_at: datetime | None = None


class ReceptionInvoicePage(Page[ReceptionInvoiceItem]):
    """Paginated reception invoice list."""


class InvoicePreview(APIModel):
    appointment_id: int
    patient_name: str
    doctor_name: str
    appointment_status: str
    charge_id: int
    charge_name: str
    billing_item_name: str
    unit_price: Money
    quantity: int
    total_amount: Money
    medication_note: str
    prescribed_items: list[dict[str, str | int]] = Field(default_factory=list)


class ProcessPaymentRequest(APIModel):
    payment_method: Literal["CASH", "TRANSFER"]
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    external_reference: str | None = Field(default=None, min_length=6, max_length=100)
    manual_verified: bool = False

    @field_validator("external_reference")
    @classmethod
    def nonblank_reference(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("External transaction reference cannot be blank")
        return value


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
    amount_received: Money | None = None
    change_due: Money | None = None
    recorded_by_user_id: int | None = None
    external_reference: str | None = None
    verified_at: datetime | None = None


class ChargeCatalogCreate(APIModel):
    code: str = Field(min_length=2, max_length=50, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    display_name: str = Field(min_length=1, max_length=200)
    category: Literal["CONSULTATION", "MEDICATION"]
    specialty_id: int | None = Field(default=None, ge=1)
    unit_price: Decimal = Field(gt=0, max_digits=18, decimal_places=2)

    @model_validator(mode="after")
    def validate_specialty(self) -> "ChargeCatalogCreate":
        if self.category == "CONSULTATION" and self.specialty_id is None:
            raise ValueError("Consultation charge requires a specialty")
        if self.category == "MEDICATION" and self.specialty_id is not None:
            raise ValueError("Medication charge cannot be tied to a specialty")
        return self


class ChargeCatalogItem(APIModel):
    charge_id: int
    code: str
    display_name: str
    category: Literal["CONSULTATION", "MEDICATION"]
    specialty_id: int | None = None
    unit_price: Money
    is_active: bool
    effective_from: datetime
    effective_to: datetime | None = None


class PaymentRecordPage(Page[PaymentRecordItem]):
    """Paginated payment transactions history."""


class ReceptionDashboardStats(APIModel):
    today_total_appointments: int
    today_pending_confirm: int
    today_confirmed: int
    today_checked_in: int
    today_completed: int
    today_cancelled: int
    today_no_show: int = 0
    unpaid_invoices_count: int
    unpaid_invoices_amount: Money
    today_collected_amount: Money
    recent_checked_in: list[ReceptionAppointmentItem]
