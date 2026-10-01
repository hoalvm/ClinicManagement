"""Layout and accessibility regressions for the Admin desktop shell."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QPushButton,
    QWidget,
)

from frontend.api_client import api_client
from frontend.pages import admin_ui
from frontend.pages.admin_ui import (
    AdminApiError,
    AdminApiPage,
    AdminRowActions,
    require_success,
)
from frontend.style import APP_STYLE
from frontend.ui.design_system import ViewState
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.app_sidebar import AppSidebar
from frontend.widgets.combo_box import ChevronComboBox
from frontend.widgets.filter_toolbar import FilterToolbar
from frontend.widgets.form_field import FormField
from frontend.widgets.state_host import StateHost
from frontend.widgets.table_actions import TableActionMenu


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


def _drain_admin_workers(qt_app: QApplication) -> None:
    """Wait for the intentionally asynchronous Admin request, then deliver signals."""

    QThreadPool.globalInstance().waitForDone(2000)
    qt_app.processEvents()


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
                "SpecialtyID": 1,
                "ClinicID": 1,
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
                "SlotDuration": 30,
                "IsActive": True,
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
    _drain_admin_workers(qt_app)
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
    assert isinstance(admin_window.sidebar, AppSidebar)
    assert admin_window.sidebar.styleSheet() == ""

    for route in admin_window._routes:
        admin_window._navigate(route)
        _drain_admin_workers(qt_app)
        page = admin_window.pages.currentWidget()
        for table in page.findChildren(AdaptiveDataTable):
            assert table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
            assert table.horizontalScrollBar().maximum() == 0, (
                route,
                table.accessibleName(),
                table.viewport().width(),
                [table.columnWidth(index) for index in range(len(table.column_specs))],
            )
            assert table.accessibleName()
            assert all(
                spec.maximum_width is not None for spec in table.column_specs
            )

    admin_window.resize(1280, 800)
    qt_app.processEvents()
    assert admin_window._sidebar_compact is False
    assert admin_window.sidebar.width() == admin_window.EXPANDED_SIDEBAR_WIDTH


def test_user_role_filter_uses_role_code_instead_of_display_label(
    admin_window,
    qt_app: QApplication,
) -> None:
    admin_window._navigate("users")
    _drain_admin_workers(qt_app)
    page = admin_window.pages.currentWidget()

    page.role_filter.setCurrentIndex(page.role_filter.findData("PATIENT"))
    page._apply_filter()
    # No PATIENT in the fixture: the table shows one placeholder "no match" row.
    assert page.table.model().rowCount() == 1
    first_cell_text = page.table.data_model.item(0, 1).text()
    assert "ph\u00f9 h\u1ee3p" in first_cell_text or "b\u1ed9 l\u1ecdc" in first_cell_text

    page.role_filter.setCurrentIndex(page.role_filter.findData("ADMIN"))
    page._apply_filter()
    assert page.table.model().rowCount() == 1
    # The ADMIN row must be a real data row (has a numeric id in column 0).
    admin_id_text = page.table.data_model.item(0, 0).text()
    assert admin_id_text.isdigit() or admin_id_text == "1"


def test_admin_edit_callback_ignores_qt_checked_argument(qt_app: QApplication) -> None:
    selected: list[dict[str, int]] = []
    user = {"UserID": 17}
    actions = AdminRowActions(
        "tai khoan patient17",
        on_edit=lambda item=user: selected.append(item),
    )

    assert actions.edit_button is not None
    actions.edit_button.click()

    assert selected == [user]
    actions.deleteLater()
    qt_app.processEvents()


def test_statistics_cards_reflow_without_duplicates(
    admin_window,
    qt_app: QApplication,
) -> None:
    admin_window.resize(1100, 680)
    admin_window._navigate("statistics")
    _drain_admin_workers(qt_app)
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
    _drain_admin_workers(qt_app)
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
    admin_window._navigate("statistics")
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
    for route in admin_window._routes:
        admin_window._navigate(route)
        _drain_admin_workers(qt_app)
        page = admin_window.pages.currentWidget()

        assert isinstance(page.state_host, StateHost)
        assert page.state_host.state in ViewState
        assert page.state_host.content_widget.findChildren(AdaptiveDataTable)


def test_admin_crud_pages_are_list_first_with_dialog_ctas(
    admin_window,
    qt_app: QApplication,
) -> None:
    expected = {
        "users": "Tạo tài khoản",
        "doctors": "Thêm bác sĩ",
        "specialties": "Thêm chuyên khoa",
        "clinics": "Thêm phòng khám",
        "schedules": "Thêm lịch trực",
    }
    for route, action_label in expected.items():
        admin_window._navigate(route)
        _drain_admin_workers(qt_app)
        page = admin_window.pages.currentWidget()
        assert page.header.action_button.text() == action_label
        assert page.table.data_model.rowCount() == 1
        menus = page.table.findChildren(TableActionMenu)
        assert menus
        assert all(menu.text() == "⋯" for menu in menus)


def test_admin_grouped_cells_keep_full_secondary_information(
    admin_window,
    qt_app: QApplication,
) -> None:
    admin_window._navigate("doctors")
    _drain_admin_workers(qt_app)
    page = admin_window.pages.currentWidget()
    doctor_item = page.table.data_model.item(0, 1)
    assert "CCHN-123456789" in doctor_item.toolTip()
    assert "số giấy phép hành nghề" in doctor_item.accessibleText()
    assert page.table.column_specs[1].line_limit == 2


def test_admin_search_uses_shared_debounced_filter_toolbar(
    admin_window,
    qt_app: QApplication,
) -> None:
    for route in ("users", "doctors", "clinics"):
        admin_window._navigate(route)
        _drain_admin_workers(qt_app)
        page = admin_window.pages.currentWidget()
        assert isinstance(page.search, FilterToolbar)
        page.search.set_debounce_ms(0)
        page.search.search_input.setText("không tồn tại")
        qt_app.processEvents()
        # May be 0 (empty table) or 1 (no-match placeholder row), but never more.
        assert page.table.data_model.rowCount() <= 1
        assert page.search.clear_button.isVisible()
        page.search.clear()
        qt_app.processEvents()
        assert page.table.data_model.rowCount() == 1


def test_admin_dialogs_use_form_fields_and_painted_combos(
    admin_window,
    qt_app: QApplication,
) -> None:
    for route in ("users", "doctors", "specialties", "clinics", "schedules"):
        admin_window._navigate(route)
        _drain_admin_workers(qt_app)
        page = admin_window.pages.currentWidget()
        built = page._build_dialog()
        dialog = built[0]
        fields = dialog.findChildren(FormField)
        assert fields
        enabled_before = [field.control.isEnabled() for field in fields]
        dialog.set_busy(True)
        assert not any(field.control.isEnabled() for field in fields)
        dialog.set_busy(False)
        assert [field.control.isEnabled() for field in fields] == enabled_before
        for combo in dialog.findChildren(ChevronComboBox):
            assert combo.property("paintedChevron") is True
        dialog.reject()
        dialog.deleteLater()
    qt_app.processEvents()


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


# ---------------------------------------------------------------------------
# New tests added as part of P0-P3 upgrade
# ---------------------------------------------------------------------------

def test_feedback_banner_success_timeout_is_two_seconds(qt_app: QApplication) -> None:
    """Success banner must auto-dismiss after 2000 ms (±250 ms tolerance)."""
    from frontend.ui.design_system import FeedbackSeverity
    from frontend.widgets.feedback_banner import _TIMEOUT_MS, FeedbackBanner

    banner = FeedbackBanner()
    assert _TIMEOUT_MS[FeedbackSeverity.SUCCESS] == 2000
    assert _TIMEOUT_MS[FeedbackSeverity.INFO] == 2500
    assert _TIMEOUT_MS[FeedbackSeverity.WARNING] == 5000
    assert _TIMEOUT_MS[FeedbackSeverity.ERROR] == 5000

    banner.show_message("Đã lưu", "Thông tin đã được cập nhật.", severity="success")
    assert banner.isVisible()
    assert banner._dismiss_timer.isActive()
    remaining = banner._dismiss_timer.remainingTime()
    # Must be within [1750, 2250] ms immediately after start.
    assert 1750 <= remaining <= 2250, f"Timer not in 2s window: {remaining}ms"

    # A second show_message must reset the timer.
    banner.show_message("Mới", "Thông báo mới.", severity="success")
    remaining2 = banner._dismiss_timer.remainingTime()
    assert 1750 <= remaining2 <= 2250

    banner.clear()
    assert not banner.isVisible()
    assert not banner._dismiss_timer.isActive()
    banner.deleteLater()
    qt_app.processEvents()


def test_feedback_banner_has_manual_close_button(qt_app: QApplication) -> None:
    """Banner must expose a × button that clears the banner immediately."""
    from frontend.widgets.feedback_banner import FeedbackBanner

    banner = FeedbackBanner()
    banner.show_message("Info", "Test", severity="info")
    assert banner.isVisible()
    banner._close_btn.click()
    assert not banner.isVisible()
    banner.deleteLater()
    qt_app.processEvents()


def test_connect_action_ignores_qt_checked_bool(qt_app: QApplication) -> None:
    """connect_action must discard the checked:bool argument Qt passes to callbacks."""
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QPushButton

    from frontend.pages.admin_ui import connect_action

    calls: list[object] = []
    row = {"DoctorID": 42}

    btn = QPushButton("Test")
    connect_action(btn.clicked, lambda item=row: calls.append(item))
    btn.click()
    assert calls == [row], f"Expected [{row!r}], got {calls!r}"

    calls.clear()
    action = QAction("Test")
    connect_action(action.triggered, lambda item=row: calls.append(item))
    action.trigger()
    assert calls == [row]

    btn.deleteLater()
    qt_app.processEvents()


def test_role_filter_normalizes_lowercase_role_from_api(
    admin_window,
    qt_app: QApplication,
) -> None:
    """Role codes from API normalized with strip().upper() before comparison."""
    admin_window._navigate("users")
    _drain_admin_workers(qt_app)
    page = admin_window.pages.currentWidget()

    # Inject a user whose Role comes back lowercase from the API.
    page._all_users = [
        {"UserID": 99, "Username": "testuser", "FullName": "Test", "Role": "admin", "IsActive": True},
    ]
    page.role_filter.setCurrentIndex(page.role_filter.findData("ADMIN"))
    page._apply_filter()
    # The lowercase "admin" must be matched after normalization.
    row_count = page.table.data_model.rowCount()
    assert row_count == 1
    id_text = page.table.data_model.item(0, 0).text()
    assert str(id_text) == "99"


def test_clinic_status_filter_is_available(
    admin_window,
    qt_app: QApplication,
) -> None:
    """ClinicManagementPage must expose a status_filter combobox."""
    admin_window._navigate("clinics")
    _drain_admin_workers(qt_app)
    page = admin_window.pages.currentWidget()
    assert hasattr(page, "status_filter"), "ClinicManagementPage must have status_filter"
    # Default: all clinics visible (active_filter=None).
    assert page.status_filter.currentData() is None


def test_admin_row_cannot_be_locked_in_user_management(
    admin_window,
    qt_app: QApplication,
) -> None:
    """The system admin row must not expose 'Khóa tài khoản' in its actions."""
    admin_window._navigate("users")
    _drain_admin_workers(qt_app)
    page = admin_window.pages.currentWidget()

    page._all_users = [
        {"UserID": 1, "Username": "admin", "FullName": "Quản trị viên", "Role": "ADMIN", "IsActive": True},
        {"UserID": 2, "Username": "staff01", "FullName": "Nhân viên", "Role": "STAFF", "IsActive": True},
    ]
    page._apply_filter()

    # Row 0: admin -> overflow menu should not contain "Khóa tài khoản"
    widget_admin = page.table.indexWidget(page.table.data_model.index(0, 4))
    assert widget_admin is not None
    admin_menu = widget_admin.more_button.menu()
    admin_actions = [a.text() for a in admin_menu.actions()]
    assert "Khóa tài khoản" not in admin_actions

    # Row 1: staff01 -> overflow menu should contain "Khóa tài khoản"
    widget_staff = page.table.indexWidget(page.table.data_model.index(1, 4))
    assert widget_staff is not None
    staff_menu = widget_staff.more_button.menu()
    staff_actions = [a.text() for a in staff_menu.actions()]
    assert "Khóa tài khoản" in staff_actions

