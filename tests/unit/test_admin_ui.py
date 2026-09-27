"""Layout and accessibility regressions for the Admin desktop shell."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QPushButton,
    QTableWidget,
    QWidget,
)

from frontend.api_client import api_client
from frontend.pages import admin_ui
from frontend.pages.admin_ui import AdminApiError, AdminApiPage, require_success
from frontend.style import APP_STYLE
from frontend.ui.design_system import ViewState
from frontend.widgets.state_host import StateHost


class _Response:
    status_code = 200

    def __init__(self, data: object) -> None:
        self._data = data

    def json(self) -> object:
        return self._data


class _DeferredPool:
    def __init__(self) -> None:
        self.workers = []

    def start(self, worker) -> None:
        self.workers.append(worker)


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    previous_style = application.styleSheet()
    application.setStyleSheet(APP_STYLE)
    yield application
    application.setStyleSheet(previous_style)


@pytest.fixture
def admin_window(monkeypatch: pytest.MonkeyPatch, qt_app: QApplication):
    long_name = "Nguyễn Văn Quản Trị Viên Có Tên Rất Dài " * 2
    data = {
        "/users/": [
            {
                "UserID": 1,
                "Username": "admin-with-a-very-long-username",
                "FullName": long_name,
                "Role": "ADMIN",
                "IsActive": True,
            }
        ],
        "/doctors/": [
            {
                "DoctorID": 1,
                "FullName": long_name,
                "SpecialtyName": "Chuyên khoa tim mạch can thiệp",
                "ClinicName": "Phòng khám trung tâm thành phố",
                "LicenseNumber": "CCHN-123456789",
                "IsActive": True,
            }
        ],
        "/specialties/": [
            {
                "SpecialtyID": 1,
                "SpecialtyName": "Tim mạch can thiệp và phục hồi",
                "Description": "Mô tả chuyên khoa " * 20,
                "IsActive": True,
            }
        ],
        "/clinics/": [
            {
                "ClinicID": 1,
                "ClinicName": "Phòng khám trung tâm thành phố",
                "Address": "123 Đường Nguyễn Văn Cừ, Phường 4, Quận 5 " * 5,
                "Phone": "0901234567",
                "IsActive": True,
            }
        ],
        "/schedules/": [
            {
                "ScheduleID": 1,
                "DoctorID": 1,
                "DayOfWeek": 2,
                "StartTime": "08:00:00",
                "EndTime": "17:00:00",
            }
        ],
        "/statistics/overview": {
            "total_users": 100,
            "total_doctors": 20,
            "total_clinics": 5,
            "total_specialties": 12,
            "total_schedules": 35,
            "doctors_by_specialty": [
                {"name": "Tim mạch can thiệp và phục hồi", "count": 10}
            ],
            "doctors_by_clinic": [
                {"name": "Phòng khám trung tâm thành phố", "count": 12}
            ],
        },
    }

    def fake_get(path: str, *args: object, **kwargs: object) -> _Response:  # noqa: ARG001
        return _Response(data[path])

    monkeypatch.setattr(api_client, "get", fake_get)

    from frontend.admin_dashboard import AdminDashboard

    window = AdminDashboard()
    window.resize(1100, 680)
    window.show()
    qt_app.processEvents()
    yield window
    window.close()
    window.deleteLater()
    qt_app.processEvents()


def test_minimum_admin_window_uses_compact_sidebar_and_tables_fit(
    admin_window,
    qt_app: QApplication,
) -> None:
    assert admin_window._sidebar_compact is True
    assert admin_window.sidebar.width() == admin_window.COMPACT_SIDEBAR_WIDTH
    assert admin_window.user_card.styleSheet() == ""

    for page_index in range(admin_window.pages.count()):
        admin_window.menu.setCurrentRow(page_index)
        qt_app.processEvents()
        page = admin_window.pages.currentWidget()
        for table in page.findChildren(QTableWidget):
            assert table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
            assert table.horizontalScrollBar().maximum() == 0
            assert table.accessibleName()
            for row in range(table.rowCount()):
                for column in range(table.columnCount()):
                    item = table.item(row, column)
                    if item is None:
                        continue
                    assert item.toolTip()
                    assert item.data(Qt.ItemDataRole.AccessibleTextRole)

    admin_window.resize(1280, 800)
    qt_app.processEvents()
    assert admin_window._sidebar_compact is False
    assert admin_window.sidebar.width() == admin_window.EXPANDED_SIDEBAR_WIDTH


def test_statistics_cards_reflow_without_duplicates(
    admin_window,
    qt_app: QApplication,
) -> None:
    admin_window.resize(1100, 680)
    admin_window.menu.setCurrentRow(5)
    qt_app.processEvents()
    page = admin_window.pages.currentWidget()

    assert page.cards_layout.count() == 5
    positions = [
        page.cards_layout.getItemPosition(page.cards_layout.indexOf(card))[:2]
        for card in page._stat_cards
    ]
    assert positions == [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0)]
    assert all(card._title_label.wordWrap() for card in page._stat_cards)

    admin_window.resize(1280, 800)
    qt_app.processEvents()
    positions = [
        page.cards_layout.getItemPosition(page.cards_layout.indexOf(card))[:2]
        for card in page._stat_cards
    ]
    assert positions == [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)]

    page.load_data()
    qt_app.processEvents()
    assert page.cards_layout.count() == 5
    assert len({id(card) for card in page._stat_cards}) == 5

    admin_window.resize(1560, 900)
    qt_app.processEvents()
    assert all(
        page.cards_layout.getItemPosition(page.cards_layout.indexOf(card))[0] == 0
        for card in page._stat_cards
    )


def test_admin_sidebar_boundary_does_not_reduce_stat_card_columns(
    admin_window,
    qt_app: QApplication,
) -> None:
    admin_window.menu.setCurrentRow(5)
    page = admin_window.pages.currentWidget()

    admin_window.resize(admin_window.COMPACT_BREAKPOINT - 1, 680)
    qt_app.processEvents()
    compact_columns = page._card_column_count()
    assert admin_window._sidebar_compact is True

    admin_window.resize(admin_window.COMPACT_BREAKPOINT, 680)
    qt_app.processEvents()
    expanded_columns = page._card_column_count()
    assert admin_window._sidebar_compact is False

    assert compact_columns == expanded_columns == 3


def test_all_admin_pages_use_explicit_content_state(
    admin_window,
    qt_app: QApplication,
) -> None:
    for page_index in range(admin_window.pages.count()):
        admin_window.menu.setCurrentRow(page_index)
        qt_app.processEvents()
        page = admin_window.pages.currentWidget()

        assert isinstance(page.state_host, StateHost)
        assert page.state_host.state in ViewState
        assert page.state_host.content_widget.findChildren(QTableWidget)


def test_admin_state_host_distinguishes_empty_and_error_and_retries(
    monkeypatch: pytest.MonkeyPatch,
    qt_app: QApplication,
) -> None:
    pool = _DeferredPool()

    class _ThreadPoolProxy:
        @staticmethod
        def globalInstance():  # noqa: N802
            return pool

    monkeypatch.setattr(admin_ui, "QThreadPool", _ThreadPoolProxy)
    page = AdminApiPage()
    retry_calls: list[str] = []
    empty_calls: list[str] = []
    host = page.bind_state_host(
        QWidget(),
        lambda: retry_calls.append("retry"),
        empty_title="Chưa có bản ghi",
        empty_description="Hãy tạo bản ghi đầu tiên.",
        empty_action_text="Tạo mới",
        on_empty_action=lambda: empty_calls.append("create"),
    )

    assert page.run_admin_task(
        "load-empty",
        list,
        lambda _items: None,
        stateful=True,
        empty_when=lambda items: not items,
    )
    assert host.state is ViewState.LOADING
    assert not page.loading.isVisible()

    pool.workers.pop(0).run()
    qt_app.processEvents()
    assert host.state is ViewState.EMPTY
    assert host.empty.title_label.text() == "Chưa có bản ghi"
    host.empty.action_button.click()
    assert empty_calls == ["create"]

    def fail_request():
        raise AdminApiError("Máy chủ tạm thời không phản hồi.", 500)

    assert page.run_admin_task(
        "load-error",
        fail_request,
        lambda _items: None,
        stateful=True,
    )
    pool.workers.pop(0).run()
    qt_app.processEvents()
    assert host.state is ViewState.ERROR
    assert host.error.description_label.text() == "Máy chủ tạm thời không phản hồi."
    host.error.action_button.click()
    assert retry_calls == ["retry"]

    page.deleteLater()
    qt_app.processEvents()


def test_admin_task_is_non_blocking_and_rejects_duplicate_submission(
    monkeypatch: pytest.MonkeyPatch,
    qt_app: QApplication,
) -> None:
    pool = _DeferredPool()

    class _ThreadPoolProxy:
        @staticmethod
        def globalInstance():  # noqa: N802
            return pool

    monkeypatch.setattr(admin_ui, "QThreadPool", _ThreadPoolProxy)
    page = AdminApiPage()
    submit = QPushButton("Lưu", page)
    results = []

    assert page.run_admin_task(
        "save",
        lambda: "ok",
        results.append,
        controls=(submit,),
    )
    assert not page.run_admin_task("save", lambda: "duplicate", results.append)
    assert not submit.isEnabled()
    assert len(pool.workers) == 1

    pool.workers[0].run()
    qt_app.processEvents()

    assert results == ["ok"]
    assert submit.isEnabled()
    assert not page.has_pending_task("save")
    page.deleteLater()


def test_admin_http_error_is_normalized_for_feedback(qt_app: QApplication) -> None:
    page = AdminApiPage()

    with pytest.raises(RuntimeError, match="Không thể tải dữ liệu"):
        require_success(_ResponseWithStatus(500), "Không thể tải dữ liệu")

    page.deleteLater()
    qt_app.processEvents()


class _ResponseWithStatus(_Response):
    def __init__(self, status_code: int) -> None:
        super().__init__({})
        self.status_code = status_code
