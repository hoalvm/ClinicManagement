"""Mapping for the existing ``Payments`` table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, text
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.invoice import Invoice


class Payment(Base):
    __tablename__ = "Payments"

    payment_id: Mapped[int] = mapped_column("PaymentID", Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        "InvoiceID", ForeignKey("Invoices.InvoiceID"), unique=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column("Amount", Numeric(18, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column("PaymentMethod", String(20), nullable=False)
    payment_date: Mapped[datetime] = mapped_column(
        "PaymentDate", DATETIME2, nullable=False, server_default=text("GETDATE()")
    )

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="payment")
