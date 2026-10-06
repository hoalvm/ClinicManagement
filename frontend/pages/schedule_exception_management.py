"""One-off doctor leave and clinic closure administration."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFrame,
    QLineEdit,
    QMessageBox,
    QTimeEdit,
    QVBoxLayout,
)

from frontend.api_client import api_client
from frontend.core.clinic_clock import clinic_today_qdate
from frontend.pages.admin_ui import (
    AdminApiPage,
    AdminFormDialog,
    AdminRowActions,
    require_success,
    set_row_actions,
)
from frontend.ui.design_system import CellValue, ColumnPriority, ColumnSpec
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.combo_box import ChevronComboBox
from frontend.widgets.page_header import PageHeader


class ScheduleExceptionManagementPage(AdminApiPage):
    """Approved closures are visible separately from weekly doctor shifts."""

    def __init__(self) -> None:
        super().__init__()
        self._doctors: list[dict] = []
        self._doctor_names: dict[int, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self.header = PageHeader(
            "Nghỉ và đóng ca",
            "Đóng ngày hoặc khung giờ của bác sĩ sau khi xử lý các lịch hẹn còn mở.",
            action_label="Thêm ngày nghỉ",
        )
        self.header.action_clicked.connect(self.open_create_dialog)
        layout.addWidget(self.header)
        self.add_request_feedback(layout)

        card = QFrame()
        card.setObjectName("contentCard")
        card.setAccessibleName("Danh sách ngày nghỉ và khung giờ đóng")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        self.table = AdaptiveDataTable(
            (
                ColumnSpec("Ngày", "date", minimum_width=115, preferred_width=130, maximum_width=145),
                ColumnSpec("Bác sĩ", "doctor", minimum_width=170, preferred_width=220, maximum_width=270),
                ColumnSpec("Thời gian", "hours", minimum_width=130, preferred_width=150, maximum_width=175),
                ColumnSpec("Lý do", "reason", minimum_width=200, preferred_width=260, maximum_width=360, grow_weight=2),
                ColumnSpec(
                    "Trạng thái",
                    "status",
                    minimum_width=115,
                    preferred_width=130,
                    maximum_width=145,
                    priority=int(ColumnPriority.CRITICAL),
                    status=True,
                ),
                ColumnSpec(
                    "Thao tác",
                    "actions",
                    minimum_width=120,
                    preferred_width=130,
                    maximum_width=145,
                    priority=int(ColumnPriority.CRITICAL),
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
            ),
            accessible_name="Danh sách ngày nghỉ và khung giờ đóng",
        )
        card_layout.addWidget(self.table)
        self.table_state = self.bind_state_host(
            card,
            self.load_data,
            empty_title="Chưa có ngày nghỉ",
            empty_description="Ca trực định kỳ đang áp dụng theo lịch đã cấu hình.",
        )
        layout.addWidget(self.table_state, 1)

    @staticmethod
    def _fetch_data() -> tuple[list[dict], list[dict]]:
        doctors = require_success(
            api_client.get("/doctors/"), "Không thể tải danh sách bác sĩ."
        ).json()
        exceptions = require_success(
            api_client.get("/schedules/exceptions"),
            "Không thể tải ngày nghỉ của bác sĩ.",
        ).json()
        return doctors, exceptions

    def load_data(self, *, clear_feedback: bool = True):
        return self.run_admin_task(
            "load-schedule-exceptions",
            self._fetch_data,
            self._populate,
            loading_text="Đang tải ngày nghỉ…",
            clear_feedback=clear_feedback,
            stateful=True,
            empty_when=lambda result: not result[1],
        )

    def _populate(self, result: tuple[list[dict], list[dict]]) -> None:
        doctors, exceptions = result
        self._doctors = [doctor for doctor in doctors if doctor.get("IsActive")]
        self._doctor_names = {
            int(doctor["DoctorID"]): str(doctor.get("FullName") or "Bác sĩ")
            for doctor in doctors
        }
        rows = []
        for item in exceptions:
            day = str(item.get("exception_date") or "")[:10]
            hours = (
                "Cả ngày"
                if not item.get("start_time")
                else f"{str(item['start_time'])[:5]}–{str(item['end_time'])[:5]}"
            )
            doctor_name = self._doctor_names.get(int(item["doctor_id"]), "Bác sĩ đã ngừng")
            rows.append(
                {
                    "date": day,
                    "doctor": doctor_name,
                    "hours": hours,
                    "reason": CellValue(str(item.get("reason") or "—")),
                    "status": "ACTIVE" if item.get("is_active") else "INACTIVE",
                    "actions": "",
                }
            )
        self.table.set_rows(rows)
        for row, item in enumerate(exceptions):
            if not item.get("is_active"):
                continue
            action = AdminRowActions(
                "ngày nghỉ của bác sĩ",
                self.table,
                overflow_actions=(("Mở lại ca", lambda item=item: self._confirm_reopen(item)),),
            )
            set_row_actions(self.table, row, 5, action)

    def open_create_dialog(self) -> None:
        if not self._doctors:
            self.feedback.show_message(
                "Chưa có bác sĩ",
                "Hãy tải danh sách và tạo bác sĩ đang hoạt động trước khi đóng ca.",
                severity="error",
            )
            return

        dialog = AdminFormDialog(
            "Thêm ngày nghỉ hoặc đóng ca",
            "Lịch hẹn chưa kết thúc trong khoảng này phải được chuyển hoặc hủy trước.",
            self,
        )
        doctor = ChevronComboBox()
        doctor.addItem("Chọn bác sĩ", None)
        for item in self._doctors:
            doctor.addItem(str(item.get("FullName") or "Bác sĩ"), int(item["DoctorID"]))
        day = QDateEdit(clinic_today_qdate())
        day.setDisplayFormat("dd/MM/yyyy")
        day.setCalendarPopup(True)
        day.setMinimumDate(clinic_today_qdate())
        all_day = QCheckBox("Đóng cả ngày")
        all_day.setChecked(True)
        start = QTimeEdit(QTime(8, 0))
        end = QTimeEdit(QTime(17, 0))
        for editor in (start, end):
            editor.setDisplayFormat("HH:mm")
            editor.setEnabled(False)
        all_day.toggled.connect(lambda checked: start.setEnabled(not checked))
        all_day.toggled.connect(lambda checked: end.setEnabled(not checked))
        reason = QLineEdit()
        reason.setMaxLength(255)
        reason.setPlaceholderText("Ví dụ: bác sĩ nghỉ phép đã được duyệt")
        dialog.add_field("Bác sĩ", doctor, 0, 0, required=True, column_span=2)
        dialog.add_field("Ngày", day, 1, 0, required=True)
        dialog.add_field("Phạm vi", all_day, 1, 1)
        dialog.add_field("Từ", start, 2, 0)
        dialog.add_field("Đến", end, 2, 1)
        dialog.add_field("Lý do", reason, 3, 0, required=True, column_span=2)

        def submit() -> None:
            doctor_id = doctor.currentData()
            note = reason.text().strip()
            if doctor_id is None or len(note) < 3:
                dialog.show_request_error("Thiếu thông tin", "Chọn bác sĩ và nhập lý do từ 3 ký tự.")
                return
            if not all_day.isChecked() and start.time() >= end.time():
                dialog.show_request_error("Giờ không hợp lệ", "Giờ kết thúc phải sau giờ bắt đầu.")
                return
            payload = {
                "doctor_id": doctor_id,
                "exception_date": day.date().toString("yyyy-MM-dd"),
                "start_time": None if all_day.isChecked() else start.time().toString("HH:mm"),
                "end_time": None if all_day.isChecked() else end.time().toString("HH:mm"),
                "reason": note,
            }
            dialog.set_busy(True)
            self.run_admin_task(
                "create-schedule-exception",
                lambda: require_success(
                    api_client.post("/schedules/exceptions", json=payload),
                    "Không thể đóng ca trực.",
                ),
                lambda _response: self._saved(dialog),
                on_finished=lambda: dialog.set_busy(False),
                on_error=lambda error: dialog.show_request_error(
                    "Không thể đóng ca", self.error_message(error)
                ),
                loading_text="Đang đóng ca trực…",
            )

        dialog.buttons.accepted.connect(submit)
        dialog.exec()

    def _saved(self, dialog: AdminFormDialog) -> None:
        dialog.accept()
        self.feedback.show_message("Đã đóng ca", "Ngày nghỉ đã được ghi nhận.", severity="success")
        self.load_data(clear_feedback=False)

    def _confirm_reopen(self, item: dict) -> None:
        answer = QMessageBox.question(
            self,
            "Mở lại ca trực",
            "Mở lại thời gian này để bác sĩ có thể nhận lịch hẹn mới?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        exception_id = int(item["exception_id"])
        self.run_admin_task(
            f"reopen-schedule-exception:{exception_id}",
            lambda: require_success(
                api_client.delete(f"/schedules/exceptions/{exception_id}"),
                "Không thể mở lại ca trực.",
            ),
            lambda _response: self._reopened(),
            loading_text="Đang mở lại ca trực…",
        )

    def _reopened(self) -> None:
        self.feedback.show_message("Đã mở lại ca", "Bác sĩ có thể nhận lịch mới.", severity="success")
        self.load_data(clear_feedback=False)
