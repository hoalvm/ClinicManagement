"""Appointment Management View for Receptionist / Staff."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.views.common import BaseApiView
from frontend.widgets.empty_state import EmptyState
from frontend.widgets.page_header import PageHeader
from frontend.widgets.pagination import Pagination
from frontend.widgets.status_badge import StatusBadge


class AppointmentManagementView(BaseApiView):
    """View to filter, confirm, check-in, cancel, or reschedule appointments."""

    check_in_requested = Signal(int)
    book_requested = Signal()

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._current_page = 1
        self._page_size = 15
        self._current_items: list[dict[str, Any]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        self.header = PageHeader(
            "Quản lý lịch hẹn",
            "Theo dõi, xác nhận và tiếp nhận bệnh nhân theo lịch hẹn",
            action_label="+ Lịch hẹn mới",
            parent=self,
        )
        self.header.action_clicked.connect(self.book_requested)
        layout.addWidget(self.header)
        layout.addWidget(self.feedback)
        layout.addWidget(self.loading)

        # Filter Controls Bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm kiếm theo tên bệnh nhân, SĐT hoặc lý do...")
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

        self.btn_refresh = QPushButton("Lọc / Làm mới")
        self.btn_refresh.clicked.connect(self._apply_filter)
        filter_bar.addWidget(self.btn_refresh)

        layout.addLayout(filter_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Mã hẹn", "Thời gian", "Bệnh nhân", "Số điện thoại", "Bác sĩ", "Trạng thái", "Thao tác"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.empty_state = EmptyState(
            "Không tìm thấy lịch hẹn",
            "Thử thay đổi điều kiện tìm kiếm hoặc tạo lịch hẹn mới.",
            parent=self,
        )
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

        # Pagination
        self.pagination = Pagination(parent=self)
        self.pagination.page_requested.connect(self._go_to_page)
        layout.addWidget(self.pagination)

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
            loading_text="Đang tải danh sách lịch hẹn...",
        )

    def _on_appointments_loaded(self, data: dict[str, Any]) -> None:
        items = data.get("items", [])
        self._current_items = items
        total = data.get("total", 0)
        total_pages = data.get("total_pages", 1)
        self.pagination.update_state(self._current_page, total_pages, total)

        if not items:
            self.table.hide()
            self.empty_state.show()
            return

        self.empty_state.hide()
        self.table.show()
        self.table.setRowCount(len(items))

        for row, appt in enumerate(items):
            appt_id = appt.get("appointment_id", 0)
            appt_date = str(appt.get("appointment_date", ""))
            start_time = str(appt.get("start_time", ""))[:5]
            patient = appt.get("patient", {})
            doctor = appt.get("doctor", {})
            status = appt.get("status", "PENDING")

            self.table.setItem(row, 0, QTableWidgetItem(f"#{appt_id}"))
            self.table.setItem(row, 1, QTableWidgetItem(f"{appt_date} {start_time}"))
            self.table.setItem(row, 2, QTableWidgetItem(patient.get("full_name", "")))
            self.table.setItem(row, 3, QTableWidgetItem(patient.get("phone", "") or "—"))
            self.table.setItem(row, 4, QTableWidgetItem(doctor.get("full_name", "")))

            badge = StatusBadge(status)
            self.table.setCellWidget(row, 5, badge)

            # Actions cell container
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)

            if status == "PENDING":
                btn_confirm = QPushButton("Xác nhận")
                btn_confirm.setStyleSheet("background-color: #0f766e; color: white; border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: 600;")
                btn_confirm.clicked.connect(lambda _, a_id=appt_id: self._confirm_appointment(a_id))
                actions_layout.addWidget(btn_confirm)

            if status in ("PENDING", "CONFIRMED"):
                btn_checkin = QPushButton("Tiếp nhận")
                btn_checkin.setStyleSheet("background-color: #0284c7; color: white; border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: 600;")
                btn_checkin.clicked.connect(lambda _, a_id=appt_id: self._check_in_appointment(a_id))
                actions_layout.addWidget(btn_checkin)

            if status not in ("COMPLETED", "CANCELLED"):
                btn_reschedule = QPushButton("Đổi lịch")
                btn_reschedule.setStyleSheet("background-color: #e2e8f0; color: #334155; border-radius: 6px; padding: 4px 8px; font-size: 11px;")
                btn_reschedule.clicked.connect(lambda _, a=appt: self._reschedule_dialog(a))
                actions_layout.addWidget(btn_reschedule)

                btn_cancel = QPushButton("Hủy")
                btn_cancel.setStyleSheet("background-color: #fee2e2; color: #b91c1c; border-radius: 6px; padding: 4px 8px; font-size: 11px;")
                btn_cancel.clicked.connect(lambda _, a_id=appt_id: self._cancel_dialog(a_id))
                actions_layout.addWidget(btn_cancel)

            self.table.setCellWidget(row, 6, actions_widget)

    def _confirm_appointment(self, appt_id: int) -> None:
        self.run_api_task(
            f"confirm_{appt_id}",
            lambda: self.api_client.post(f"/api/v1/reception/appointments/{appt_id}/confirm"),
            lambda _: self._on_action_success(f"Đã xác nhận lịch hẹn #{appt_id} thành công!"),
            loading_text="Đang xác nhận lịch hẹn...",
        )

    def _check_in_appointment(self, appt_id: int) -> None:
        self.run_api_task(
            f"checkin_{appt_id}",
            lambda: self.api_client.post(f"/api/v1/reception/appointments/{appt_id}/check-in"),
            lambda _: self._on_action_success(f"Đã tiếp nhận bệnh nhân cho lịch hẹn #{appt_id}!"),
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
        btn_cancel.clicked.connect(dialog.reject)
        btn_confirm = QPushButton("Xác nhận hủy")
        btn_confirm.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold;")
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
        btn_close.clicked.connect(dialog.reject)
        btn_save = QPushButton("Lưu lịch mới")
        btn_save.setStyleSheet("background-color: #0f766e; color: white; font-weight: bold;")
        btn_save.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_close)
        btn_row.addWidget(btn_save)
        form.addRow(btn_row)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_date = date_edit.date().toString("yyyy-MM-dd")
            new_time = time_edit.time().toString("HH:mm:00")
            payload = {
                "appointment_date": new_date,
                "start_time": new_time,
                "end_time": "10:00:00",
                "reason": reason_edit.text().strip() or "Đổi lịch bởi nhân viên tiếp đón",
            }
            self.run_api_task(
                f"reschedule_{appt_id}",
                lambda: self.api_client.post(
                    f"/api/v1/reception/appointments/{appt_id}/reschedule",
                    json=payload,
                ),
                lambda _: self._on_action_success(f"Đã đổi lịch hẹn #{appt_id} sang ngày {new_date}!"),
                loading_text="Đang cập nhật lịch hẹn...",
            )
