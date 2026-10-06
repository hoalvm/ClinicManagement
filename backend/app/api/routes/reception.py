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
    InvoicePreview,
    PaymentRecordPage,
    ProcessPaymentRequest,
    ReceptionAppointmentItem,
    ReceptionAppointmentPage,
    ReceptionDashboardStats,
    ReceptionInvoiceItem,
    ReceptionInvoicePage,
    ReceptionPatientSummary,
    RescheduleAppointmentRequest,
    VerifiedPatientIdentity,
    VerifyPatientIdentityRequest,
)
from backend.app.services.reception_service import ReceptionService

router = APIRouter(prefix="/reception", tags=["Reception & Staff Operations"])


def require_staff(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    allowed_roles = {"STAFF"}
    if current_user.role not in allowed_roles:
        raise AuthorizationError("Yêu cầu quyền nhân viên tiếp tân.")
    return current_user


StaffUser = Annotated[User, Depends(require_staff)]


def _service(session: DatabaseSession, staff: StaffUser) -> ReceptionService:
    return ReceptionService(session, staff_user_id=staff.user_id)


@router.get("/dashboard", response_model=ReceptionDashboardStats)
def get_dashboard(
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionDashboardStats:
    return _service(session, staff).get_dashboard_stats()


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
    return _service(session, staff).list_appointments(
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=status,
        appointment_date=appointment_date,
        doctor_id=doctor_id,
    )


@router.get("/appointments/{appointment_id}", response_model=ReceptionAppointmentItem)
def get_appointment(
    appointment_id: int,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionAppointmentItem:
    return _service(session, staff).get_appointment(appointment_id)


@router.post("/appointments/{appointment_id}/confirm", response_model=ReceptionAppointmentItem)
def confirm_appointment(
    appointment_id: int,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionAppointmentItem:
    return _service(session, staff).confirm_appointment(appointment_id)


@router.post("/appointments/{appointment_id}/check-in", response_model=ReceptionAppointmentItem)
def check_in_patient(
    appointment_id: int,
    session: DatabaseSession,
    staff: StaffUser,
    body: CheckInRequest | None = None,
) -> ReceptionAppointmentItem:
    return _service(session, staff).check_in_patient(
        appointment_id,
        notes=body.notes if body else None,
    )


@router.post("/appointments/{appointment_id}/no-show", response_model=ReceptionAppointmentItem)
def mark_no_show(
    appointment_id: int,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionAppointmentItem:
    return _service(session, staff).mark_no_show(appointment_id)


@router.post("/appointments/book", response_model=ReceptionAppointmentItem)
def book_for_patient(
    body: BookForPatientRequest,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionAppointmentItem:
    return _service(session, staff).book_for_patient(body)


@router.post("/appointments/{appointment_id}/cancel", response_model=ReceptionAppointmentItem)
def cancel_appointment(
    appointment_id: int,
    body: CancelAppointmentRequest,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionAppointmentItem:
    return _service(session, staff).cancel_appointment(
        appointment_id,
        body.cancellation_reason,
        care_not_started=body.care_not_started,
    )


@router.post("/appointments/{appointment_id}/reschedule", response_model=ReceptionAppointmentItem)
def reschedule_appointment(
    appointment_id: int,
    body: RescheduleAppointmentRequest,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionAppointmentItem:
    return _service(session, staff).reschedule_appointment(
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
    return _service(session, staff).list_invoices(
        page=page,
        page_size=page_size,
        status=status,
        keyword=keyword,
    )


@router.get("/invoices/{invoice_id}", response_model=ReceptionInvoiceItem)
def get_invoice(
    invoice_id: int,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionInvoiceItem:
    return _service(session, staff).get_invoice(invoice_id)


@router.get(
    "/appointments/{appointment_id}/invoice-preview", response_model=InvoicePreview
)
def invoice_preview(
    appointment_id: int,
    session: DatabaseSession,
    staff: StaffUser,
) -> InvoicePreview:
    return _service(session, staff).invoice_preview(appointment_id)


@router.post("/invoices", response_model=ReceptionInvoiceItem)
def create_invoice(
    body: CreateInvoiceRequest,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionInvoiceItem:
    return _service(session, staff).create_invoice(body)


@router.post("/invoices/{invoice_id}/pay", response_model=ReceptionInvoiceItem)
def process_payment(
    invoice_id: int,
    body: ProcessPaymentRequest,
    session: DatabaseSession,
    staff: StaffUser,
) -> ReceptionInvoiceItem:
    return _service(session, staff).process_payment(
        invoice_id, body, recorded_by_user_id=staff.user_id
    )


@router.get("/payments", response_model=PaymentRecordPage)
def list_payments(
    session: DatabaseSession,
    staff: StaffUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    payment_method: Annotated[str | None, Query()] = None,
    keyword: Annotated[str | None, Query(max_length=200)] = None,
) -> PaymentRecordPage:
    return _service(session, staff).list_payments(
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
    return _service(session, staff).search_patients(q)


@router.post("/patients/verify-identity", response_model=VerifiedPatientIdentity)
def verify_patient_identity(
    body: VerifyPatientIdentityRequest,
    session: DatabaseSession,
    staff: StaffUser,
) -> VerifiedPatientIdentity:
    return _service(session, staff).verify_patient_identity(body)
