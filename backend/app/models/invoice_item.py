"""Mapping for the existing ``InvoiceItems`` table."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.invoice import Invoice


class InvoiceItem(Base):
    __tablename__ = "InvoiceItems"

    invoice_item_id: Mapped[int] = mapped_column("InvoiceItemID", Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        "InvoiceID", ForeignKey("Invoices.InvoiceID"), nullable=False
    )
    item_name: Mapped[str] = mapped_column("ItemName", String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(
        "Quantity", Integer, nullable=False, server_default=text("1")
    )
    unit_price: Mapped[Decimal] = mapped_column("UnitPrice", Numeric(18, 2), nullable=False)

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="items")
