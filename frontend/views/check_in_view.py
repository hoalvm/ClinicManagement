"""Patient Fast Check-In View for Reception Staff."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.core.clinic_clock import clinic_today_qdate
from frontend.ui.design_system import (
    CellValue,
    ColumnDisplayMode,
    ColumnPriority,
    ColumnSpec,
)
from frontend.views.common import BaseApiView, format_date, format_time
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.page_header import PageHeader
from frontend.widgets.state_host import StateHost


class CheckInView(BaseApiView):
    """Fast check-in desk for arriving patients with appointment search and arrival queue."""

    appointment_checked_in = Signal(int)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._candidate_items: list[dict[str, Any]] = []
        self._last_ticket: dict[str, Any] | None = None
        self._print_dialog: QDialog | None = None

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        self.header = PageHeader(
            "Tiếp nhận",
            "Xác nhận có mặt và cấp số khám",
            action_label="Làm mới",
            parent=self,
        )
        if self.header.action_button is not None:
            self.header.action_button.setObjectName("secondaryButton")
        self.header.action_clicked.connect(self.refresh)
        layout.addWidget(self.header)
        layout.addWidget(self.feedback)
        layout.addWidget(self.loading)

        # Fast Intake Search Box
        intake_card = QFrame()
        intake_card.setObjectName("filterCard")
        intake_layout = QVBoxLayout(intake_card)
        intake_layout.setContentsMargins(16, 14, 16, 14)
        intake_layout.setSpacing(10)

        card_title = QLabel("Tìm kiếm lịch hẹn")
        card_title.setObjectName("sectionTitle")
        intake_layout.addWidget(card_title)

        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("SĐT, họ tên hoặc mã hẹn...")
        self.search_input.setAccessibleName("Tìm kiếm lịch hẹn chờ tiếp nhận")
        self.search_input.returnPressed.connect(self.search_and_load)
        search_row.addWidget(self.search_input, 3)

        self.queue_num_input = QLineEdit()
        self.queue_num_input.setPlaceholderText("Server cấp số")
        self.queue_num_input.setAccessibleName("Số thứ tự khám")
        self.queue_num_input.setMaximumWidth(140)
        self.queue_num_input.setReadOnly(True)
        self.queue_num_input.setText("Tự động")
        search_row.addWidget(self.queue_num_input, 1)

        self.btn_search = QPushButton("Tìm kiếm")
        self.btn_search.setCursor(Qt.PointingHandCursor)
        self.btn_search.clicked.connect(self.search_and_load)
        search_row.addWidget(self.btn_search)

        intake_layout.addLayout(search_row)
        layout.addWidget(intake_card)

        self.ticket_card = QFrame()
        self.ticket_card.setObjectName("contentCard")
        ticket_layout = QHBoxLayout(self.ticket_card)
        ticket_layout.setContentsMargins(16, 12, 16, 12)
        self.ticket_summary = QLabel()
        self.ticket_summary.setWordWrap(True)
        self.ticket_summary.setObjectName("sectionTitle")
        ticket_layout.addWidget(self.ticket_summary, 1)
        self.btn_call = QPushButton("Gọi số")
        self.btn_call.setObjectName("secondaryButton")
        self.btn_call.clicked.connect(self._call_current_number)
        ticket_layout.addWidget(self.btn_call)
        self.btn_print = QPushButton("In phiếu")
        self.btn_print.setObjectName("secondaryButton")
        self.btn_print.clicked.connect(self._show_print_preview)
        ticket_layout.addWidget(self.btn_print)
        self.ticket_card.hide()
        layout.addWidget(self.ticket_card)

        # Results table for check-in
        results_label = QLabel("Lịch hẹn chờ tiếp nhận")
        results_label.setObjectName("sectionTitle")
        layout.addWidget(results_label)

        self.results_table = AdaptiveDataTable(
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
                    preferred_width=188,
                    maximum_width=270,
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
                    preferred_width=160,
                    maximum_width=230,
                    priority=ColumnPriority.NORMAL,
                    grow_weight=2,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Trạng thái",
                    "status",
                    minimum_width=100,
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
                    minimum_width=112,
                    preferred_width=122,
                    maximum_width=136,
                    priority=ColumnPriority.CRITICAL,
                    display_mode=ColumnDisplayMode.FULL,
                    preserve_full=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
            ],
            accessible_name="Lịch hẹn chờ tiếp nhận",
        )
        self.results_table.setAccessibleDescription(
            "Bảng chỉ đọc; trạng thái và nút tiếp nhận luôn hiển thị."
        )
        self.results_table.setMinimumHeight(240)

        self.state_host = StateHost(self.results_table)
        self.bind_state_host(self.state_host)
        self.empty_results = self.state_host.empty
        self.empty_results.set_title("Không có lịch hẹn chờ tiếp nhận")
        self.empty_results.set_description("Tìm kiếm theo SĐT, họ tên hoặc mã hẹn.")
        self.empty_results.set_action("Làm mới")
        self.state_host.empty_action_requested.connect(self.refresh)
        self.state_host.retry_requested.connect(self.refresh)
        layout.addWidget(self.state_host, 1)

        layout.addStretch(1)
        scroll.setWidget(container)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        self.search_and_load()

    def search_and_load(self, *, clear_feedback: bool = True) -> None:
        raw_keyword = self.search_input.text().strip()
        compact_keyword = "".join(raw_keyword.split())
        keyword = (
            compact_keyword if compact_keyword.lstrip("+").isdigit() else raw_keyword
        ) or None
        # Only confirmed appointments can be checked in today.
        params = {
            "page": 1,
            "page_size": 100,
            "appointment_date": clinic_today_qdate().toString(Qt.DateFormat.ISODate),
        }
        if keyword:
            params["keyword"] = keyword

        self.run_api_task(
            "load_checkin_candidates",
            lambda: self.api_client.get("/api/v1/reception/appointments", params=params),
            self._on_candidates_loaded,
            controls=(
                self.search_input,
                self.queue_num_input,
                self.btn_search,
            ),
            loading_text="Đang tìm lịch hẹn...",
            clear_feedback=clear_feedback,
        )

    def _on_candidates_loaded(self, data: dict[str, Any]) -> None:
        all_items = data.get("items", [])
        self._candidate_items = list(all_items)
        checked_in = [i for i in all_items if i.get("status") == "CHECKED_IN"]
        items = [i for i in all_items if i.get("status") == "CONFIRMED"]

        rows = []
        for appt in items:
            patient = appt.get("patient", {})
            doctor = appt.get("doctor", {})
            rows.append(
                {
                    "appointment_id": appt.get("appointment_id", 0),
                    "appointment_time": CellValue(
                        format_date(appt.get("appointment_date")),
                        format_time(appt.get("start_time")),
                    ),
                    "patient": CellValue(
                        str(patient.get("full_name", "") or "—"),
                        str(patient.get("phone", "") or "Chưa có số điện thoại"),
                    ),
                    "doctor_name": doctor.get("full_name", ""),
                    "status": appt.get("status", "PENDING"),
                    "_actions": "",
                }
            )
        self.results_table.set_rows(rows)

        if not items:
            self.state_host.show_empty(
                "Không có lịch hẹn chờ tiếp nhận",
                "Tìm kiếm theo SĐT, họ tên hoặc mã hẹn.",
                action_text="Làm mới",
            )
            if checked_in:
                self.feedback.show_message(
                    "Đã tiếp nhận",
                    f"Lịch hẹn #{checked_in[0].get('appointment_id')} của bệnh nhân {checked_in[0].get('patient', {}).get('full_name')} đã được tiếp nhận trước đó.",
                    severity="info",
                )
            return

        self.state_host.show_content()

        for row, appt in enumerate(items):
            appt_id = appt.get("appointment_id", 0)

            action_widget = QWidget()
            action_widget.setObjectName("tableCellWidget")
            act_layout = QHBoxLayout(action_widget)
            act_layout.setContentsMargins(4, 0, 4, 0)
            act_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn = QPushButton("Tiếp nhận")
            btn.setObjectName("tableActionPrimary")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setAccessibleName(f"Tiếp nhận lịch hẹn #{appt_id}")
            btn.clicked.connect(lambda _, a_id=appt_id: self._execute_check_in(a_id))
            act_layout.addWidget(btn)

            self.results_table.setIndexWidget(
                self.results_table.model().index(row, 5),
                action_widget,
            )
            self.results_table.verticalHeader().resizeSection(row, 60)

    def _execute_check_in(self, appt_id: int) -> None:
        self.run_api_task(
            f"do_checkin_{appt_id}",
            lambda: self.api_client.post(
                f"/api/v1/reception/appointments/{appt_id}/check-in",
                json={},
            ),
            self._on_check_in_success,
            controls=(
                self.results_table,
                self.search_input,
                self.queue_num_input,
                self.btn_search,
            ),
            loading_text="Đang xác nhận tiếp nhận...",
        )

    def _on_check_in_success(self, result: dict[str, Any]) -> None:
        appt_id = int(result.get("appointment_id") or 0)
        resolved_queue = str(result.get("queue_number") or "")
        if not resolved_queue:
            self.feedback.show_message(
                "Thiếu số thứ tự",
                "Server đã tiếp nhận nhưng chưa trả số thứ tự. Vui lòng làm mới để đối chiếu.",
                severity="error",
            )
            self.search_and_load(clear_feedback=False)
            return
        self._last_ticket = result
        self.queue_num_input.setText(resolved_queue)
        msg = f"Tiếp nhận bệnh nhân cho lịch hẹn #{appt_id} thành công!"
        if resolved_queue:
            msg += f" (Số thứ tự: {resolved_queue})"
        self.feedback.show_message("Tiếp nhận thành công", msg, severity="success")
        patient_name = str(result.get("patient", {}).get("full_name") or "Bệnh nhân")
        check_in_at = str(result.get("check_in_at") or "")
        self.ticket_summary.setText(
            f"{resolved_queue} · {patient_name} · Hẹn #{appt_id}"
            + (f" · Tiếp nhận {check_in_at[11:16]}" if check_in_at else "")
        )
        self.ticket_card.show()
        self.appointment_checked_in.emit(appt_id)
        self.search_and_load(clear_feedback=False)

    def _call_current_number(self) -> None:
        if not self._last_ticket:
            return
        queue_number = str(self._last_ticket.get("queue_number") or "")
        patient_name = str(self._last_ticket.get("patient", {}).get("full_name") or "Bệnh nhân")
        QApplication.beep()
        self.feedback.show_message(
            f"Đang gọi số {queue_number}",
            f"Mời bệnh nhân {patient_name} đến quầy tiếp nhận.",
            severity="info",
        )

    def _ticket_text(self) -> str:
        if not self._last_ticket:
            return ""
        ticket = self._last_ticket
        patient = ticket.get("patient", {})
        doctor = ticket.get("doctor", {})
        clinic = ticket.get("clinic") or {}
        return "\n".join(
            (
                "PHIẾU TIẾP NHẬN",
                f"Số thứ tự: {ticket.get('queue_number', '—')}",
                f"Giờ tiếp nhận: {str(ticket.get('check_in_at') or '—')[11:16]}",
                f"Mã lịch hẹn: #{ticket.get('appointment_id', '—')}",
                f"Bệnh nhân: {patient.get('full_name') or '—'}",
                f"Số điện thoại: {patient.get('phone') or '—'}",
                f"Bác sĩ: {doctor.get('full_name') or '—'}",
                f"Thời gian: {format_date(ticket.get('appointment_date'))} · {format_time(ticket.get('start_time'))}",
                f"Phòng khám: {clinic.get('clinic_name') or '—'}",
            )
        )

    def _show_print_preview(self) -> None:
        text = self._ticket_text()
        if not text:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Xem trước phiếu tiếp nhận")
        dialog.resize(460, 340)
        layout = QVBoxLayout(dialog)
        title = QLabel("Xem trước phiếu tiếp nhận")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        content = QLabel(text)
        content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content.setWordWrap(True)
        content.setAccessibleName(text)
        layout.addWidget(content, 1)
        close_button = QPushButton("Đóng")
        close_button.setObjectName("secondaryButton")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)
        self._print_dialog = dialog
        dialog.finished.connect(lambda _result: setattr(self, "_print_dialog", None))
        dialog.open()
