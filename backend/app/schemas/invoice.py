"""Invoice history and detail schemas."""

from datetime import date, datetime, time

from backend.app.schemas.common import APIModel, Money, Page


class InvoiceSummary(APIModel):
    invoice_id: int
    appointment_id: int
    created_at: datetime
    total_amount: Money
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
    unit_price: Money
    line_total: Money


class PaymentResponse(APIModel):
    payment_id: int
    amount: Money
    payment_method: str
    payment_date: datetime


class InvoiceDetail(APIModel):
    invoice_id: int
    appointment_id: int
    created_at: datetime
    total_amount: Money
    status: str
    appointment: InvoiceAppointment
    items: list[InvoiceItemResponse]
    payment: PaymentResponse | None = None
