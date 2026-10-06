"""Authorization and audit checks for the clinician history view."""

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from backend.app.routers import doctor_portal


@pytest.mark.parametrize(
    ("appointment", "expected_status"),
    [
        (None, 404),
        (SimpleNamespace(doctor_id=8, status="CHECKED_IN", appointment_date=date.today()), 403),
        (SimpleNamespace(doctor_id=7, status="CONFIRMED", appointment_date=date.today()), 409),
        (
            SimpleNamespace(
                doctor_id=7,
                status="CHECKED_IN",
                appointment_date=date.today() - timedelta(days=1),
            ),
            409,
        ),
    ],
)
def test_clinical_context_rejects_non_active_or_other_doctors_encounter(
    monkeypatch: pytest.MonkeyPatch, appointment: object, expected_status: int
) -> None:
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = appointment
    audit = MagicMock()
    monkeypatch.setattr(doctor_portal, "clinic_today", date.today)
    monkeypatch.setattr(doctor_portal, "record_audit_event", audit)

    with pytest.raises(HTTPException) as exc:
        doctor_portal.get_clinical_context(
            42,
            auth_info=(SimpleNamespace(user_id=19), SimpleNamespace(doctor_id=7)),
            db=session,
        )

    assert exc.value.status_code == expected_status
    audit.assert_not_called()
    session.commit.assert_not_called()


def test_production_rejects_prescription_before_writing_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock()
    session.get_bind.return_value.dialect.name = "sqlite"
    session.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        appointment_id=42,
        doctor_id=7,
        status="IN_PROGRESS",
        appointment_date=date(2026, 10, 6),
        check_in_at=datetime(2026, 10, 6, 8, 30),
        clinical_context_loaded_at=datetime(2026, 10, 6, 8, 31),
        clinical_context_loaded_by_user_id=19,
    )
    monkeypatch.setattr(
        doctor_portal, "get_settings", lambda: SimpleNamespace(app_mode="production")
    )
    monkeypatch.setattr(doctor_portal, "clinic_today", lambda: date(2026, 10, 6))
    with pytest.raises(HTTPException) as exc:
        doctor_portal.complete_examination(
            42,
            doctor_portal.CompleteExamRequest(
                symptoms="Ho",
                diagnosis="Viêm họng",
                prescription_items=[
                    doctor_portal.PrescriptionItemIn(medicine_name="Thuốc thử", quantity=1)
                ],
            ),
            auth_info=(SimpleNamespace(user_id=19), SimpleNamespace(doctor_id=7)),
            db=session,
        )

    assert exc.value.status_code == 409
    session.add.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("loaded_at", "loaded_by"),
    [
        (None, None),
        (datetime(2026, 10, 6, 8, 31), 20),
        (datetime(2026, 10, 6, 8, 29), 19),
    ],
)
def test_production_completion_requires_this_doctors_context_after_check_in(
    monkeypatch: pytest.MonkeyPatch, loaded_at: datetime | None, loaded_by: int | None
) -> None:
    session = MagicMock()
    session.get_bind.return_value.dialect.name = "sqlite"
    session.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        appointment_id=42,
        doctor_id=7,
        status="IN_PROGRESS",
        appointment_date=date(2026, 10, 6),
        check_in_at=datetime(2026, 10, 6, 8, 30),
        clinical_context_loaded_at=loaded_at,
        clinical_context_loaded_by_user_id=loaded_by,
    )
    monkeypatch.setattr(
        doctor_portal, "get_settings", lambda: SimpleNamespace(app_mode="production")
    )
    monkeypatch.setattr(doctor_portal, "clinic_today", lambda: date(2026, 10, 6))

    with pytest.raises(HTTPException) as exc:
        doctor_portal.complete_examination(
            42,
            doctor_portal.CompleteExamRequest(symptoms="Ho", diagnosis="Viêm họng"),
            auth_info=(SimpleNamespace(user_id=19), SimpleNamespace(doctor_id=7)),
            db=session,
        )

    assert exc.value.status_code == 409
    session.add.assert_not_called()
    session.commit.assert_not_called()


def test_context_marks_review_and_reports_more_than_ten_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visit_time = datetime(2026, 10, 6, 8, 30)
    now = datetime(2026, 10, 6, 8, 35)
    patient = SimpleNamespace(
        patient_id=3,
        date_of_birth=date(1991, 3, 4),
        gender="FEMALE",
        user=SimpleNamespace(full_name="Bệnh nhân thử"),
    )
    appt = SimpleNamespace(
        appointment_id=42,
        patient_id=3,
        patient=patient,
        doctor_id=7,
        clinic_id=2,
        appointment_date=date(2026, 10, 6),
        status="CHECKED_IN",
        check_in_at=visit_time,
        clinical_context_loaded_at=None,
        clinical_context_loaded_by_user_id=None,
    )
    records = [
        SimpleNamespace(
            medical_record_id=i,
            appointment_id=i,
            examination_date=now - timedelta(days=i),
            appointment=SimpleNamespace(
                doctor=SimpleNamespace(user=SimpleNamespace(full_name="Bác sĩ trước"))
            ),
            symptoms="Ho",
            diagnosis="Viêm họng",
            notes=None,
            prescription=None,
        )
        for i in range(1, 12)
    ]
    session = MagicMock()
    session.get_bind.return_value.dialect.name = "sqlite"
    visit_query = MagicMock()
    visit_query.filter.return_value.first.return_value = appt
    history_query = MagicMock()
    history_query.join.return_value.options.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = records
    session.query.side_effect = [visit_query, history_query]
    audit = MagicMock()
    monkeypatch.setattr(doctor_portal, "clinic_today", lambda: date(2026, 10, 6))
    monkeypatch.setattr(doctor_portal, "clinic_naive_now", lambda: now)
    monkeypatch.setattr(
        doctor_portal, "get_settings", lambda: SimpleNamespace(app_mode="production")
    )
    monkeypatch.setattr(doctor_portal, "record_audit_event", audit)

    response = doctor_portal.get_clinical_context(
        42,
        auth_info=(SimpleNamespace(user_id=19), SimpleNamespace(doctor_id=7)),
        db=session,
    )

    assert len(response.prior_records) == 10
    assert response.prior_records_has_more is True
    history_query.join.return_value.options.return_value.filter.return_value.order_by.return_value.limit.assert_called_once_with(11)
    assert appt.clinical_context_loaded_at == now
    assert appt.clinical_context_loaded_by_user_id == 19
    audit.assert_called_once()
    session.commit.assert_called_once()
