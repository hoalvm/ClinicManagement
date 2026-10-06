"""Immutable charge definitions used to price production invoices on the server."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, text
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.invoice_item import InvoiceItem


class ChargeCatalog(Base):
    __tablename__ = "ChargeCatalog"

    charge_id: Mapped[int] = mapped_column("ChargeID", Integer, primary_key=True)
    code: Mapped[str] = mapped_column("Code", NVARCHAR(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column("DisplayName", NVARCHAR(200), nullable=False)
    category: Mapped[str] = mapped_column("Category", NVARCHAR(20), nullable=False)
    specialty_id: Mapped[int | None] = mapped_column(
        "SpecialtyID", ForeignKey("Specialties.SpecialtyID"), nullable=True
    )
    unit_price: Mapped[Decimal] = mapped_column("UnitPrice", Numeric(18, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, server_default=text("1")
    )
    effective_from: Mapped[datetime] = mapped_column(
        "EffectiveFrom", DATETIME2, nullable=False, server_default=text("GETDATE()")
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        "EffectiveTo", DATETIME2, nullable=True
    )

    invoice_items: Mapped[list[InvoiceItem]] = relationship(
        "InvoiceItem", back_populates="charge"
    )
