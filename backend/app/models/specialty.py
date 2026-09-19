"""Mapping for the existing ``Specialties`` table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, text
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.doctor import Doctor


class Specialty(Base):
    __tablename__ = "Specialties"

    specialty_id: Mapped[int] = mapped_column("SpecialtyID", Integer, primary_key=True)
    specialty_name: Mapped[str] = mapped_column(
        "SpecialtyName", NVARCHAR(100), unique=True, nullable=False
    )
    description: Mapped[str | None] = mapped_column("Description", NVARCHAR(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, server_default=text("1")
    )

    doctors: Mapped[list[Doctor]] = relationship("Doctor", back_populates="specialty")
