"""Current patient's read-only invoice endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.api.deps import CurrentPatient, DatabaseSession
from backend.app.schemas.common import InvoiceStatus
from backend.app.schemas.invoice import InvoiceDetail, InvoicePage
from backend.app.services import InvoiceService

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("/me", response_model=InvoicePage)
def list_invoices(
    current_patient: CurrentPatient,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    status: InvoiceStatus | None = None,
) -> InvoicePage:
    return InvoiceService(session).list_invoices(
        current_patient.patient_id,
        page=page,
        page_size=page_size,
        status=status.value if status is not None else None,
    )


@router.get("/me/{invoice_id}", response_model=InvoiceDetail)
def get_invoice_detail(
    invoice_id: int,
    current_patient: CurrentPatient,
    session: DatabaseSession,
) -> InvoiceDetail:
    return InvoiceService(session).get_detail(invoice_id, current_patient.patient_id)
