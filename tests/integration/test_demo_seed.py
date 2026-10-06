"""Read-only invariant checks for a freshly initialized project database."""

from __future__ import annotations

import os
from collections import Counter
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from backend.app.core.clock import clinic_now
from backend.app.db.seed import DEMO_DOCTORS, SEED_VERSION, demo_live_slot, seed_database
from backend.app.db.session import SessionLocal
from backend.app.models import (
    Appointment,
    ChargeCatalog,
    Clinic,
    Doctor,
    DoctorSchedule,
    Invoice,
    InvoiceItem,
    MedicalRecord,
    Patient,
    Payment,
    PrescriptionItem,
    Specialty,
    StaffClinicAssignment,
    User,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_SQLSERVER_INTEGRATION", "").strip() != "1",
            reason="set RUN_SQLSERVER_INTEGRATION=1 on a fresh project database",
    ),
]


def test_fresh_demo_seed_is_coherent_and_rerun_is_non_destructive() -> None:
    with SessionLocal() as session:
        assert session.execute(text("SELECT DB_NAME()")).scalar_one() == "ClinicManagementDB"
        assert session.execute(
            text("SELECT COUNT(*) FROM dbo.SchemaMigrations WHERE MigrationID = :version"),
            {"version": SEED_VERSION},
        ).scalar_one() == 1

        users = session.execute(select(User)).scalars().all()
        doctors = session.execute(select(Doctor)).scalars().all()
        patients = session.execute(select(Patient)).scalars().all()
        appointments = session.execute(select(Appointment)).scalars().all()
        schedules = session.execute(select(DoctorSchedule)).scalars().all()
        records = session.execute(select(MedicalRecord)).scalars().all()
        invoices = session.execute(select(Invoice)).scalars().all()
        items = session.execute(select(InvoiceItem)).scalars().all()
        payments = session.execute(select(Payment)).scalars().all()
        charges = session.execute(select(ChargeCatalog)).scalars().all()
        grants = session.execute(select(StaffClinicAssignment)).scalars().all()
        clinics = session.execute(select(Clinic)).scalars().all()
        specialties = session.execute(select(Specialty)).scalars().all()
        prescription_items = session.execute(select(PrescriptionItem)).scalars().all()

        assert len(users) == 16  # 1 admin, 2 staff, 5 doctors, 8 patients
        assert len(doctors) == 5 and len(patients) == 8
        assert len(clinics) == 3 and len(specialties) == 5
        assert len({user.phone for user in users}) == len(users)
        assert all(user.email.endswith("@anhoaclinic.example.com") for user in users)
        assert len({patient.address for patient in patients}) == len(patients)
        assert len({doctor.license_number for doctor in doctors}) == len(doctors)
        displayed_fields = [
            *(user.full_name for user in users),
            *(user.phone for user in users),
            *(clinic.clinic_name for clinic in clinics),
            *(clinic.address for clinic in clinics),
            *(specialty.description for specialty in specialties),
            *(doctor.license_number for doctor in doctors),
            *(patient.address for patient in patients),
            *(item.instructions for item in prescription_items),
            *(payment.external_reference for payment in payments if payment.external_reference),
        ]
        assert all(
            forbidden not in value.casefold()
            for value in displayed_fields
            for forbidden in ("demo", "giả lập", "mẫu", "training", "090000")
        )
        users_by_id = {user.user_id: user for user in users}
        assert {(users_by_id[doctor.user_id].username, users_by_id[doctor.user_id].full_name)
                for doctor in doctors} == {(row[0], row[1]) for row in DEMO_DOCTORS}
        assert len(appointments) == 12
        assert Counter(item.status for item in appointments) == {
            "COMPLETED": 5, "PENDING": 2, "CONFIRMED": 2,
            "CHECKED_IN": 1, "IN_PROGRESS": 1, "CANCELLED": 1,
        }
        assert len(records) == 5 and len(invoices) == 4 and len(payments) == 2
        assert len(charges) == 5 and len(grants) == 4
        assert {payment.payment_method for payment in payments} == {"CASH", "TRANSFER"}
        assert all(
            payment.recorded_by_user_id is not None
            and payment.verified_at is not None
            and payment.amount_received == payment.amount + payment.change_due
            for payment in payments
        )
        assert all(
            appt.appointment_date <= clinic_now().date()
            for appt in appointments
            if appt.status in {"COMPLETED", "CHECKED_IN", "IN_PROGRESS"}
        )

        record_ids = {record.appointment_id for record in records}
        assert record_ids == {appt.appointment_id for appt in appointments
                              if appt.status == "COMPLETED"}
        assert all(invoice.appointment_id in record_ids for invoice in invoices)
        assert all(appt.clinic_id == next(d.clinic_id for d in doctors
                                          if d.doctor_id == appt.doctor_id)
                   for appt in appointments)

        for appt in appointments:
            assert any(
                schedule.doctor_id == appt.doctor_id
                and schedule.day_of_week == appt.appointment_date.isoweekday()
                and schedule.is_active
                and schedule.start_time <= appt.start_time
                and appt.end_time <= schedule.end_time
                and schedule.slot_duration == 30
                for schedule in schedules
            ), appt.appointment_id
            if appt.status in {"CHECKED_IN", "IN_PROGRESS"}:
                assert appt.queue_number and appt.check_in_at
            if appt.status == "CANCELLED":
                assert appt.cancellation_reason

        active = [appt for appt in appointments if appt.status != "CANCELLED"]
        for index, left in enumerate(active):
            for right in active[index + 1:]:
                if left.appointment_date == right.appointment_date:
                    overlaps = left.start_time < right.end_time and right.start_time < left.end_time
                    assert not (overlaps and left.doctor_id == right.doctor_id)
                    assert not (overlaps and left.patient_id == right.patient_id)
        doctor01 = next(d for d in doctors if users_by_id[d.user_id].username == "doctor01")
        live_day, live_start = demo_live_slot()
        assert not any(
            appt.doctor_id == doctor01.doctor_id
            and appt.appointment_date == live_day
            and appt.start_time == live_start
            for appt in active
        )

        for invoice in invoices:
            total = sum((item.quantity * item.unit_price for item in items
                         if item.invoice_id == invoice.invoice_id), Decimal("0.00"))
            payment = next((p for p in payments if p.invoice_id == invoice.invoice_id), None)
            assert invoice.total_amount == total
            assert (invoice.status == "PAID") == (payment is not None)
            if payment is not None:
                assert payment.amount == total

        before = Counter((appt.appointment_id, appt.status) for appt in appointments)
        assert seed_database(session) is False
        after = Counter((appt.appointment_id, appt.status) for appt in
                        session.execute(select(Appointment)).scalars().all())
        assert after == before
