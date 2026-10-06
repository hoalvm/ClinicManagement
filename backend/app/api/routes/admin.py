"""Authenticated administration reports sourced from the clinic database."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import CurrentUser, DatabaseSession
from backend.app.core.clock import clinic_today
from backend.app.core.exceptions import AuthorizationError
from backend.app.models import Appointment, Invoice, Payment
from backend.app.schemas.admin import AdminStats

router = APIRouter(prefix="/admin", tags=["Admin"])


def _count(session: Session, statement) -> int:
    return int(session.scalar(statement) or 0)


def _money(session: Session, statement) -> Decimal:
    return Decimal(session.scalar(statement) or 0).quantize(Decimal("0.01"))


def load_admin_stats(session: Session, today: date) -> AdminStats:
    """Calculate each metric from live appointments, invoices, and payments."""
    total_appointments = _count(session, select(func.count(Appointment.appointment_id)))
    completed_appointments = _count(
        session,
        select(func.count(Appointment.appointment_id)).where(Appointment.status == "COMPLETED"),
    )
    today_appointments = _count(
        session,
        select(func.count(Appointment.appointment_id)).where(
            Appointment.appointment_date == today
        ),
    )
    today_completed = _count(
        session,
        select(func.count(Appointment.appointment_id)).where(
            Appointment.appointment_date == today,
            Appointment.status == "COMPLETED",
        ),
    )
    paid_revenue = _money(
        session,
        select(func.sum(Payment.amount))
        .join(Invoice, Invoice.invoice_id == Payment.invoice_id)
        .where(Invoice.status == "PAID"),
    )
    today_collected = _money(
        session,
        select(func.sum(Payment.amount))
        .join(Invoice, Invoice.invoice_id == Payment.invoice_id)
        .where(Invoice.status == "PAID", cast(Payment.payment_date, Date) == today),
    )
    unpaid_total = _money(
        session,
        select(func.sum(Invoice.total_amount)).where(Invoice.status == "UNPAID"),
    )
    return AdminStats(
        total_appointments=total_appointments,
        completed_appointments=completed_appointments,
        paid_revenue=paid_revenue,
        today_appointments=today_appointments,
        today_completed=today_completed,
        today_collected=today_collected,
        unpaid_total=unpaid_total,
    )


@router.get("/stats", response_model=AdminStats)
def get_admin_stats(session: DatabaseSession, current_user: CurrentUser) -> AdminStats:
    if current_user.role != "ADMIN":
        raise AuthorizationError("Only administrators may view clinic statistics.")
    return load_admin_stats(session, clinic_today())
