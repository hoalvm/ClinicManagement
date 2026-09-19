"""Ownership-scoped invoice queries."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from backend.app.models import Appointment, Doctor, Invoice


class InvoiceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_patient(
        self,
        patient_id: int,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> tuple[list[Invoice], int]:
        base = select(Invoice).join(Invoice.appointment).where(Appointment.patient_id == patient_id)
        count_statement = (
            select(func.count(Invoice.invoice_id))
            .join(Invoice.appointment)
            .where(Appointment.patient_id == patient_id)
        )
        if status:
            base = base.where(Invoice.status == status)
            count_statement = count_statement.where(Invoice.status == status)
        total = int(self.session.scalar(count_statement) or 0)
        statement = (
            base.order_by(Invoice.created_at.desc(), Invoice.invoice_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        invoices = list(self.session.execute(statement).scalars().all())
        return invoices, total

    def get_owned(self, invoice_id: int, patient_id: int) -> Invoice | None:
        statement = (
            select(Invoice)
            .join(Invoice.appointment)
            .options(
                joinedload(Invoice.appointment)
                .joinedload(Appointment.doctor)
                .joinedload(Doctor.user),
                joinedload(Invoice.items),
                joinedload(Invoice.payment),
            )
            .where(
                Invoice.invoice_id == invoice_id,
                Appointment.patient_id == patient_id,
            )
        )
        return self.session.execute(statement).unique().scalar_one_or_none()

    def count_for_patient(self, patient_id: int, *, status: str | None = None) -> int:
        statement = (
            select(func.count(Invoice.invoice_id))
            .join(Invoice.appointment)
            .where(Appointment.patient_id == patient_id)
        )
        if status:
            statement = statement.where(Invoice.status == status)
        return int(self.session.scalar(statement) or 0)
