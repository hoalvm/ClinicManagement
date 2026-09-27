"""Focused regression tests for the second Staff UX pass."""

from collections.abc import Callable, Iterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from frontend.api.api_client import ApiClient
from frontend.views.book_for_patient_view import BookForPatientView
from frontend.views.common import BaseApiView
from frontend.widgets.adaptive_data_table import (
    RAW_VALUE_ROLE,
    SECONDARY_TEXT_ROLE,
    AdaptiveDataTable,
)


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def booking_view(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[BookForPatientView]:
    monkeypatch.setattr(BaseApiView, "run_api_task", lambda *_args, **_kwargs: False)
    view = BookForPatientView(MagicMock(spec=ApiClient))
    yield view
    view.deleteLater()
    qt_app.processEvents()


def test_booking_starts_nullable_and_progressively_reveals_history(
    booking_view: BookForPatientView,
) -> None:
    assert booking_view.header.title == "Đặt lịch hộ"
    assert booking_view.gender_combo.currentData() is None
    assert booking_view.dob_edit.date() == booking_view.NULL_DATE
    assert not booking_view.history_card.isVisible()
    assert booking_view.footer.parent() is booking_view

    booking_view._select_patient(
        {
            "patient_id": 17,
            "full_name": "Nguyễn Văn An",
            "phone": "0900000001",
            "gender": None,
            "date_of_birth": None,
            "address": "",
        }
    )

    assert booking_view.name_input.isReadOnly()
    assert booking_view.phone_input.isReadOnly()
    assert not booking_view.gender_combo.isEnabled()
    assert not booking_view.dob_edit.isEnabled()
    assert not booking_view.history_card.isHidden()
    assert booking_view.btn_unselect_pt.text() == "Đổi bệnh nhân"


def test_booking_uses_catalog_names_and_only_api_available_slots(
    booking_view: BookForPatientView,
) -> None:
    booking_view._on_doctors_loaded(
        [
            {
                "doctor_id": 8,
                "full_name": "BS. CKI Nguyễn Minh Anh",
                "specialty_name": "Nội tổng quát",
            }
        ]
    )
    assert booking_view.doctor_combo.itemText(1).startswith("BS. CKI Nguyễn Minh Anh")
    assert "BS. BS." not in booking_view.doctor_combo.itemText(1)

    booking_view._on_slots_loaded(
        {
            "has_schedule": True,
            "slots": [
                {
                    "start_time": "08:00:00",
                    "end_time": "08:30:00",
                    "is_available": True,
                },
                {
                    "start_time": "08:30:00",
                    "end_time": "09:00:00",
                    "is_available": False,
                },
            ],
        }
    )
    assert booking_view.time_combo.count() == 2
    assert booking_view.time_combo.itemData(1) == ("08:00", "08:30")
    assert booking_view.time_combo.findText("08:30–09:00") == -1

    booking_view._on_doctors_loaded([])
    assert booking_view.doctor_combo.count() == 1
    assert booking_view.doctor_combo.currentData() is None


def test_embedded_patient_tables_use_adaptive_two_line_cells(
    booking_view: BookForPatientView,
    qt_app: QApplication,
) -> None:
    assert isinstance(booking_view.search_results_table, AdaptiveDataTable)
    assert isinstance(booking_view.history_table, AdaptiveDataTable)
    patients = [
        {
            "patient_id": patient_id,
            "full_name": f"Bệnh nhân {patient_id}",
            "phone": f"090000000{patient_id}",
            "date_of_birth": "1990-01-02",
        }
        for patient_id in (1, 2)
    ]
    booking_view._on_patient_search_results(patients)

    assert booking_view.search_results_table.model().rowCount() == 2
    assert (
        booking_view.search_results_table.model()
        .index(0, 0)
        .data(SECONDARY_TEXT_ROLE)
        == "0900000001"
    )
    assert (
        booking_view.search_results_table.indexWidget(
            booking_view.search_results_table.model().index(0, 2)
        )
        is not None
    )

    booking_view._on_history_loaded(
        {
            "items": [
                {
                    "appointment_date": f"2026-09-{day:02d}",
                    "doctor": {"full_name": f"Bác sĩ {day}"},
                    "status": "CONFIRMED",
                }
                for day in range(1, 6)
            ]
        }
    )
    assert booking_view.history_table.model().rowCount() == 3
    assert (
        booking_view.history_table.model().index(0, 2).data(RAW_VALUE_ROLE)
        == "CONFIRMED"
    )
    booking_view.resize(1100, 700)
    booking_view.show()
    qt_app.processEvents()
    assert booking_view.search_results_table.horizontalScrollBar().maximum() == 0
    assert booking_view.history_table.horizontalScrollBar().maximum() == 0


def test_booking_slot_request_targets_real_available_slots_endpoint(
    booking_view: BookForPatientView,
) -> None:
    captured: dict[str, Any] = {}

    def capture(
        key: str,
        operation: Callable[[], Any],
        _success: object,
        **kwargs: object,
    ) -> bool:
        captured.update(key=key, operation=operation, kwargs=kwargs)
        return True

    booking_view.run_api_task = capture  # type: ignore[method-assign]
    booking_view._on_doctors_loaded(
        [{"doctor_id": 42, "full_name": "Nguyễn Minh Anh"}]
    )
    booking_view.doctor_combo.setCurrentIndex(1)
    booking_view.api_client.get.return_value = {"has_schedule": True, "slots": []}

    result = captured["operation"]()

    assert result == {"has_schedule": True, "slots": []}
    booking_view.api_client.get.assert_called_with(
        "/api/v1/catalog/doctors/42/available-slots",
        params={
            "appointment_date": booking_view.date_edit.date().toString("yyyy-MM-dd")
        },
    )


def test_existing_patient_payload_does_not_rewrite_profile_and_success_persists(
    booking_view: BookForPatientView,
) -> None:
    captured: dict[str, Any] = {}

    def capture(
        _key: str,
        operation: Callable[[], Any],
        success: Callable[[dict[str, Any]], None],
        **_kwargs: object,
    ) -> bool:
        captured.update(operation=operation, success=success)
        return True

    booking_view.run_api_task = capture  # type: ignore[method-assign]
    booking_view._on_doctors_loaded(
        [{"doctor_id": 8, "full_name": "Nguyễn Minh Anh"}]
    )
    booking_view.doctor_combo.setCurrentIndex(1)
    booking_view._on_slots_loaded(
        {
            "has_schedule": True,
            "slots": [
                {
                    "start_time": "08:00:00",
                    "end_time": "08:30:00",
                    "is_available": True,
                }
            ],
        }
    )
    booking_view.time_combo.setCurrentIndex(1)
    booking_view._select_patient(
        {
            "patient_id": 5,
            "full_name": "Trần Thị Bình",
            "phone": "0900000002",
        }
    )
    booking_view._submit_booking()
    booking_view.api_client.post.return_value = {"appointment_id": 31}

    captured["operation"]()
    payload = booking_view.api_client.post.call_args.kwargs["json"]
    assert payload["patient_id"] == 5
    assert "date_of_birth" not in payload
    assert "gender" not in payload

    captured["success"]({"appointment_id": 31})
    assert not booking_view.feedback.isHidden()
    assert booking_view.feedback.title == "Tạo lịch hẹn thành công"
    assert "#31" in booking_view.feedback.message

