"""Invoice history and detail schemas."""

from datetime import date, datetime, time
from decimal import Decimal

from backend.app.schemas.common import APIModel, Page


class InvoiceSummary(APIModel):
    invoice_id: int
    appointment_id: int
    created_at: datetime
    total_amount: Decimal
    status: str


class InvoicePage(Page[InvoiceSummary]):
    """Paginated invoice history response."""


class InvoiceDoctor(APIModel):
    doctor_id: int
    full_name: str


class InvoiceAppointment(APIModel):
    appointment_date: date
    start_time: time
    doctor: InvoiceDoctor


class InvoiceItemResponse(APIModel):
    item_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class PaymentResponse(APIModel):
    payment_id: int
    amount: Decimal
    payment_method: str
    payment_date: datetime


class InvoiceDetail(APIModel):
    invoice_id: int
    appointment_id: int
    created_at: datetime
    total_amount: Decimal
    status: str
    appointment: InvoiceAppointment
    items: list[InvoiceItemResponse]
    payment: PaymentResponse | None = None
