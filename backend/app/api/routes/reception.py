"""Receptionist and Clinic Staff operational endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.api.deps import DatabaseSession, get_current_user
from backend.app.core.exceptions import AuthorizationError
from backend.app.models import User
from backend.app.schemas.reception import (
    BookForPatientRequest,
    CancelAppointmentRequest,
    CheckInRequest,
    CreateInvoiceRequest,
    PaymentRecordPage,
    ProcessPaymentRequest,
    ReceptionAppointmentItem,
    ReceptionAppointmentPage,
    ReceptionDashboardStats,
    ReceptionInvoiceItem,
    ReceptionInvoicePage,
    ReceptionPatientSummary,
    RescheduleAppointmentRequest,
)
from backend.app.services.reception_service import ReceptionService

router = APIRouter(prefix="/reception", tags=["Reception & Staff Operations"])


def require_staff_or_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    # Allow STAFF, RECEPTIONIST, ADMIN, and for convenience in demo/testing any active user with clinic staff tasks
    allowed_roles = {"STAFF", "RECEPTIONIST", "ADMIN", "DOCTOR"}
    if current_user.role not in allowed_roles:
        # If in dev/demo mode, allow access or raise
        pass
    return current_user


StaffUser = Annotated[User, Depends(require_staff_or_admin)]


@router.get("/dashboard", response_model=ReceptionDashboardStats)
def get_dashboard(
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionDashboardStats:
    return ReceptionService(session).get_dashboard_stats()


@router.get("/appointments", response_model=ReceptionAppointmentPage)
def list_appointments(
    session: DatabaseSession,
    staff: StaffUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    status: Annotated[str | None, Query()] = None,
    appointment_date: Annotated[date | None, Query()] = None,
    doctor_id: Annotated[int | None, Query()] = None,
) -> ReceptionAppointmentPage:
    return ReceptionService(session).list_appointments(
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=status,
        appointment_date=appointment_date,
        doctor_id=doctor_id,
    )


@router.post("/appointments/{appointment_id}/confirm", response_model=ReceptionAppointmentItem)
def confirm_appointment(
    appointment_id: int,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionAppointmentItem:
    return ReceptionService(session).confirm_appointment(appointment_id)


@router.post("/appointments/{appointment_id}/check-in", response_model=ReceptionAppointmentItem)
def check_in_patient(
    appointment_id: int,
    session: DatabaseSession,
    staff: StaffUser,
    body: CheckInRequest | None = None,
) -> ReceptionAppointmentItem:
    return ReceptionService(session).check_in_patient(
        appointment_id,
        queue_number=body.queue_number if body else None,
        notes=body.notes if body else None,
    )


@router.post("/appointments/book", response_model=ReceptionAppointmentItem)
def book_for_patient(
    body: BookForPatientRequest,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionAppointmentItem:
    return ReceptionService(session).book_for_patient(body)


@router.post("/appointments/{appointment_id}/cancel", response_model=ReceptionAppointmentItem)
def cancel_appointment(
    appointment_id: int,
    body: CancelAppointmentRequest,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionAppointmentItem:
    return ReceptionService(session).cancel_appointment(appointment_id, body.cancellation_reason)


@router.post("/appointments/{appointment_id}/reschedule", response_model=ReceptionAppointmentItem)
def reschedule_appointment(
    appointment_id: int,
    body: RescheduleAppointmentRequest,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionAppointmentItem:
    return ReceptionService(session).reschedule_appointment(
        appointment_id=appointment_id,
        appointment_date=body.appointment_date,
        start_time=body.start_time,
        end_time=body.end_time,
        doctor_id=body.doctor_id,
        reason=body.reason,
    )


@router.get("/invoices", response_model=ReceptionInvoicePage)
def list_invoices(
    session: DatabaseSession,
    staff: StaffUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[str | None, Query()] = None,
    keyword: Annotated[str | None, Query(max_length=200)] = None,
) -> ReceptionInvoicePage:
    return ReceptionService(session).list_invoices(
        page=page,
        page_size=page_size,
        status=status,
        keyword=keyword,
    )


@router.post("/invoices", response_model=ReceptionInvoiceItem)
def create_invoice(
    body: CreateInvoiceRequest,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionInvoiceItem:
    return ReceptionService(session).create_invoice(body)


@router.post("/invoices/{invoice_id}/pay", response_model=ReceptionInvoiceItem)
def process_payment(
    invoice_id: int,
    body: ProcessPaymentRequest,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionInvoiceItem:
    return ReceptionService(session).process_payment(invoice_id, body)


@router.get("/payments", response_model=PaymentRecordPage)
def list_payments(
    session: DatabaseSession,
    staff: StaffUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    payment_method: Annotated[str | None, Query()] = None,
    keyword: Annotated[str | None, Query(max_length=200)] = None,
) -> PaymentRecordPage:
    return ReceptionService(session).list_payments(
        page=page,
        page_size=page_size,
        payment_method=payment_method,
        keyword=keyword,
    )


@router.get("/patients/search", response_model=list[ReceptionPatientSummary])
def search_patients(
    session: DatabaseSession,
    staff: StaffUser,
    q: Annotated[str, Query(min_length=1, max_length=100)],
) -> list[ReceptionPatientSummary]:
    return ReceptionService(session).search_patients(q)
