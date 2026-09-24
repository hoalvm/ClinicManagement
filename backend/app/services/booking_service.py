"""Business logic for patient booking, available time slots, and schedule changes."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.clock import clinic_now, clinic_today
from backend.app.core.exceptions import (
    AppError,
    ConflictError,
    InternalServerError,
    NotFoundError,
)
from backend.app.models import Appointment
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


class BookingService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.doctor_repo = DoctorRepository(session)
        self.appointment_repo = AppointmentRepository(session)
        self.appointment_service = AppointmentService(session)

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
        if exclude_appointment_id:
            active_patient_appts = [
                a
                for a in active_patient_appts
                if getattr(a, "appointment_id", None) != exclude_appointment_id
            ]
        has_active_same_specialty = any(
            getattr(a, "appointment_date", None) == appointment_date
            and getattr(a, "doctor", None)
            and getattr(a.doctor, "specialty_id", None) == doctor.specialty_id
            for a in active_patient_appts
        )
        has_active_same_clinic_day = (
            doctor.clinic_id is not None
            and any(
                getattr(a, "appointment_date", None) == appointment_date
                and getattr(a, "clinic_id", None) == doctor.clinic_id
                for a in active_patient_appts
            )
        )

        today = clinic_today()
        now_time = clinic_now().time()
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
                elif has_active_same_specialty:
                    slots.append(
                        TimeSlot(
                            start_time=slot_start,
                            end_time=slot_end,
                            is_available=False,
                            reason="Bạn đang có lịch hẹn chưa khám thuộc chuyên khoa này",
                        )
                    )
                elif has_active_same_clinic_day:
                    slots.append(
                        TimeSlot(
                            start_time=slot_start,
                            end_time=slot_end,
                            is_available=False,
                            reason="Bạn đã có lịch hẹn tại phòng khám này trong ngày",
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

    def book_appointment(self, patient_id: int, req: AppointmentCreateRequest) -> AppointmentDetail:
        today = clinic_today()
        if req.appointment_date < today:
            raise AppError("Không thể đặt lịch khám trong quá khứ.")

        if req.appointment_date == today and req.start_time <= clinic_now().time():
            raise AppError("Khung giờ đặt lịch đã trôi qua.")

        if req.start_time >= req.end_time:
            raise AppError("Thời gian bắt đầu phải trước thời gian kết thúc.")

        doctor = self.doctor_repo.get_doctor_by_id(req.doctor_id)
        if not doctor:
            raise NotFoundError("Bác sĩ không tồn tại hoặc đã ngừng hoạt động.")

        day_of_week = req.appointment_date.isoweekday()
        schedules = self.doctor_repo.get_schedules(req.doctor_id, day_of_week=day_of_week)
        in_schedule = any(
            s.start_time <= req.start_time and req.end_time <= s.end_time for s in schedules
        )
        if not in_schedule:
            raise AppError("Bác sĩ không có ca trực trong khung giờ yêu cầu.")

        # Check doctor collision
        doc_appts = self.appointment_repo.get_active_appointments_for_doctor(
            req.doctor_id, req.appointment_date
        )
        if any(_overlap(req.start_time, req.end_time, a.start_time, a.end_time) for a in doc_appts):
            raise ConflictError("Khung giờ này đã có người đặt. Vui lòng chọn khung giờ khác.")

        # Check anti-spam: 1 active appointment per specialty until examined/cancelled
        active_patient_appts = (
            self.appointment_repo.get_active_appointments_for_patient_all(patient_id)
            if hasattr(self.appointment_repo, "get_active_appointments_for_patient_all")
            else []
        )
        same_spec_appt = next(
            (
                a
                for a in active_patient_appts
                if getattr(a, "appointment_date", None) == req.appointment_date
                and getattr(a, "doctor", None)
                and getattr(a.doctor, "specialty_id", None) == doctor.specialty_id
            ),
            None,
        )
        if same_spec_appt:
            spec_name = (
                doctor.specialty.specialty_name
                if getattr(doctor, "specialty", None)
                else "chuyên khoa này"
            )
            raise ConflictError(
                f"Bạn đã có một lịch hẹn trong ngày này thuộc chuyên khoa {spec_name}. "
                "Vui lòng chọn ngày khám khác hoặc hủy lịch hẹn cũ trước khi đặt lịch mới."
            )

        # Check anti-spam: only 1 appointment at same clinic on same date
        if doctor.clinic_id:
            same_clinic_day = next(
                (
                    a
                    for a in active_patient_appts
                    if getattr(a, "appointment_date", None) == req.appointment_date
                    and getattr(a, "clinic_id", None) == doctor.clinic_id
                ),
                None,
            )
            if same_clinic_day:
                raise ConflictError("Bạn đã có lịch khám tại phòng khám này trong ngày đã chọn.")

        # Check patient time collision on date
        patient_appts = self.appointment_repo.get_active_appointments_for_patient(
            patient_id, req.appointment_date
        )
        if any(
            _overlap(req.start_time, req.end_time, a.start_time, a.end_time) for a in patient_appts
        ):
            raise ConflictError("Bạn đã có lịch khám khác trùng khung giờ này.")

        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor.doctor_id,
            clinic_id=doctor.clinic_id,
            appointment_date=req.appointment_date,
            start_time=req.start_time,
            end_time=req.end_time,
            reason=req.reason,
            status="PENDING",
        )
        self.appointment_repo.add(appointment)
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError(
                "Không thể lưu thông tin lịch khám vào cơ sở dữ liệu."
            ) from exc
        return self.appointment_service.get_detail(appointment.appointment_id, patient_id)

    def cancel_appointment(
        self, appointment_id: int, patient_id: int, req: AppointmentCancelRequest
    ) -> AppointmentDetail:
        appointment = self.appointment_repo.get_owned(appointment_id, patient_id)
        if not appointment:
            raise NotFoundError("Không tìm thấy lịch hẹn hoặc bạn không có quyền thao tác.")

        if appointment.status in ("COMPLETED", "IN_PROGRESS", "CANCELLED"):
            raise AppError(f"Không thể hủy lịch hẹn đang ở trạng thái {appointment.status}.")

        today = clinic_today()
        if appointment.appointment_date < today or (
            appointment.appointment_date == today and appointment.start_time <= clinic_now().time()
        ):
            raise AppError("Không thể hủy lịch khám đã qua thời gian bắt đầu.")

        appointment.status = "CANCELLED"
        if req.cancellation_reason:
            appointment.reason = (
                f"{appointment.reason or ''} [Lý do hủy: {req.cancellation_reason}]".strip()
            )
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Không thể cập nhật trạng thái hủy lịch.") from exc
        return self.appointment_service.get_detail(appointment.appointment_id, patient_id)

    def reschedule_appointment(
        self, appointment_id: int, patient_id: int, req: AppointmentRescheduleRequest
    ) -> AppointmentDetail:
        appointment = self.appointment_repo.get_owned(appointment_id, patient_id)
        if not appointment:
            raise NotFoundError("Không tìm thấy lịch hẹn hoặc bạn không có quyền thao tác.")

        if appointment.status not in ("PENDING", "CONFIRMED"):
            raise AppError("Chỉ có thể đổi lịch khi lịch hẹn ở trạng thái PENDING hoặc CONFIRMED.")

        today = clinic_today()
        if req.new_appointment_date < today:
            raise AppError("Không thể đổi sang ngày trong quá khứ.")

        if req.new_appointment_date == today and req.new_start_time <= clinic_now().time():
            raise AppError("Khung giờ đổi lịch đã trôi qua.")

        if req.new_start_time >= req.new_end_time:
            raise AppError("Thời gian bắt đầu phải trước thời gian kết thúc.")

        target_doctor_id = req.new_doctor_id or appointment.doctor_id
        if (
            target_doctor_id == appointment.doctor_id
            and req.new_appointment_date == appointment.appointment_date
            and req.new_start_time == appointment.start_time
        ):
            raise AppError("Vui lòng chọn ngày khám hoặc khung giờ mới khác với lịch hẹn hiện tại.")

        target_doctor = self.doctor_repo.get_doctor_by_id(target_doctor_id)
        if not target_doctor:
            raise NotFoundError("Bác sĩ không tồn tại hoặc đã ngừng hoạt động.")

        day_of_week = req.new_appointment_date.isoweekday()
        schedules = self.doctor_repo.get_schedules(target_doctor_id, day_of_week=day_of_week)
        in_schedule = any(
            s.start_time <= req.new_start_time and req.new_end_time <= s.end_time for s in schedules
        )
        if not in_schedule:
            raise AppError("Bác sĩ không có ca trực trong khung giờ yêu cầu.")

        # Check doctor conflicts excluding this appointment
        doc_appts = self.appointment_repo.get_active_appointments_for_doctor(
            target_doctor_id, req.new_appointment_date
        )
        doc_conflicts = [
            a
            for a in doc_appts
            if a.appointment_id != appointment_id
            and _overlap(req.new_start_time, req.new_end_time, a.start_time, a.end_time)
        ]
        if doc_conflicts:
            raise ConflictError("Khung giờ này bác sĩ đã có lịch hẹn khác.")

        # Check patient conflicts excluding this appointment
        patient_appts = self.appointment_repo.get_active_appointments_for_patient(
            patient_id, req.new_appointment_date
        )
        patient_conflicts = [
            a
            for a in patient_appts
            if a.appointment_id != appointment_id
            and _overlap(req.new_start_time, req.new_end_time, a.start_time, a.end_time)
        ]
        if patient_conflicts:
            raise ConflictError("Bạn đã có một lịch khám khác trùng khung giờ này.")

        appointment.doctor_id = target_doctor.doctor_id
        appointment.clinic_id = target_doctor.clinic_id
        appointment.appointment_date = req.new_appointment_date
        appointment.start_time = req.new_start_time
        appointment.end_time = req.new_end_time
        appointment.status = "PENDING"
        if req.reason:
            appointment.reason = f"{appointment.reason or ''} [Đổi lịch: {req.reason}]".strip()
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Không thể lưu cập nhật đổi lịch khám.") from exc
        return self.appointment_service.get_detail(appointment.appointment_id, patient_id)
