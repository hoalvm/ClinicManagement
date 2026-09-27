"""Appointment Management View for Receptionist / Staff."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.ui.design_system import (
    CellValue,
    ColumnDisplayMode,
    ColumnPriority,
    ColumnSpec,
)
from frontend.views.common import BaseApiView, format_date, format_time
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.filter_toolbar import FilterToolbar
from frontend.widgets.page_header import PageHeader
from frontend.widgets.pagination import Pagination
from frontend.widgets.state_host import StateHost
from frontend.widgets.status_badge import display_status
from frontend.widgets.table_actions import (
    RowAction,
    TableActionMenu,
    table_action_cell,
)


class AppointmentManagementView(BaseApiView):
    """View to filter, confirm, check-in, cancel, or reschedule appointments."""

    check_in_requested = Signal(int)
    book_requested = Signal()

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._current_page = 1
        self._page_size = 15
        self._current_items: list[dict[str, Any]] = []

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        self.header = PageHeader(
            "Lịch hẹn",
            "Theo dõi và xử lý lịch khám của bệnh nhân",
            action_label="Đặt lịch mới",
            parent=self,
        )
        self.header.action_clicked.connect(self.book_requested)
        layout.addWidget(self.header)
        layout.addWidget(self.feedback)
        layout.addWidget(self.loading)

        self.filters = FilterToolbar(
            "Tìm tên bệnh nhân, số điện thoại hoặc lý do",
            search_accessible_name="Tìm kiếm lịch hẹn",
        )
        self.search_input = self.filters.search_input
        self.status_combo = self.filters.add_filter(
            "status",
            (
                ("Tất cả trạng thái", ""),
                (display_status("PENDING", "vi"), "PENDING"),
                (display_status("CONFIRMED", "vi"), "CONFIRMED"),
                (display_status("CHECKED_IN", "vi"), "CHECKED_IN"),
                (display_status("IN_PROGRESS", "vi"), "IN_PROGRESS"),
                (display_status("COMPLETED", "vi"), "COMPLETED"),
                (display_status("CANCELLED", "vi"), "CANCELLED"),
            ),
            accessible_name="Lọc lịch hẹn theo trạng thái",
        )
        self.btn_refresh = self.filters.clear_button
        self.filters.filters_changed.connect(self._apply_filter)
        self.search_input.returnPressed.connect(self.filters.flush_search)
        layout.addWidget(self.filters)

        self.table = AdaptiveDataTable(
            [
                ColumnSpec(
                    "Mã hẹn",
                    "appointment_id",
                    minimum_width=64,
                    preferred_width=72,
                    maximum_width=88,
                    priority=ColumnPriority.HIGH,
                    formatter=lambda value: f"#{int(value or 0)}",
                    display_mode=ColumnDisplayMode.FULL,
                    preserve_full=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Thời gian",
                    "appointment_time",
                    minimum_width=116,
                    preferred_width=132,
                    maximum_width=154,
                    priority=ColumnPriority.HIGH,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Bệnh nhân",
                    "patient",
                    minimum_width=154,
                    preferred_width=190,
                    maximum_width=280,
                    priority=ColumnPriority.CRITICAL,
                    grow_weight=3,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                    stretch=True,
                ),
                ColumnSpec(
                    "Bác sĩ",
                    "doctor_name",
                    minimum_width=132,
                    preferred_width=164,
                    maximum_width=230,
                    priority=ColumnPriority.NORMAL,
                    grow_weight=2,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Trạng thái",
                    "status",
                    minimum_width=104,
                    preferred_width=112,
                    maximum_width=126,
                    priority=ColumnPriority.CRITICAL,
                    display_mode=ColumnDisplayMode.FULL,
                    preserve_full=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                    status=True,
                ),
                ColumnSpec(
                    "Thao tác",
                    "_actions",
                    minimum_width=126,
                    preferred_width=142,
                    maximum_width=154,
                    priority=ColumnPriority.CRITICAL,
                    display_mode=ColumnDisplayMode.FULL,
                    preserve_full=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
            ],
            accessible_name="Danh sách lịch hẹn",
        )
        self.table.setAccessibleDescription(
            "Bảng lịch hẹn chỉ đọc; trạng thái và thao tác chính luôn hiển thị."
        )
        self.table.setMinimumHeight(260)

        self.state_host = StateHost(self.table)
        self.bind_state_host(self.state_host)
        self.empty_state = self.state_host.empty
        self.empty_state.set_title("Không tìm thấy lịch hẹn")
        self.empty_state.set_description(
            "Thử thay đổi điều kiện tìm kiếm hoặc tạo lịch hẹn mới."
        )
        self.empty_state.set_action("Làm mới")
        self.state_host.empty_action_requested.connect(self._retry)
        self.state_host.retry_requested.connect(self._retry)
        layout.addWidget(self.state_host, 1)

        # Pagination
        self.pagination = Pagination(parent=self)
        self.pagination.page_requested.connect(self._go_to_page)
        layout.addWidget(self.pagination)

        scroll.setWidget(container)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        self.load_appointments()

    def _apply_filter(self, _values: object | None = None) -> None:
        self._current_page = 1
        self.load_appointments()

    def _clear_filters(self) -> None:
        self.filters.clear()

    def _go_to_page(self, page: int) -> None:
        self._current_page = page
        self.load_appointments()

    def load_appointments(self) -> None:
        status_param = self.status_combo.currentData() or None
        keyword_param = self.search_input.text().strip() or None

        params = {
            "page": self._current_page,
            "page_size": self._page_size,
        }
        if status_param:
            params["status"] = status_param
        if keyword_param:
            params["keyword"] = keyword_param

        self.run_api_task(
            "load_staff_appts",
            lambda: self.api_client.get("/api/v1/reception/appointments", params=params),
            self._on_appointments_loaded,
            controls=(
                self.search_input,
                self.status_combo,
                self.btn_refresh,
                self.pagination,
            ),
            loading_text="Đang tải danh sách lịch hẹn...",
        )

    def _on_appointments_loaded(self, data: dict[str, Any]) -> None:
        items = data.get("items", [])
        self._current_items = items
        total = data.get("total", 0)
        total_pages = data.get("total_pages", 1)
        self.pagination.update_state(self._current_page, total_pages, total)

        rows: list[dict[str, Any]] = []
        for appt in items:
            appt_id = appt.get("appointment_id", 0)
            appt_date = str(appt.get("appointment_date", ""))
            start_time = str(appt.get("start_time", ""))[:5]
            patient = appt.get("patient", {})
            doctor = appt.get("doctor", {})
            status = appt.get("status", "PENDING")
            rows.append(
                {
                    "appointment_id": appt_id,
                    "appointment_time": CellValue(
                        format_date(appt_date),
                        format_time(start_time),
                    ),
                    "patient": CellValue(
                        str(patient.get("full_name", "") or "—"),
                        str(patient.get("phone", "") or "Chưa có số điện thoại"),
                    ),
                    "doctor_name": doctor.get("full_name", ""),
                    "status": status,
                    "_actions": "",
                }
            )

        self.table.set_rows(rows)
        if not items:
            self.state_host.show_empty(
                "Không tìm thấy lịch hẹn",
                "Thử thay đổi điều kiện tìm kiếm hoặc tạo lịch hẹn mới.",
                action_text="Làm mới",
            )
            return

        self.state_host.show_content()

        for row, appt in enumerate(items):
            appt_id = appt.get("appointment_id", 0)
            status = appt.get("status", "PENDING")

            primary: QPushButton | None = None
            if status in ("PENDING", "CONFIRMED"):
                primary_label = "Xác nhận" if status == "PENDING" else "Tiếp nhận"
                primary = QPushButton(primary_label)
                primary.setObjectName("tableActionPrimary")
                primary.setCursor(Qt.PointingHandCursor)
                primary.setAccessibleName(f"{primary_label} lịch hẹn #{appt_id}")
                if status == "PENDING":
                    primary.clicked.connect(
                        lambda _, a_id=appt_id: self._confirm_appointment(a_id)
                    )
                else:
                    primary.clicked.connect(
                        lambda _, a_id=appt_id: self._check_in_appointment(a_id)
                    )
            overflow: TableActionMenu | None = None
            if status not in ("COMPLETED", "CANCELLED"):
                actions: list[RowAction] = []
                if status == "PENDING":
                    actions.append(
                        RowAction(
                            "Tiếp nhận",
                            lambda a_id=appt_id: self._check_in_appointment(a_id),
                        )
                    )
                actions.extend(
                    (
                        RowAction(
                            "Đổi lịch",
                            lambda value=appt: self._reschedule_dialog(value),
                        ),
                        RowAction(
                            "Hủy lịch",
                            lambda a_id=appt_id: self._cancel_dialog(a_id),
                            destructive=True,
                        ),
                    )
                )
                overflow = TableActionMenu(
                    actions,
                    accessible_name=f"Thao tác khác cho lịch hẹn #{appt_id}",
                )
            actions_widget = table_action_cell(
                primary,
                overflow,
                accessible_name=f"Thao tác lịch hẹn #{appt_id}",
            )
            self.table.setIndexWidget(self.table.model().index(row, 5), actions_widget)
            self.table.verticalHeader().resizeSection(row, 60)

    def _retry(self) -> None:
        self.load_appointments()

    def _confirm_appointment(self, appt_id: int) -> None:
        self.run_api_task(
            f"confirm_{appt_id}",
            lambda: self.api_client.post(f"/api/v1/reception/appointments/{appt_id}/confirm"),
            lambda _: self._on_action_success(f"Đã xác nhận lịch hẹn #{appt_id} thành công!"),
            controls=(self.table,),
            loading_text="Đang xác nhận lịch hẹn...",
        )

    def _check_in_appointment(self, appt_id: int) -> None:
        self.run_api_task(
            f"checkin_{appt_id}",
            lambda: self.api_client.post(f"/api/v1/reception/appointments/{appt_id}/check-in"),
            lambda _: self._on_action_success(f"Đã tiếp nhận bệnh nhân cho lịch hẹn #{appt_id}!"),
            controls=(self.table,),
            loading_text="Đang tiếp nhận bệnh nhân...",
        )

    def _on_action_success(self, msg: str) -> None:
        self.feedback.show_message("Thành công", msg, severity="success")
        self.load_appointments()

    def _cancel_dialog(self, appt_id: int) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Hủy lịch hẹn #{appt_id}")
        dialog.resize(360, 160)
        d_layout = QVBoxLayout(dialog)

        label = QLabel("Vui lòng nhập lý do hủy lịch hẹn:")
        d_layout.addWidget(label)

        reason_input = QLineEdit()
        d_layout.addWidget(reason_input)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Đóng")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(dialog.reject)
        btn_confirm = QPushButton("Xác nhận hủy")
        btn_confirm.setObjectName("dangerButton")
        btn_confirm.setCursor(Qt.PointingHandCursor)
        btn_confirm.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_confirm)
        d_layout.addLayout(btn_row)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            reason = reason_input.text().strip() or "Hủy bởi nhân viên tiếp đón."
            self.run_api_task(
                f"cancel_{appt_id}",
                lambda: self.api_client.post(
                    f"/api/v1/reception/appointments/{appt_id}/cancel",
                    json={"cancellation_reason": reason},
                ),
                lambda _: self._on_action_success(f"Đã hủy lịch hẹn #{appt_id}."),
                controls=(self.table,),
                loading_text="Đang hủy lịch hẹn...",
            )

    def _reschedule_dialog(self, appt: dict[str, Any]) -> None:
        appt_id = appt.get("appointment_id", 0)
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Đổi lịch hẹn #{appt_id}")
        dialog.resize(380, 200)
        form = QFormLayout(dialog)

        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("dd/MM/yyyy")
        form.addRow("Ngày khám mới:", date_edit)

        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("HH:mm")
        form.addRow("Giờ khám mới:", time_edit)

        reason_edit = QLineEdit()
        form.addRow("Lý do đổi:", reason_edit)

        btn_row = QHBoxLayout()
        btn_close = QPushButton("Hủy")
        btn_close.setObjectName("secondaryButton")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(dialog.reject)
        btn_save = QPushButton("Lưu lịch mới")
        btn_save.setObjectName("primaryButton")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_close)
        btn_row.addWidget(btn_save)
        form.addRow(btn_row)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_date = date_edit.date().toString("yyyy-MM-dd")
            selected_time = time_edit.time()
            new_time = selected_time.toString("HH:mm:00")
            payload = {
                "appointment_date": new_date,
                "start_time": new_time,
                "end_time": selected_time.addSecs(30 * 60).toString("HH:mm:00"),
                "reason": reason_edit.text().strip() or "Đổi lịch bởi nhân viên tiếp đón",
            }
            self.run_api_task(
                f"reschedule_{appt_id}",
                lambda: self.api_client.post(
                    f"/api/v1/reception/appointments/{appt_id}/reschedule",
                    json=payload,
                ),
                lambda _: self._on_action_success(f"Đã đổi lịch hẹn #{appt_id} sang ngày {new_date}!"),
                controls=(self.table,),
                loading_text="Đang cập nhật lịch hẹn...",
            )
