"""Business logic for patient booking, available time slots, and schedule changes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time, timedelta

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.audit import record_audit_event
from backend.app.core.clock import clinic_now
from backend.app.core.config import get_settings
from backend.app.core.exceptions import (
    ConflictError,
    InternalServerError,
    NotFoundError,
    ValidationError,
)
from backend.app.models import Appointment, ChargeCatalog, Doctor, Patient, Specialty
from backend.app.models.doctor_schedule_exception import DoctorScheduleException
from backend.app.repositories.appointment_repository import AppointmentRepository
from backend.app.repositories.doctor_repository import DoctorRepository
from backend.app.schemas.appointment import AppointmentDetail
from backend.app.schemas.booking import (
    AppointmentCancelRequest,
    AppointmentCreateRequest,
    AppointmentRescheduleRequest,
    AvailableSlotsResponse,
    DoctorPublicItem,
    DoctorScheduleItem,
    SpecialtyItem,
    TimeSlot,
)
from backend.app.services.appointment_service import AppointmentService


def _overlap(start1: time, end1: time, start2: time, end2: time) -> bool:
    """Check if two time intervals overlap (strictly greater than zero duration)."""
    return max(start1, start2) < min(end1, end2)


def _add_minutes(t: time, minutes: int) -> time:
    temp_dt = datetime.combine(date.today(), t) + timedelta(minutes=minutes)
    return temp_dt.time()


def _active_appointments(appointments: list[Appointment]) -> list[Appointment]:
    """Defensively exclude cancelled rows from every availability calculation."""

    return [
        appointment
        for appointment in appointments
        if str(getattr(appointment, "status", "")).upper() not in {"CANCELLED", "NO_SHOW"}
    ]


class BookingService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.doctor_repo = DoctorRepository(session)
        self.appointment_repo = AppointmentRepository(session)
        self.appointment_service = AppointmentService(session)

    def _consultation_charges_for_day(
        self, specialty_id: int, appointment_date: date
    ) -> list[ChargeCatalog]:
        """Read fee versions that can cover at least one slot on this date."""

        day_start = datetime.combine(appointment_date, time.min)
        day_end = datetime.combine(appointment_date, time.max)
        return self.session.scalars(
            select(ChargeCatalog).where(
                ChargeCatalog.category == "CONSULTATION",
                ChargeCatalog.specialty_id == specialty_id,
                ChargeCatalog.effective_from <= day_end,
                or_(
                    ChargeCatalog.effective_to.is_(None),
                    ChargeCatalog.effective_to > day_start,
                ),
            )
        ).all()

    @staticmethod
    def _has_one_valid_charge(
        charges: list[ChargeCatalog], appointment_date: date, start_time: time
    ) -> bool:
        service_time = datetime.combine(appointment_date, start_time)
        effective = [
            charge
            for charge in charges
            if charge.effective_from <= service_time
            and (charge.effective_to is None or charge.effective_to > service_time)
        ]
        return len(effective) == 1 and effective[0].unit_price > 0

    def _audit_patient_change(
        self,
        appointment: Appointment,
        action: str,
        *,
        old_status: str | None = None,
        new_status: str | None = None,
    ) -> None:
        patient = self.session.get(Patient, appointment.patient_id)
        if patient is None:
            raise InternalServerError("Không tìm thấy chủ hồ sơ lịch khám.")
        details = {}
        if old_status is not None:
            details["old_status"] = old_status
        if new_status is not None:
            details["new_status"] = new_status
        record_audit_event(
            self.session,
            actor_user_id=patient.user_id,
            actor_role="PATIENT",
            action=action,
            entity_type="Appointment",
            entity_id=appointment.appointment_id,
            clinic_id=appointment.clinic_id,
            details=details,
        )

    def _schedule_exceptions(
        self, doctor_id: int, appointment_date: date
    ) -> list[DoctorScheduleException]:
        if get_settings().app_mode != "production":
            return []
        return list(
            self.session.scalars(
                select(DoctorScheduleException).where(
                    DoctorScheduleException.doctor_id == doctor_id,
                    DoctorScheduleException.exception_date == appointment_date,
                    DoctorScheduleException.is_active.is_(True),
                )
            ).all()
        )

    @staticmethod
    def _blocked_by_exception(
        start_time: time, end_time: time, exceptions: list[DoctorScheduleException]
    ) -> bool:
        return any(
            exception.start_time is None
            or _overlap(start_time, end_time, exception.start_time, exception.end_time)
            for exception in exceptions
        )

    def list_specialties(self) -> list[SpecialtyItem]:
        records = self.doctor_repo.list_specialties()
        return [
            SpecialtyItem(
                specialty_id=spec.specialty_id,
                specialty_name=spec.specialty_name,
                description=spec.description,
                doctor_count=count,
            )
            for spec, count in records
        ]

    def list_doctors(
        self,
        specialty_id: int | None = None,
        appointment_date: date | None = None,
    ) -> list[DoctorPublicItem]:
        day_of_week = appointment_date.isoweekday() if appointment_date else None
        doctors = self.doctor_repo.list_doctors(specialty_id, day_of_week=day_of_week)
        return [
            DoctorPublicItem(
                doctor_id=doc.doctor_id,
                full_name=doc.user.full_name,
                specialty_id=doc.specialty_id,
                specialty_name=doc.specialty.specialty_name,
                clinic_id=doc.clinic_id,
                clinic_name=doc.clinic.clinic_name if doc.clinic else None,
                clinic_address=doc.clinic.address if doc.clinic else None,
                license_number=doc.license_number,
                phone=doc.user.phone,
                email=doc.user.email,
            )
            for doc in doctors
        ]

    def get_doctor_schedules(self, doctor_id: int) -> list[DoctorScheduleItem]:
        schedules = self.doctor_repo.get_schedules(doctor_id)
        return [
            DoctorScheduleItem(
                schedule_id=s.schedule_id,
                doctor_id=s.doctor_id,
                day_of_week=s.day_of_week,
                start_time=s.start_time,
                end_time=s.end_time,
                slot_duration=s.slot_duration,
            )
            for s in schedules
        ]

    def get_available_slots(
        self,
        doctor_id: int,
        appointment_date: date,
        patient_id: int | None = None,
        exclude_appointment_id: int | None = None,
    ) -> AvailableSlotsResponse:
        doctor = self.doctor_repo.get_doctor_by_id(doctor_id)
        if not doctor:
            raise NotFoundError("Bác sĩ không tồn tại hoặc đã ngừng hoạt động.")

        day_of_week = appointment_date.isoweekday()
        schedules = self.doctor_repo.get_schedules(doctor_id, day_of_week=day_of_week)
        exceptions = self._schedule_exceptions(doctor_id, appointment_date)
        charges = (
            self._consultation_charges_for_day(doctor.specialty_id, appointment_date)
            if get_settings().app_mode == "production"
            else None
        )

        if not schedules:
            return AvailableSlotsResponse(
                doctor_id=doctor.doctor_id,
                doctor_name=doctor.user.full_name,
                specialty_name=doctor.specialty.specialty_name,
                clinic_name=doctor.clinic.clinic_name if doctor.clinic else None,
                appointment_date=appointment_date,
                day_of_week=day_of_week,
                has_schedule=False,
                slots=[],
            )

        # Existing doctor appointments on this date (excluding current rescheduled appointment if any)
        doctor_appointments = self.appointment_repo.get_active_appointments_for_doctor(
            doctor_id, appointment_date
        )
        doctor_appointments = _active_appointments(doctor_appointments)
        if exclude_appointment_id:
            doctor_appointments = [
                a
                for a in doctor_appointments
                if getattr(a, "appointment_id", None) != exclude_appointment_id
            ]

        # Existing patient appointments on this date (excluding current rescheduled appointment if any)
        patient_appointments = (
            self.appointment_repo.get_active_appointments_for_patient(patient_id, appointment_date)
            if patient_id
            else []
        )
        patient_appointments = _active_appointments(patient_appointments)
        if exclude_appointment_id:
            patient_appointments = [
                a
                for a in patient_appointments
                if getattr(a, "appointment_id", None) != exclude_appointment_id
            ]

        # Existing patient active appointments for anti-spam checks (excluding current rescheduled appointment)
        active_patient_appts = (
            self.appointment_repo.get_active_appointments_for_patient_all(patient_id)
            if patient_id and hasattr(self.appointment_repo, "get_active_appointments_for_patient_all")
            else []
        )
        active_patient_appts = _active_appointments(active_patient_appts)
        if exclude_appointment_id:
            active_patient_appts = [
                a
                for a in active_patient_appts
                if getattr(a, "appointment_id", None) != exclude_appointment_id
            ]
        has_active_same_specialty = any(
            getattr(a, "appointment_date", None) == appointment_date
            and (
                getattr(a, "specialty_id", None)
                or getattr(getattr(a, "doctor", None), "specialty_id", None)
            ) == doctor.specialty_id
            for a in active_patient_appts
        )

        now = clinic_now()
        today = now.date()
        now_time = now.time().replace(tzinfo=None)
        is_past_date = appointment_date < today
        is_today = appointment_date == today

        slots: list[TimeSlot] = []

        for schedule in schedules:
            curr = schedule.start_time
            step = schedule.slot_duration or 30

            while True:
                next_t = _add_minutes(curr, step)
                if next_t > schedule.end_time or next_t <= curr:
                    break

                slot_start, slot_end = curr, next_t

                if is_past_date:
                    slots.append(
                        TimeSlot(
                            start_time=slot_start,
                            end_time=slot_end,
                            is_available=False,
                            reason="Ngày khám trong quá khứ",
                        )
                    )
                elif is_today and slot_start <= now_time:
                    slots.append(
                        TimeSlot(
                            start_time=slot_start,
                            end_time=slot_end,
                            is_available=False,
                            reason="Khung giờ đã qua",
                        )
                    )
                elif charges is not None and not self._has_one_valid_charge(
                    charges, appointment_date, slot_start
                ):
                    slots.append(
                        TimeSlot(
                            start_time=slot_start,
                            end_time=slot_end,
                            is_available=False,
                            reason="Chuyên khoa chưa có một phí khám hợp lệ cho khung giờ này",
                        )
                    )
                elif self._blocked_by_exception(slot_start, slot_end, exceptions):
                    slots.append(
                        TimeSlot(
                            start_time=slot_start,
                            end_time=slot_end,
                            is_available=False,
                            reason="Bác sĩ nghỉ hoặc ca trực đã được đóng trong thời gian này",
                        )
                    )
                elif has_active_same_specialty:
                    slots.append(
                        TimeSlot(
                            start_time=slot_start,
                            end_time=slot_end,
                            is_available=False,
                            reason="Bạn đang có lịch hẹn chưa khám thuộc chuyên khoa này",
                        )
                    )
                elif any(
                    _overlap(slot_start, slot_end, appt.start_time, appt.end_time)
                    for appt in doctor_appointments
                ):
                    slots.append(
                        TimeSlot(
                            start_time=slot_start,
                            end_time=slot_end,
                            is_available=False,
                            reason="Bác sĩ đã có lịch hẹn",
                        )
                    )
                elif any(
                    _overlap(slot_start, slot_end, appt.start_time, appt.end_time)
                    for appt in patient_appointments
                ):
                    slots.append(
                        TimeSlot(
                            start_time=slot_start,
                            end_time=slot_end,
                            is_available=False,
                            reason="Bạn đã có lịch khám khác trong giờ này",
                        )
                    )
                else:
                    slots.append(
                        TimeSlot(
                            start_time=slot_start,
                            end_time=slot_end,
                            is_available=True,
                            reason=None,
                        )
                    )

                curr = next_t

        return AvailableSlotsResponse(
            doctor_id=doctor.doctor_id,
            doctor_name=doctor.user.full_name,
            specialty_name=doctor.specialty.specialty_name,
            clinic_name=doctor.clinic.clinic_name if doctor.clinic else None,
            appointment_date=appointment_date,
            day_of_week=day_of_week,
            has_schedule=True,
            slots=slots,
        )

    def _lock_booking_resources(self, patient_id: int, doctor_id: int) -> None:
        """Serialize booking changes that share a patient or doctor on SQL Server.

        Locks are taken in the same order for every booking and reschedule.
        HOLDLOCK protects the conflict recheck until the subsequent commit.
        """
        bind = self.session.get_bind()
        if getattr(getattr(bind, "dialect", None), "name", None) != "mssql":
            return
        for model, key in ((Patient, patient_id), (Doctor, doctor_id)):
            id_column = model.patient_id if model is Patient else model.doctor_id
            statement = (
                select(id_column)
                .where(id_column == key)
                .with_hint(model, "WITH (UPDLOCK, HOLDLOCK)", dialect_name="mssql")
            )
            self.session.execute(statement).scalar_one_or_none()

    def _lock_specialty_pricing(self, specialty_id: int) -> None:
        """Serialize a booking with a concurrent consultation price change."""
        bind = self.session.get_bind()
        if getattr(getattr(bind, "dialect", None), "name", None) != "mssql":
            return
        statement = (
            select(Specialty.specialty_id)
            .where(Specialty.specialty_id == specialty_id)
            .with_hint(Specialty, "WITH (UPDLOCK, HOLDLOCK)", dialect_name="mssql")
        )
        self.session.execute(statement).scalar_one_or_none()

    def _lock_appointment(self, appointment: Appointment) -> None:
        bind = self.session.get_bind()
        if getattr(getattr(bind, "dialect", None), "name", None) != "mssql":
            return
        statement = (
            select(Appointment.appointment_id)
            .where(Appointment.appointment_id == appointment.appointment_id)
            .with_hint(Appointment, "WITH (UPDLOCK, HOLDLOCK)", dialect_name="mssql")
        )
        self.session.execute(statement).scalar_one_or_none()
        self.session.refresh(appointment)

    def validate_target_slot(
        self,
        patient_id: int,
        doctor_id: int,
        appointment_date: date,
        start_time: time,
        end_time: time,
        exclude_appointment_id: int | None = None,
        allow_inactive_patient: bool = False,
    ) -> Doctor:
        """Apply the same booking rules to patient and reception workflows."""
        self._lock_booking_resources(patient_id, doctor_id)

        patient = self.session.get(Patient, patient_id)
        if patient is None:
            raise NotFoundError("Không tìm thấy hồ sơ bệnh nhân.")
        # Real ORM models are checked here. Lightweight unit fakes are allowed
        # to provide their own repository responses without a complete identity graph.
        if isinstance(patient, Patient):
            user = patient.user
            if (
                user is None
                or user.role != "PATIENT"
                or (
                    not user.is_active
                    and not (allow_inactive_patient and getattr(patient, "is_walk_in", False))
                )
            ):
                raise ValidationError("Hồ sơ bệnh nhân không hoạt động hoặc không hợp lệ.")

        now = clinic_now()
        if appointment_date < now.date():
            raise ValidationError("Không thể đặt lịch khám trong quá khứ.")
        if start_time.tzinfo is not None or end_time.tzinfo is not None or start_time >= end_time:
            raise ValidationError("Khung giờ khám không hợp lệ.")
        if appointment_date == now.date() and start_time <= now.time().replace(tzinfo=None):
            raise ValidationError("Khung giờ đặt lịch đã trôi qua.")

        doctor = self.doctor_repo.get_doctor_by_id(doctor_id)
        if doctor is None:
            raise NotFoundError("Bác sĩ không tồn tại hoặc đã ngừng hoạt động.")
        doctor_user = getattr(doctor, "user", None)
        specialty = getattr(doctor, "specialty", None)
        clinic = getattr(doctor, "clinic", None)
        if (
            doctor_user is None
            or not getattr(doctor_user, "is_active", True)
            or getattr(doctor_user, "role", "DOCTOR") != "DOCTOR"
            or specialty is None
            or not getattr(specialty, "is_active", True)
            or clinic is None
            or not getattr(clinic, "is_active", True)
        ):
            raise ValidationError("Bác sĩ, chuyên khoa hoặc cơ sở khám không hoạt động.")

        if get_settings().app_mode == "production":
            self._lock_specialty_pricing(doctor.specialty_id)
            if not self._has_one_valid_charge(
                self._consultation_charges_for_day(doctor.specialty_id, appointment_date),
                appointment_date,
                start_time,
            ):
                raise ConflictError(
                    "Chuyên khoa chưa có đúng một phí khám hiệu lực tại giờ hẹn; "
                    "quản trị viên cần duyệt bảng giá trước khi đặt lịch."
                )

        schedules = self.doctor_repo.get_schedules(
            doctor_id, day_of_week=appointment_date.isoweekday()
        )
        valid_slot = False
        for schedule in schedules:
            step = getattr(schedule, "slot_duration", 0)
            if (
                not getattr(schedule, "is_active", True)
                or step <= 0
                or start_time < schedule.start_time
                or end_time > schedule.end_time
            ):
                continue
            schedule_start = datetime.combine(appointment_date, schedule.start_time)
            target_start = datetime.combine(appointment_date, start_time)
            target_end = datetime.combine(appointment_date, end_time)
            offset = (target_start - schedule_start).total_seconds()
            length = (target_end - target_start).total_seconds()
            if offset % (step * 60) == 0 and length == step * 60:
                valid_slot = True
                break
        if not valid_slot:
            raise ValidationError("Khung giờ phải là một slot nguyên vẹn trong ca trực của bác sĩ.")
        if self._blocked_by_exception(
            start_time, end_time, self._schedule_exceptions(doctor_id, appointment_date)
        ):
            raise ConflictError("Bác sĩ nghỉ hoặc ca trực đã được đóng trong thời gian này.")

        doctor_appointments = _active_appointments(
            self.appointment_repo.get_active_appointments_for_doctor(doctor_id, appointment_date)
        )
        if any(
            a.appointment_id != exclude_appointment_id
            and _overlap(start_time, end_time, a.start_time, a.end_time)
            for a in doctor_appointments
        ):
            raise ConflictError("Khung giờ này bác sĩ đã có lịch hẹn khác.")

        patient_appointments = _active_appointments(
            self.appointment_repo.get_active_appointments_for_patient(patient_id, appointment_date)
        )
        if any(
            a.appointment_id != exclude_appointment_id
            and _overlap(start_time, end_time, a.start_time, a.end_time)
            for a in patient_appointments
        ):
            raise ConflictError("Bạn đã có lịch khám khác trùng khung giờ này.")

        patient_appointments_all = _active_appointments(
            self.appointment_repo.get_active_appointments_for_patient_all(patient_id)
        )
        if any(
            a.appointment_id != exclude_appointment_id
            and a.appointment_date == appointment_date
            and (
                getattr(a, "specialty_id", None)
                or getattr(getattr(a, "doctor", None), "specialty_id", None)
            ) == doctor.specialty_id
            for a in patient_appointments_all
        ):
            raise ConflictError(
                "Bạn đã có lịch hẹn thuộc chuyên khoa này trong ngày đã chọn."
            )
        return doctor

    def create_appointment_for_patient(
        self,
        patient_id: int,
        doctor_id: int,
        appointment_date: date,
        start_time: time,
        end_time: time,
        reason: str | None,
        *,
        status: str = "PENDING",
        allow_inactive_patient: bool = False,
        before_commit: Callable[[Appointment], None] | None = None,
    ) -> Appointment:
        if status not in ("PENDING", "CONFIRMED"):
            raise ValidationError("Trạng thái đặt lịch không hợp lệ.")
        if reason is not None and (not reason.strip() or len(reason) > 500):
            raise ValidationError("Lý do khám phải có nội dung và không quá 500 ký tự.")
        doctor = self.validate_target_slot(
            patient_id,
            doctor_id,
            appointment_date,
            start_time,
            end_time,
            allow_inactive_patient=allow_inactive_patient,
        )
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor.doctor_id,
            clinic_id=doctor.clinic_id,
            specialty_id=doctor.specialty_id,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            reason=reason,
            status=status,
            created_at=clinic_now().replace(tzinfo=None),
        )
        try:
            self.appointment_repo.add(appointment)
            if before_commit is not None:
                before_commit(appointment)
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Không thể lưu thông tin lịch khám.") from exc
        return appointment

    def reschedule_for_patient(
        self,
        appointment: Appointment,
        appointment_date: date,
        start_time: time,
        end_time: time,
        doctor_id: int,
        *,
        status: str,
        reason: str | None = None,
        allow_inactive_patient: bool = False,
        before_commit: Callable[[Appointment], None] | None = None,
    ) -> Appointment:
        if status not in ("PENDING", "CONFIRMED"):
            raise ValidationError("Trạng thái đổi lịch không hợp lệ.")
        if appointment.status not in ("PENDING", "CONFIRMED"):
            raise ConflictError("Chỉ có thể đổi lịch trước khi bệnh nhân check-in.")
        if reason is not None and (not reason.strip() or len(reason) > 500):
            raise ValidationError("Lý do đổi lịch phải có nội dung và không quá 500 ký tự.")
        if (
            appointment.doctor_id == doctor_id
            and appointment.appointment_date == appointment_date
            and appointment.start_time == start_time
            and appointment.end_time == end_time
        ):
            raise ValidationError(
                "Vui lòng chọn ngày khám hoặc khung giờ mới khác với lịch hẹn hiện tại."
            )
        doctor = self.validate_target_slot(
            appointment.patient_id,
            doctor_id,
            appointment_date,
            start_time,
            end_time,
            exclude_appointment_id=appointment.appointment_id,
            allow_inactive_patient=allow_inactive_patient,
        )
        self._lock_appointment(appointment)
        if appointment.status not in ("PENDING", "CONFIRMED"):
            raise ConflictError("Chỉ có thể đổi lịch trước khi bệnh nhân check-in.")
        appointment.doctor_id = doctor.doctor_id
        appointment.clinic_id = doctor.clinic_id
        appointment.specialty_id = doctor.specialty_id
        appointment.appointment_date = appointment_date
        appointment.start_time = start_time
        appointment.end_time = end_time
        appointment.status = status
        appointment.last_reschedule_reason = reason
        try:
            if before_commit is not None:
                before_commit(appointment)
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Không thể lưu cập nhật đổi lịch khám.") from exc
        return appointment

    def book_appointment(self, patient_id: int, req: AppointmentCreateRequest) -> AppointmentDetail:
        appointment = self.create_appointment_for_patient(
            patient_id,
            req.doctor_id,
            req.appointment_date,
            req.start_time,
            req.end_time,
            req.reason,
            before_commit=(
                lambda appointment: self._audit_patient_change(
                    appointment, "APPOINTMENT_BOOK", new_status="PENDING"
                )
                if get_settings().app_mode == "production"
                else None
            ),
        )
        return self.appointment_service.get_detail(appointment.appointment_id, patient_id)

    def cancel_appointment(
        self, appointment_id: int, patient_id: int, req: AppointmentCancelRequest
    ) -> AppointmentDetail:
        appointment = self.appointment_repo.get_owned(appointment_id, patient_id)
        if appointment is None:
            raise NotFoundError("Không tìm thấy lịch hẹn hoặc bạn không có quyền thao tác.")
        self._lock_appointment(appointment)
        if appointment.status not in ("PENDING", "CONFIRMED"):
            raise ConflictError("Chỉ có thể hủy lịch trước khi bệnh nhân check-in.")
        now = clinic_now()
        if appointment.appointment_date < now.date() or (
            appointment.appointment_date == now.date()
            and appointment.start_time <= now.time().replace(tzinfo=None)
        ):
            raise ValidationError("Không thể hủy lịch đã qua thời gian bắt đầu.")
        previous_status = appointment.status
        appointment.status = "CANCELLED"
        appointment.cancellation_reason = req.cancellation_reason
        try:
            if get_settings().app_mode == "production":
                self._audit_patient_change(
                    appointment,
                    "APPOINTMENT_CANCEL",
                    old_status=previous_status,
                    new_status="CANCELLED",
                )
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Không thể cập nhật trạng thái hủy lịch.") from exc
        return self.appointment_service.get_detail(appointment.appointment_id, patient_id)

    def reschedule_appointment(
        self, appointment_id: int, patient_id: int, req: AppointmentRescheduleRequest
    ) -> AppointmentDetail:
        appointment = self.appointment_repo.get_owned(appointment_id, patient_id)
        if appointment is None:
            raise NotFoundError("Không tìm thấy lịch hẹn hoặc bạn không có quyền thao tác.")
        target_doctor_id = req.new_doctor_id or appointment.doctor_id
        self.reschedule_for_patient(
            appointment,
            req.new_appointment_date,
            req.new_start_time,
            req.new_end_time,
            target_doctor_id,
            status="PENDING",
            reason=req.reason,
            before_commit=(
                lambda changed: self._audit_patient_change(
                    changed, "APPOINTMENT_RESCHEDULE", new_status="PENDING"
                )
                if get_settings().app_mode == "production"
                else None
            ),
        )
        return self.appointment_service.get_detail(appointment.appointment_id, patient_id)
