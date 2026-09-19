"""Mapping for the existing ``Users`` table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String, text
from sqlalchemy.dialects.mssql import DATETIME2
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.doctor import Doctor
    from backend.app.models.patient import Patient


class User(Base):
    __tablename__ = "Users"

    user_id: Mapped[int] = mapped_column("UserID", Integer, primary_key=True)
    username: Mapped[str] = mapped_column("Username", String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column("PasswordHash", String(255), nullable=False)
    full_name: Mapped[str] = mapped_column("FullName", String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column("Phone", String(15), nullable=True)
    email: Mapped[str | None] = mapped_column("Email", String(100), nullable=True)
    role: Mapped[str] = mapped_column("Role", String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DATETIME2, nullable=False, server_default=text("GETDATE()")
    )

    patient: Mapped[Patient | None] = relationship("Patient", back_populates="user", uselist=False)
    doctor: Mapped[Doctor | None] = relationship("Doctor", back_populates="user", uselist=False)
