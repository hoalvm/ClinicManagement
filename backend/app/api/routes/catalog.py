"""Public and patient catalog endpoints for specialties, doctors, and available slots."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.app.api.deps import CurrentUser, DatabaseSession, OptionalPatient
from backend.app.core.audit import record_audit_event
from backend.app.core.clock import clinic_naive_now
from backend.app.core.config import get_settings
from backend.app.core.exceptions import (
    AuthorizationError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    ValidationError,
)
from backend.app.models import Appointment, ChargeCatalog, Specialty
from backend.app.schemas.booking import (
    AvailableSlotsResponse,
    DoctorPublicItem,
    DoctorScheduleItem,
    SpecialtyItem,
)
from backend.app.schemas.reception import ChargeCatalogCreate, ChargeCatalogItem
from backend.app.services.booking_service import BookingService

router = APIRouter(prefix="/catalog", tags=["Catalog & Doctor Schedules"])


@router.get("/specialties", response_model=list[SpecialtyItem])
def list_specialties(session: DatabaseSession) -> list[SpecialtyItem]:
    return BookingService(session).list_specialties()


@router.get("/doctors", response_model=list[DoctorPublicItem])
def list_doctors(
    session: DatabaseSession,
    specialty_id: Annotated[int | None, Query(ge=1)] = None,
    appointment_date: Annotated[date | None, Query(description="Filter doctors with schedules on this date")] = None,
) -> list[DoctorPublicItem]:
    return BookingService(session).list_doctors(
        specialty_id=specialty_id,
        appointment_date=appointment_date,
    )


@router.get("/doctors/{doctor_id}/schedules", response_model=list[DoctorScheduleItem])
def get_doctor_schedules(doctor_id: int, session: DatabaseSession) -> list[DoctorScheduleItem]:
    return BookingService(session).get_doctor_schedules(doctor_id)


@router.get("/doctors/{doctor_id}/available-slots", response_model=AvailableSlotsResponse)
def get_available_slots(
    doctor_id: int,
    session: DatabaseSession,
    optional_patient: OptionalPatient,
    appointment_date: Annotated[date, Query(description="Target date in YYYY-MM-DD format")],
    exclude_appointment_id: Annotated[int | None, Query(description="Exclude appointment ID for reschedule self-conflict avoidance")] = None,
) -> AvailableSlotsResponse:
    patient_id = optional_patient.patient_id if optional_patient else None
    return BookingService(session).get_available_slots(
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        patient_id=patient_id,
        exclude_appointment_id=exclude_appointment_id,
    )


def _require_catalog_role(user: CurrentUser, *, admin: bool = False) -> None:
    roles = {"ADMIN"} if admin else {"ADMIN", "STAFF"}
    if user.role not in roles:
        raise AuthorizationError("Bạn không có quyền truy cập bảng giá.")


def _lock_specialty(session: DatabaseSession, specialty_id: int) -> None:
    bind = session.get_bind()
    if getattr(getattr(bind, "dialect", None), "name", None) == "mssql":
        session.execute(
            text(
                "SELECT SpecialtyID FROM Specialties WITH (UPDLOCK, HOLDLOCK) "
                "WHERE SpecialtyID=:specialty_id"
            ),
            {"specialty_id": specialty_id},
        ).scalar_one_or_none()


@router.get("/charges", response_model=list[ChargeCatalogItem])
def list_charges(
    session: DatabaseSession,
    current_user: CurrentUser,
    category: Annotated[str | None, Query(pattern="^(CONSULTATION|MEDICATION)$")] = None,
    specialty_id: Annotated[int | None, Query(ge=1)] = None,
    include_retired: bool = False,
) -> list[ChargeCatalogItem]:
    _require_catalog_role(current_user)
    if include_retired and current_user.role != "ADMIN":
        raise AuthorizationError("Chỉ quản trị viên được xem các phiên bản giá đã ngừng.")
    stmt = select(ChargeCatalog)
    if not include_retired:
        now = clinic_naive_now()
        stmt = stmt.where(
            ChargeCatalog.is_active,
            ChargeCatalog.effective_from <= now,
            or_(ChargeCatalog.effective_to.is_(None), ChargeCatalog.effective_to > now),
        )
    if category is not None:
        stmt = stmt.where(ChargeCatalog.category == category)
    if specialty_id is not None:
        stmt = stmt.where(ChargeCatalog.specialty_id == specialty_id)
    rows = session.scalars(stmt.order_by(ChargeCatalog.category, ChargeCatalog.display_name)).all()
    return [ChargeCatalogItem.model_validate(row) for row in rows]


@router.post("/charges", response_model=ChargeCatalogItem, status_code=201)
def create_charge(
    body: ChargeCatalogCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ChargeCatalogItem:
    _require_catalog_role(current_user, admin=True)
    if get_settings().app_mode == "production" and body.category == "MEDICATION":
        raise ValidationError(
            "Production chưa hỗ trợ danh mục thuốc hoặc cấp phát thuốc; chỉ được tạo phí khám."
        )
    if session.scalar(select(ChargeCatalog.charge_id).where(ChargeCatalog.code == body.code)):
        raise ConflictError("Mã khoản thu đã tồn tại; tạo mã phiên bản mới cho mức giá mới.")
    previous: list[ChargeCatalog] = []
    if body.category == "CONSULTATION":
        assert body.specialty_id is not None
        _lock_specialty(session, body.specialty_id)
    now = clinic_naive_now()
    if body.category == "CONSULTATION":
        specialty = session.get(Specialty, body.specialty_id)
        if specialty is None or not specialty.is_active:
            raise ValidationError("Chuyên khoa không tồn tại hoặc đã ngừng hoạt động.")
        if get_settings().app_mode == "production" and session.scalar(
            select(Appointment.appointment_id).where(
                Appointment.specialty_id == body.specialty_id,
                Appointment.status.in_(("PENDING", "CONFIRMED", "CHECKED_IN", "IN_PROGRESS")),
                or_(
                    Appointment.appointment_date > now.date(),
                    (Appointment.appointment_date == now.date())
                    & (Appointment.start_time > now.time()),
                ),
            )
        ) is not None:
            raise ConflictError(
                "Chuyên khoa còn lịch hẹn tương lai; chưa thể đổi phí khám khi chưa có "
                "quy trình báo giá và thông báo thay đổi cho bệnh nhân."
            )
        previous = session.scalars(
            select(ChargeCatalog).where(
                ChargeCatalog.category == "CONSULTATION",
                ChargeCatalog.specialty_id == body.specialty_id,
                ChargeCatalog.is_active,
            )
        ).all()
        for old in previous:
            old.is_active = False
            old.effective_to = now
    elif session.scalar(
        select(ChargeCatalog.charge_id).where(
            ChargeCatalog.category == "MEDICATION",
            func.lower(ChargeCatalog.display_name) == body.display_name.casefold(),
            ChargeCatalog.is_active,
        )
    ):
        raise ConflictError("Thuốc này đã có mức giá đang hoạt động.")
    charge = ChargeCatalog(
        code=body.code,
        display_name=body.display_name,
        category=body.category,
        specialty_id=body.specialty_id,
        unit_price=body.unit_price,
        is_active=True,
        effective_from=now,
    )
    try:
        # Free the one-active-fee key before inserting its replacement.
        if previous:
            session.flush()
        session.add(charge)
        session.flush()
        for old in previous:
            record_audit_event(
                session,
                actor_user_id=current_user.user_id,
                actor_role="ADMIN",
                action="CHARGE_RETIRED",
                entity_type="ChargeCatalog",
                entity_id=old.charge_id,
            )
        record_audit_event(
            session,
            actor_user_id=current_user.user_id,
            actor_role="ADMIN",
            action="CHARGE_CREATED",
            entity_type="ChargeCatalog",
            entity_id=charge.charge_id,
            details={"amount": body.unit_price},
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("Bảng giá bị trùng hoặc vừa được thay đổi.") from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise InternalServerError("Không thể lưu khoản thu lúc này.") from exc
    return ChargeCatalogItem.model_validate(charge)


@router.delete("/charges/{charge_id}", response_model=ChargeCatalogItem)
def retire_charge(
    charge_id: int,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ChargeCatalogItem:
    _require_catalog_role(current_user, admin=True)
    charge = session.get(ChargeCatalog, charge_id)
    if charge is None:
        raise NotFoundError("Không tìm thấy khoản thu.")
    if not charge.is_active:
        return ChargeCatalogItem.model_validate(charge)
    if charge.category == "CONSULTATION" and charge.specialty_id is not None:
        _lock_specialty(session, charge.specialty_id)
        specialty = session.get(Specialty, charge.specialty_id)
        if specialty is not None and specialty.is_active:
            raise ConflictError(
                "Không thể ngừng phí khám cuối cùng của chuyên khoa đang hoạt động; hãy tạo giá thay thế."
            )
    charge.is_active = False
    charge.effective_to = clinic_naive_now()
    try:
        record_audit_event(
            session,
            actor_user_id=current_user.user_id,
            actor_role="ADMIN",
            action="CHARGE_RETIRED",
            entity_type="ChargeCatalog",
            entity_id=charge.charge_id,
        )
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        raise InternalServerError("Không thể ngừng khoản thu lúc này.") from exc
    return ChargeCatalogItem.model_validate(charge)
