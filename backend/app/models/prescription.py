"""Mapping for the existing ``Prescriptions`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, text
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.medical_record import MedicalRecord
    from backend.app.models.prescription_item import PrescriptionItem


class Prescription(Base):
    __tablename__ = "Prescriptions"

    prescription_id: Mapped[int] = mapped_column("PrescriptionID", Integer, primary_key=True)
    medical_record_id: Mapped[int] = mapped_column(
        "MedicalRecordID",
        ForeignKey("MedicalRecords.MedicalRecordID"),
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DATETIME2, nullable=False, server_default=text("GETDATE()")
    )

    medical_record: Mapped[MedicalRecord] = relationship(
        "MedicalRecord", back_populates="prescription"
    )
    items: Mapped[list[PrescriptionItem]] = relationship(
        "PrescriptionItem",
        back_populates="prescription",
        order_by="PrescriptionItem.prescription_item_id",
    )
