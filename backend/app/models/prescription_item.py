"""Mapping for the existing ``PrescriptionItems`` table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.prescription import Prescription


class PrescriptionItem(Base):
    __tablename__ = "PrescriptionItems"

    prescription_item_id: Mapped[int] = mapped_column(
        "PrescriptionItemID", Integer, primary_key=True
    )
    prescription_id: Mapped[int] = mapped_column(
        "PrescriptionID", ForeignKey("Prescriptions.PrescriptionID"), nullable=False
    )
    medicine_name: Mapped[str] = mapped_column("MedicineName", NVARCHAR(150), nullable=False)
    quantity: Mapped[int] = mapped_column("Quantity", Integer, nullable=False)
    dosage: Mapped[str | None] = mapped_column("Dosage", NVARCHAR(255), nullable=True)
    instructions: Mapped[str | None] = mapped_column("Instructions", NVARCHAR(500), nullable=True)

    prescription: Mapped[Prescription] = relationship("Prescription", back_populates="items")
