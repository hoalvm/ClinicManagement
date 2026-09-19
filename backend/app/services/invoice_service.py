"""Invoice history and detail business logic."""

from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.repositories import InvoiceRepository
from backend.app.schemas.invoice import (
    InvoiceAppointment,
    InvoiceDetail,
    InvoiceDoctor,
    InvoiceItemResponse,
    InvoicePage,
    InvoiceSummary,
    PaymentResponse,
)


class InvoiceService:
    def __init__(self, session: Session) -> None:
        self.repository = InvoiceRepository(session)

    def list_invoices(
        self,
        patient_id: int,
        *,
        page: int,
        page_size: int,
        status: str | None,
    ) -> InvoicePage:
        invoices, total = self.repository.list_for_patient(
            patient_id, page=page, page_size=page_size, status=status
        )
        return InvoicePage(
            items=[
                InvoiceSummary(
                    invoice_id=invoice.invoice_id,
                    appointment_id=invoice.appointment_id,
                    created_at=invoice.created_at,
                    total_amount=invoice.total_amount,
                    status=invoice.status,
                )
                for invoice in invoices
            ],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
        )

    def get_detail(self, invoice_id: int, patient_id: int) -> InvoiceDetail:
        invoice = self.repository.get_owned(invoice_id, patient_id)
        if invoice is None:
            raise NotFoundError("Invoice not found.")
        appointment = invoice.appointment
        doctor = appointment.doctor
        payment = invoice.payment
        return InvoiceDetail(
            invoice_id=invoice.invoice_id,
            appointment_id=invoice.appointment_id,
            created_at=invoice.created_at,
            total_amount=invoice.total_amount,
            status=invoice.status,
            appointment=InvoiceAppointment(
                appointment_date=appointment.appointment_date,
                start_time=appointment.start_time,
                doctor=InvoiceDoctor(
                    doctor_id=doctor.doctor_id,
                    full_name=doctor.user.full_name,
                ),
            ),
            items=[
                InvoiceItemResponse(
                    item_name=item.item_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.unit_price * item.quantity,
                )
                for item in invoice.items
            ],
            payment=(
                PaymentResponse(
                    payment_id=payment.payment_id,
                    amount=payment.amount,
                    payment_method=payment.payment_method,
                    payment_date=payment.payment_date,
                )
                if payment is not None
                else None
            ),
        )
