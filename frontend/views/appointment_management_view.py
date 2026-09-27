"""Appointment Management View for Receptionist / Staff."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QTimeEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.ui.design_system import ColumnPriority, ColumnSpec
from frontend.views.common import BaseApiView
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.page_header import PageHeader
from frontend.widgets.pagination import Pagination
from frontend.widgets.state_host import StateHost


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

        # Filter Controls Bar
        filter_card = QFrame()
        filter_card.setObjectName("filterCard")
        filter_bar = QHBoxLayout(filter_card)
        filter_bar.setContentsMargins(16, 10, 16, 10)
        filter_bar.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm kiếm theo tên bệnh nhân, SĐT hoặc lý do...")
        self.search_input.setAccessibleName("Tìm kiếm lịch hẹn")
        self.search_input.returnPressed.connect(self._apply_filter)
        filter_bar.addWidget(self.search_input, 2)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Tất cả trạng thái", "")
        self.status_combo.addItem("Chờ xác nhận", "PENDING")
        self.status_combo.addItem("Đã xác nhận", "CONFIRMED")
        self.status_combo.addItem("Chờ khám", "CHECKED_IN")
        self.status_combo.addItem("Hoàn thành", "COMPLETED")
        self.status_combo.addItem("Đã hủy", "CANCELLED")
        self.status_combo.currentIndexChanged.connect(self._apply_filter)
        filter_bar.addWidget(self.status_combo, 1)

        self.btn_refresh = QPushButton("Lọc")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self._apply_filter)
        filter_bar.addWidget(self.btn_refresh)

        layout.addWidget(filter_card)

        self.table = AdaptiveDataTable(
            [
                ColumnSpec(
                    "Mã hẹn",
                    "appointment_id",
                    minimum_width=64,
                    preferred_width=72,
                    priority=ColumnPriority.HIGH,
                    formatter=lambda value: f"#{int(value or 0)}",
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Thời gian",
                    "appointment_time",
                    minimum_width=110,
                    preferred_width=126,
                    priority=ColumnPriority.HIGH,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Bệnh nhân",
                    "patient_name",
                    minimum_width=120,
                    priority=ColumnPriority.CRITICAL,
                    stretch=True,
                ),
                ColumnSpec(
                    "Số điện thoại",
                    "patient_phone",
                    minimum_width=100,
                    preferred_width=108,
                    priority=ColumnPriority.HIGH,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Bác sĩ",
                    "doctor_name",
                    minimum_width=104,
                    preferred_width=128,
                    priority=ColumnPriority.NORMAL,
                ),
                ColumnSpec(
                    "Trạng thái",
                    "status",
                    minimum_width=104,
                    preferred_width=112,
                    priority=ColumnPriority.CRITICAL,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                    status=True,
                ),
                ColumnSpec(
                    "Thao tác",
                    "_actions",
                    minimum_width=126,
                    preferred_width=146,
                    priority=ColumnPriority.CRITICAL,
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

    def _apply_filter(self) -> None:
        self._current_page = 1
        self.load_appointments()

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
                    "appointment_time": f"{appt_date} {start_time}".strip(),
                    "patient_name": patient.get("full_name", ""),
                    "patient_phone": patient.get("phone", "") or "—",
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

            # Actions cell container
            actions_widget = QWidget()
            actions_widget.setObjectName("tableCellWidget")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            actions_layout.setSpacing(6)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

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
                actions_layout.addWidget(primary)

            if status not in ("COMPLETED", "CANCELLED"):
                more_button = QToolButton()
                more_button.setObjectName("tableMoreButton")
                more_button.setText("⋯")
                more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
                more_button.setCursor(Qt.PointingHandCursor)
                more_button.setAccessibleName(f"Thêm thao tác cho lịch hẹn #{appt_id}")
                menu = QMenu(more_button)
                if status == "PENDING":
                    checkin_action = menu.addAction("Tiếp nhận")
                    checkin_action.triggered.connect(
                        lambda _, a_id=appt_id: self._check_in_appointment(a_id)
                    )
                reschedule_action = menu.addAction("Đổi lịch")
                reschedule_action.triggered.connect(
                    lambda _, a=appt: self._reschedule_dialog(a)
                )
                cancel_action = menu.addAction("Hủy lịch")
                cancel_action.triggered.connect(
                    lambda _, a_id=appt_id: self._cancel_dialog(a_id)
                )
                more_button.setMenu(menu)
                actions_layout.addWidget(more_button)

            self.table.setIndexWidget(self.table.model().index(row, 6), actions_widget)
            self.table.verticalHeader().resizeSection(row, 50)

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
        date_edit.setDisplayFormat("yyyy-MM-dd")
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
