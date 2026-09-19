"""Mapping for the existing ``Invoices`` table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, text
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.appointment import Appointment
    from backend.app.models.invoice_item import InvoiceItem
    from backend.app.models.payment import Payment


class Invoice(Base):
    __tablename__ = "Invoices"

    invoice_id: Mapped[int] = mapped_column("InvoiceID", Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        "AppointmentID",
        ForeignKey("Appointments.AppointmentID"),
        unique=True,
        nullable=False,
    )
    total_amount: Mapped[Decimal] = mapped_column(
        "TotalAmount", Numeric(18, 2), nullable=False, server_default=text("0")
    )
    status: Mapped[str] = mapped_column(
        "Status", String(20), nullable=False, server_default=text("'UNPAID'")
    )
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DATETIME2, nullable=False, server_default=text("GETDATE()")
    )

    appointment: Mapped[Appointment] = relationship("Appointment", back_populates="invoice")
    items: Mapped[list[InvoiceItem]] = relationship(
        "InvoiceItem", back_populates="invoice", order_by="InvoiceItem.invoice_item_id"
    )
    payment: Mapped[Payment | None] = relationship(
        "Payment", back_populates="invoice", uselist=False
    )
