"""Focused regression tests for the shared PySide UI foundation."""

from collections.abc import Iterator

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QLineEdit, QWidget

from frontend.core.i18n import t
from frontend.style import APP_STYLE
from frontend.ui.design_system import (
    UI_TOKENS,
    ColumnPriority,
    ColumnSpec,
    FeedbackSeverity,
    SurfaceRole,
    ViewState,
    set_surface_role,
)
from frontend.widgets.adaptive_data_table import RAW_VALUE_ROLE, AdaptiveDataTable
from frontend.widgets.app_sidebar import AppSidebar, NavigationItem
from frontend.widgets.application_shell import ApplicationShell
from frontend.widgets.combo_box import ChevronComboBox
from frontend.widgets.feedback_banner import FeedbackBanner
from frontend.widgets.form_field import FormField
from frontend.widgets.page_header import PageHeader
from frontend.widgets.pagination import PaginationWidget
from frontend.widgets.responsive_page import ResponsivePage
from frontend.widgets.stat_card import StatCard
from frontend.widgets.state_host import StateHost
from frontend.widgets.status_badge import display_status


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    application.setStyleSheet(APP_STYLE)
    yield application


def test_design_contracts_validate_and_normalize_legacy_values() -> None:
    assert FeedbackSeverity.coerce("danger") is FeedbackSeverity.ERROR
    assert FeedbackSeverity.coerce("unknown") is FeedbackSeverity.INFO
    assert ViewState.coerce("loading") is ViewState.LOADING

    with pytest.raises(ValueError, match="minimum_width"):
        ColumnSpec("Name", minimum_width=20)
    with pytest.raises(ValueError, match="preferred_width"):
        ColumnSpec("Name", minimum_width=100, preferred_width=80)


def test_bare_widgets_are_not_forced_to_page_background(qt_app: QApplication) -> None:
    compact_style = "".join(APP_STYLE.split())

    assert "QWidget{background-color:#F4F7FB" not in compact_style
    assert 'QWidget#pageRoot,QWidget[uiSurface="page"]' in compact_style

    wrapper = QWidget()
    set_surface_role(wrapper, SurfaceRole.TRANSPARENT)
    assert wrapper.property("uiSurface") == "transparent"
    wrapper.deleteLater()
    qt_app.processEvents()


def test_form_field_exposes_inline_error_to_style_and_accessibility(
    qt_app: QApplication,
) -> None:
    control = QLineEdit()
    field = FormField("Số điện thoại", control, required=True)

    field.set_error("Số điện thoại không hợp lệ")

    assert control.property("hasError") is True
    assert control.accessibleName() == "Số điện thoại"
    assert control.accessibleDescription() == "Số điện thoại không hợp lệ"
    assert not field.error_label.isHidden()

    field.clear_error()

    assert control.property("hasError") is False
    assert control.accessibleDescription() == ""
    assert field.error_label.isHidden()
    field.deleteLater()
    qt_app.processEvents()


def test_feedback_banner_supports_warning_and_danger_alias(qt_app: QApplication) -> None:
    banner = FeedbackBanner()

    banner.show_message("Cảnh báo", "Kiểm tra dữ liệu", severity="warning")
    assert banner.severity is FeedbackSeverity.WARNING
    assert banner.property("severity") == "warning"

    banner.show_message("Lỗi", "Không thể lưu", severity="danger")
    assert banner.severity is FeedbackSeverity.ERROR
    assert banner.accessibleName() == "Lỗi. Không thể lưu"
    banner.deleteLater()
    qt_app.processEvents()


def test_adaptive_table_is_read_only_and_preserves_raw_status(
    qt_app: QApplication,
) -> None:
    columns = [
        ColumnSpec(
            "Bệnh nhân",
            key="patient",
            minimum_width=140,
            preferred_width=220,
            priority=ColumnPriority.CRITICAL,
            stretch=True,
        ),
        ColumnSpec(
            "Trạng thái",
            key="status",
            minimum_width=130,
            priority=ColumnPriority.CRITICAL,
            status=True,
        ),
    ]
    table = AdaptiveDataTable(columns, accessible_name="Danh sách lịch hẹn")
    table.set_rows([{"patient": "Nguyễn Văn Bệnh Nhân", "status": "PAID"}])

    assert table.editTriggers() == table.EditTrigger.NoEditTriggers
    assert table.model().rowCount() == 1
    assert table.model().item(0, 0).toolTip() == "Nguyễn Văn Bệnh Nhân"
    assert not table.model().item(0, 0).isEditable()
    assert table.model().item(0, 1).data(RAW_VALUE_ROLE) == "PAID"
    assert table.model().item(0, 1).text() == display_status("PAID")
    assert table.accessibleDescription() == t("a11y_read_only_table")
    table.deleteLater()
    qt_app.processEvents()


def test_adaptive_table_rejects_multiple_stretch_columns() -> None:
    with pytest.raises(ValueError, match="Only one"):
        AdaptiveDataTable(
            [
                ColumnSpec("A", stretch=True),
                ColumnSpec("B", stretch=True),
            ]
        )


def test_page_header_and_pagination_reflow_at_compact_width(
    qt_app: QApplication,
) -> None:
    header = PageHeader("Quản lý lịch hẹn", "Thông tin hỗ trợ", action_label="Tạo mới")
    header.resize(900, 140)
    header._reflow(force=True)
    assert not header.is_compact

    header.resize(600, 180)
    header._reflow(force=True)
    assert header.is_compact

    pagination = PaginationWidget()
    pagination.resize(800, 100)
    pagination._place_controls(compact=False)
    assert not pagination.is_compact
    pagination.resize(500, 120)
    pagination._place_controls(compact=True)
    assert pagination.is_compact

    header.deleteLater()
    pagination.deleteLater()
    qt_app.processEvents()


def test_state_host_keeps_empty_and_error_states_distinct(qt_app: QApplication) -> None:
    host = StateHost(QWidget())
    retries: list[bool] = []
    host.retry_requested.connect(lambda: retries.append(True))

    host.show_empty("Chưa có lịch hẹn", "Hãy tạo lịch hẹn đầu tiên.", action_text="Đặt lịch")
    assert host.state is ViewState.EMPTY
    assert host.stack.currentWidget() is host.empty

    host.show_error("Mất kết nối", "Không thể tải dữ liệu.")
    assert host.state is ViewState.ERROR
    assert host.stack.currentWidget() is host.error
    host.error.action_requested.emit()
    assert retries == [True]

    host.show_content()
    assert host.state is ViewState.CONTENT
    host.deleteLater()
    qt_app.processEvents()


def test_responsive_page_disables_page_level_horizontal_scroll(
    qt_app: QApplication,
) -> None:
    page = ResponsivePage(compact_breakpoint=900)
    page.resize(720, 500)
    page.show()
    qt_app.processEvents()

    assert page.horizontalScrollBarPolicy() is Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert page.is_compact
    assert page.content_widget.property("uiSurface") == "transparent"
    page.deleteLater()
    qt_app.processEvents()


def test_painted_combo_chevron_and_stat_card_render_without_inline_styles(
    qt_app: QApplication,
) -> None:
    combo = ChevronComboBox()
    combo.addItems(["Một", "Hai"])
    combo.resize(180, 40)
    card = StatCard("Bác sĩ hoạt động trong ngày", 12)
    card.resize(260, 100)

    image = QImage(180, 40, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    combo.render(image)

    assert combo.property("paintedChevron") is True
    assert card.accent_bar.styleSheet() == ""
    assert card._title_label.wordWrap()
    combo.deleteLater()
    card.deleteLater()
    qt_app.processEvents()


def test_app_sidebar_preserves_navigation_accessibility_when_compact(
    qt_app: QApplication,
) -> None:
    sidebar = AppSidebar(
        [
            NavigationItem("dashboard", "Tổng quan", "dashboard", "NGHIỆP VỤ"),
            NavigationItem("appointments", "Lịch hẹn", "calendar", "NGHIỆP VỤ"),
        ]
    )
    sidebar.set_user({"full_name": "Nguyễn Văn An", "role": "DOCTOR"}, role_label="Bác sĩ")
    sidebar.set_active("appointments")
    sidebar.set_compact(True)

    assert sidebar.width() == AppSidebar.COMPACT_WIDTH
    assert sidebar.active_route == "appointments"
    assert sidebar._buttons["appointments"].isChecked()
    assert sidebar._buttons["appointments"].text() == ""
    assert sidebar._buttons["appointments"].accessibleName() == "Lịch hẹn"
    assert not sidebar._buttons["appointments"].icon().isNull()
    assert "Nguyễn Văn An" in sidebar._user_row.accessibleName()
    sidebar.deleteLater()
    qt_app.processEvents()


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]

    def linearize(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linearize(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast_ratio(foreground: str, background: str) -> float:
    light, dark = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)),
        reverse=True,
    )
    return (light + 0.05) / (dark + 0.05)


def test_normal_text_tokens_meet_wcag_aa_contrast() -> None:
    assert _contrast_ratio(UI_TOKENS.text, UI_TOKENS.surface) >= 4.5
    assert _contrast_ratio(UI_TOKENS.text_muted, UI_TOKENS.surface) >= 4.5
    assert _contrast_ratio(UI_TOKENS.text, UI_TOKENS.page_background) >= 4.5
    assert _contrast_ratio(UI_TOKENS.brand, UI_TOKENS.surface) >= 4.5


def test_application_shell_owns_zero_gap_role_layout(qt_app: QApplication) -> None:
    sidebar = QWidget()
    workspace = QWidget()
    shell = ApplicationShell(sidebar, workspace)

    assert shell.layout().contentsMargins().left() == 0
    assert shell.layout().spacing() == 0
    assert shell.sidebar is sidebar
    assert shell.workspace is workspace

    shell.deleteLater()
    qt_app.processEvents()
