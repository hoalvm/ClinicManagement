"""Production leave is shown with its actual scope and active state."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from frontend.pages.schedule_exception_management import ScheduleExceptionManagementPage
from frontend.widgets.adaptive_data_table import RAW_VALUE_ROLE


def test_schedule_exception_page_shows_full_and_partial_closures() -> None:
    application = QApplication.instance() or QApplication([])
    page = ScheduleExceptionManagementPage()
    page._populate(
        (
            [{"DoctorID": 7, "FullName": "Bác sĩ Nguyễn An", "IsActive": True}],
            [
                {
                    "exception_id": 1,
                    "doctor_id": 7,
                    "exception_date": "2026-10-08",
                    "start_time": None,
                    "end_time": None,
                    "reason": "Nghỉ phép đã duyệt",
                    "is_active": True,
                },
                {
                    "exception_id": 2,
                    "doctor_id": 7,
                    "exception_date": "2026-10-09",
                    "start_time": "13:00:00",
                    "end_time": "15:00:00",
                    "reason": "Đào tạo nội bộ",
                    "is_active": False,
                },
            ],
        )
    )
    model = page.table.model()
    assert model.rowCount() == 2
    assert model.index(0, 2).data() == "Cả ngày"
    assert model.index(1, 2).data() == "13:00–15:00"
    assert model.index(0, 4).data(RAW_VALUE_ROLE) == "ACTIVE"
    assert model.index(1, 4).data(RAW_VALUE_ROLE) == "INACTIVE"
    assert page.table.indexWidget(model.index(0, 5)) is not None
    assert page.table.indexWidget(model.index(1, 5)) is None
    page.close()
    application.processEvents()
