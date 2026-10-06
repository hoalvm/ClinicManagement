"""Rollback-only production domain flow on an isolated SQL Server staging database.

Run with ``RUN_PRODUCTION_STAGING_INTEGRATION=1 pytest -q
tests/integration/test_production_staging.py``. The configured connection is
redirected to ClinicManagementSchemaStagingDB and the exact database name is
checked before the test inserts any data.
"""

from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.api.routes import catalog
from backend.app.core import audit
from backend.app.core.clock import clinic_today
from backend.app.core.config import get_settings
from backend.app.core.exceptions import AuthorizationError, ConflictError, ValidationError
from backend.app.models import (
    Appointment,
    ChargeCatalog,
    Clinic,
    Doctor,
    MedicalRecord,
    Patient,
    Payment,
    Specialty,
    StaffClinicAssignment,
    User,
)
from backend.app.routers import doctor_portal
from backend.app.routers.doctor_portal import (
    CompleteExamRequest,
    PrescriptionItemIn,
    accept_patient,
    complete_examination,
    get_clinical_context,
    get_schedule,
)
from backend.app.schemas.reception import (
    ChargeCatalogCreate,
    CreateInvoiceRequest,
    ProcessPaymentRequest,
    VerifyPatientIdentityRequest,
)
from backend.app.services import reception_service

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_PRODUCTION_STAGING_INTEGRATION") != "1",
        reason="set RUN_PRODUCTION_STAGING_INTEGRATION=1 for rollback-only SQL Server staging flow",
    ),
]

STAGING_DB = "ClinicManagementSchemaStagingDB"


def _add(session: Session, row):
    session.add(row)
    session.flush()
    return row


def test_production_billing_and_clinic_scope_are_atomic_on_sql_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings().model_copy(update={"db_name": STAGING_DB})
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    connection = engine.connect()
    try:
        assert connection.dialect.name == "mssql"
        outer = connection.begin()
        try:
            assert connection.execute(text("SELECT DB_NAME()")).scalar_one() == STAGING_DB
            make_session = sessionmaker(
                bind=connection,
                class_=Session,
                autoflush=False,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            mode = SimpleNamespace(app_mode="production", appointment_grace_minutes=15)
            today = clinic_today()
            monkeypatch.setattr(reception_service, "get_settings", lambda: mode)
            monkeypatch.setattr(catalog, "get_settings", lambda: mode)
            monkeypatch.setattr(
                catalog,
                "clinic_naive_now",
                lambda: datetime.combine(today, time(15, 0)),
            )
            monkeypatch.setattr(audit, "get_settings", lambda: mode)
            monkeypatch.setattr(doctor_portal, "get_settings", lambda: mode)
            suffix = uuid4().hex[:10]
            yesterday = today - timedelta(days=1)
            with make_session() as session:
                clinic_a = _add(
                    session,
                    Clinic(clinic_name=f"Staging A {suffix}", address="Quận 1"),
                )
                clinic_b = _add(
                    session,
                    Clinic(clinic_name=f"Staging B {suffix}", address="Tân Bình"),
                )
                specialty = _add(
                    session,
                    Specialty(specialty_name=f"Nội tổng quát {suffix}"),
                )
                staff = _add(
                    session,
                    User(
                        username=f"staff-{suffix}",
                        password_hash="integration-only",
                        full_name="Nhân viên kiểm thử",
                        role="STAFF",
                        is_active=True,
                    ),
                )
                admin = _add(
                    session,
                    User(
                        username=f"admin-{suffix}",
                        password_hash="integration-only",
                        full_name="Quản trị kiểm thử",
                        role="ADMIN",
                        is_active=True,
                    ),
                )
                patient_user = _add(
                    session,
                    User(
                        username=f"patient-{suffix}",
                        password_hash="integration-only",
                        full_name="Bệnh nhân kiểm thử",
                        role="PATIENT",
                        is_active=True,
                    ),
                )
                patient = _add(
                    session,
                    Patient(
                        user_id=patient_user.user_id,
                        date_of_birth=date(1991, 3, 4),
                        gender="FEMALE",
                    ),
                )
                doctor_user_a = _add(
                    session,
                    User(
                        username=f"doctor-a-{suffix}",
                        password_hash="integration-only",
                        full_name="Bác sĩ A",
                        role="DOCTOR",
                        is_active=True,
                    ),
                )
                doctor_user_b = _add(
                    session,
                    User(
                        username=f"doctor-b-{suffix}",
                        password_hash="integration-only",
                        full_name="Bác sĩ B",
                        role="DOCTOR",
                        is_active=True,
                    ),
                )
                doctor_a = _add(
                    session,
                    Doctor(
                        user_id=doctor_user_a.user_id,
                        specialty_id=specialty.specialty_id,
                        clinic_id=clinic_a.clinic_id,
                        license_number=f"STAGING-A-{suffix}",
                    ),
                )
                doctor_b = _add(
                    session,
                    Doctor(
                        user_id=doctor_user_b.user_id,
                        specialty_id=specialty.specialty_id,
                        clinic_id=clinic_b.clinic_id,
                        license_number=f"STAGING-B-{suffix}",
                    ),
                )
                _add(
                    session,
                    StaffClinicAssignment(
                        user_id=staff.user_id,
                        clinic_id=clinic_a.clinic_id,
                        is_active=True,
                    ),
                )
                old_charge = _add(
                    session,
                    ChargeCatalog(
                        code=f"CONS-OLD-{suffix}",
                        display_name="Phí khám Nội tổng quát",
                        category="CONSULTATION",
                        specialty_id=specialty.specialty_id,
                        unit_price=Decimal("175000.00"),
                        is_active=True,
                        effective_from=datetime.combine(yesterday - timedelta(days=1), time(0, 0)),
                    ),
                )

                def encounter(doctor: Doctor, clinic: Clinic, start: time, status: str):
                    return _add(
                        session,
                        Appointment(
                            patient_id=patient.patient_id,
                            doctor_id=doctor.doctor_id,
                            specialty_id=specialty.specialty_id,
                            clinic_id=clinic.clinic_id,
                            appointment_date=yesterday,
                            start_time=start,
                            end_time=(
                                datetime.combine(yesterday, start) + timedelta(minutes=30)
                            ).time(),
                            reason="Khám kiểm thử",
                            status=status,
                        ),
                    )

                paid_visit = encounter(doctor_a, clinic_a, time(9, 0), "COMPLETED")
                cash_visit = encounter(doctor_a, clinic_a, time(10, 0), "COMPLETED")
                other_site = encounter(doctor_b, clinic_b, time(11, 0), "COMPLETED")
                missed_visit = encounter(doctor_a, clinic_a, time(12, 0), "CONFIRMED")
                late_visit = encounter(doctor_a, clinic_a, time(13, 0), "IN_PROGRESS")
                late_visit.check_in_at = datetime.combine(yesterday, time(13, 0))
                stale_check_in = encounter(doctor_a, clinic_a, time(13, 30), "CHECKED_IN")
                stale_check_in.check_in_at = datetime.combine(yesterday, time(13, 30))
                doctor_visit = _add(
                    session,
                    Appointment(
                        patient_id=patient.patient_id,
                        doctor_id=doctor_a.doctor_id,
                        specialty_id=specialty.specialty_id,
                        clinic_id=clinic_a.clinic_id,
                        appointment_date=today,
                        start_time=time(10, 0),
                        end_time=time(10, 30),
                        reason="Khám kiểm thử",
                        status="CHECKED_IN",
                        check_in_at=datetime.combine(today, time(9, 55)),
                    ),
                )
                future_booking = _add(
                    session,
                    Appointment(
                        patient_id=patient.patient_id,
                        doctor_id=doctor_a.doctor_id,
                        specialty_id=specialty.specialty_id,
                        clinic_id=clinic_a.clinic_id,
                        appointment_date=today + timedelta(days=1),
                        start_time=time(9, 0),
                        end_time=time(9, 30),
                        reason="Kiểm tra giữ giá lịch tương lai",
                        status="CONFIRMED",
                    ),
                )
                for visit in (paid_visit, cash_visit, other_site):
                    _add(
                        session,
                        MedicalRecord(
                            appointment_id=visit.appointment_id,
                            symptoms="Ho khan",
                            diagnosis="Viêm họng",
                            examination_date=datetime.combine(yesterday, visit.end_time),
                        ),
                    )
                session.commit()

                queue = get_schedule(
                    doctor_id=doctor_a.doctor_id,
                    auth_info=(doctor_user_a, doctor_a),
                    db=session,
                )
                assert {row["AppointmentID"] for row in queue} == {
                    doctor_visit.appointment_id,
                    late_visit.appointment_id,
                }

                new_fee = ChargeCatalogCreate(
                    code=f"CONS-NEW-{suffix}",
                    display_name="Phí khám Nội tổng quát mới",
                    category="CONSULTATION",
                    specialty_id=specialty.specialty_id,
                    unit_price=Decimal("190000.00"),
                )
                with pytest.raises(ConflictError, match="lịch hẹn tương lai"):
                    catalog.create_charge(new_fee, session, admin)
                session.refresh(old_charge)
                assert old_charge.is_active
                future_booking.status = "CANCELLED"
                session.commit()
                replacement = catalog.create_charge(new_fee, session, admin)
                assert replacement.unit_price == Decimal("190000.00")
                session.refresh(old_charge)
                assert not old_charge.is_active

                service = reception_service.ReceptionService(session, staff_user_id=staff.user_id)
                with pytest.raises(ValidationError):
                    service.cancel_appointment(
                        stale_check_in.appointment_id,
                        "Bệnh nhân rời phòng khám khi chưa được khám",
                    )
                cancelled_check_in = service.cancel_appointment(
                    stale_check_in.appointment_id,
                    "Bệnh nhân rời phòng khám khi chưa được khám",
                    care_not_started=True,
                )
                assert cancelled_check_in.status == "CANCELLED"
                preview = service.invoice_preview(paid_visit.appointment_id)
                assert preview.total_amount == Decimal("175000.00")
                assert preview.charge_id == old_charge.charge_id
                with pytest.raises(AuthorizationError):
                    service.get_appointment(other_site.appointment_id)
                with pytest.raises(AuthorizationError):
                    service.create_invoice(CreateInvoiceRequest(appointment_id=other_site.appointment_id))

                transfer_invoice = service.create_invoice(
                    CreateInvoiceRequest(appointment_id=paid_visit.appointment_id)
                )
                assert transfer_invoice.total_amount == Decimal("175000.00")
                transferred = service.process_payment(
                    transfer_invoice.invoice_id,
                    ProcessPaymentRequest(
                        payment_method="TRANSFER",
                        amount=Decimal("175000.00"),
                        external_reference=f"STAGING-TXN-{suffix}",
                        manual_verified=True,
                    ),
                    recorded_by_user_id=staff.user_id,
                )
                assert transferred.status == "PAID"
                transfer_payment = session.scalar(
                    select(Payment).where(Payment.invoice_id == transfer_invoice.invoice_id)
                )
                assert transfer_payment is not None
                assert transfer_payment.external_reference == f"STAGING-TXN-{suffix}"
                assert transfer_payment.recorded_by_user_id == staff.user_id

                cash_invoice = service.create_invoice(
                    CreateInvoiceRequest(appointment_id=cash_visit.appointment_id)
                )
                cash = service.process_payment(
                    cash_invoice.invoice_id,
                    ProcessPaymentRequest(
                        payment_method="CASH", amount=Decimal("200000.00")
                    ),
                    recorded_by_user_id=staff.user_id,
                )
                assert cash.change_due == Decimal("25000.00")
                absent = service.mark_no_show(missed_visit.appointment_id)
                assert absent.no_show_reason_code == "NO_ARRIVAL"
                assert absent.no_show_by_user_id == staff.user_id
                verified = service.verify_patient_identity(
                    VerifyPatientIdentityRequest(
                        patient_id=patient.patient_id,
                        date_of_birth=date(1991, 3, 4),
                        clinic_id=clinic_a.clinic_id,
                        identity_checked=True,
                    )
                )
                assert verified.patient_id == patient.patient_id
                accept_patient(
                    doctor_visit.appointment_id,
                    auth_info=(doctor_user_a, doctor_a),
                    db=session,
                )
                with pytest.raises(HTTPException) as missing_context:
                    complete_examination(
                        doctor_visit.appointment_id,
                        CompleteExamRequest(symptoms="Ho khan", diagnosis="Viêm họng"),
                        auth_info=(doctor_user_a, doctor_a),
                        db=session,
                    )
                assert missing_context.value.status_code == 409
                context = get_clinical_context(
                    doctor_visit.appointment_id,
                    auth_info=(doctor_user_a, doctor_a),
                    db=session,
                )
                assert context.patient_id == patient.patient_id
                assert context.allergy_status == "NOT_DOCUMENTED"
                assert len(context.prior_records) == 3
                assert context.prior_records_has_more is False
                assert {r.appointment_id for r in context.prior_records} == {
                    paid_visit.appointment_id,
                    cash_visit.appointment_id,
                    other_site.appointment_id,
                }
                session.refresh(doctor_visit)
                assert doctor_visit.clinical_context_loaded_by_user_id == doctor_user_a.user_id
                assert doctor_visit.clinical_context_loaded_at >= doctor_visit.check_in_at
                with pytest.raises(HTTPException) as rejected_rx:
                    complete_examination(
                        doctor_visit.appointment_id,
                        CompleteExamRequest(
                            symptoms="Ho khan",
                            diagnosis="Viêm họng",
                            prescription_items=[
                                PrescriptionItemIn(medicine_name="Thuốc thử", quantity=1)
                            ],
                        ),
                        auth_info=(doctor_user_a, doctor_a),
                        db=session,
                    )
                assert rejected_rx.value.status_code == 409
                assert session.scalar(
                    select(MedicalRecord).where(
                        MedicalRecord.appointment_id == doctor_visit.appointment_id
                    )
                ) is None
                complete_examination(
                    doctor_visit.appointment_id,
                    CompleteExamRequest(symptoms="Ho khan", diagnosis="Viêm họng"),
                    auth_info=(doctor_user_a, doctor_a),
                    db=session,
                )
                session.refresh(doctor_visit)
                assert doctor_visit.status == "COMPLETED"
                with pytest.raises(HTTPException) as missing_late_reason:
                    complete_examination(
                        late_visit.appointment_id,
                        CompleteExamRequest(symptoms="Ho khan", diagnosis="Viêm họng"),
                        auth_info=(doctor_user_a, doctor_a),
                        db=session,
                    )
                assert missing_late_reason.value.status_code == 422
                get_clinical_context(
                    late_visit.appointment_id,
                    auth_info=(doctor_user_a, doctor_a),
                    db=session,
                )
                complete_examination(
                    late_visit.appointment_id,
                    CompleteExamRequest(
                        symptoms="Ho khan",
                        diagnosis="Viêm họng",
                        late_entry_reason="Gián đoạn hệ thống tại thời điểm kết thúc ca",
                    ),
                    auth_info=(doctor_user_a, doctor_a),
                    db=session,
                )
                session.refresh(late_visit)
                assert late_visit.status == "COMPLETED"
                late_record = session.scalar(
                    select(MedicalRecord).where(
                        MedicalRecord.appointment_id == late_visit.appointment_id
                    )
                )
                assert late_record is not None
                assert late_record.late_entry_reason == "Gián đoạn hệ thống tại thời điểm kết thúc ca"
                audit_count = session.execute(
                    text("SELECT COUNT(*) FROM dbo.AuditEvents WHERE ActorUserID=:id"),
                    {"id": staff.user_id},
                ).scalar_one()
                assert audit_count >= 6
                doctor_audit_count = session.execute(
                    text("SELECT COUNT(*) FROM dbo.AuditEvents WHERE ActorUserID=:id"),
                    {"id": doctor_user_a.user_id},
                ).scalar_one()
                assert doctor_audit_count >= 4
        finally:
            assert outer.is_active, "A service escaped the rollback-only outer transaction"
            outer.rollback()
    finally:
        connection.close()
        engine.dispose()
