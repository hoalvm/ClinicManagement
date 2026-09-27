"""List-first doctor-schedule administration."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QFrame,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
)

from frontend.api_client import api_client
from frontend.pages.admin_ui import (
    AdminApiPage,
    AdminFormDialog,
    AdminRowActions,
    require_success,
    set_row_actions,
)
from frontend.ui.design_system import (
    CellValue,
    ColumnDisplayMode,
    ColumnPriority,
    ColumnSpec,
)
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.combo_box import ChevronComboBox
from frontend.widgets.page_header import PageHeader

DAYS_VN = {
    1: "Thứ Hai",
    2: "Thứ Ba",
    3: "Thứ Tư",
    4: "Thứ Năm",
    5: "Thứ Sáu",
    6: "Thứ Bảy",
    7: "Chủ Nhật",
}


def _time_text(value: object) -> str:
    text = str(value or "")
    return text[:5] if len(text) >= 5 else text or "—"


def _qtime(value: object, fallback: QTime) -> QTime:
    parsed = QTime.fromString(_time_text(value), "HH:mm")
    return parsed if parsed.isValid() else fallback


class ScheduleManagementPage(AdminApiPage):
    def __init__(self) -> None:
        super().__init__()
        self._doctors: list[dict] = []
        self._doctor_names: dict[int, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self.header = PageHeader(
            "Lịch trực",
            "Quản lý ca làm việc định kỳ của bác sĩ",
            action_label="Thêm lịch trực",
        )
        self.header.action_clicked.connect(self.open_create_dialog)
        layout.addWidget(self.header)
        self.add_request_feedback(layout)

        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card.setAccessibleName("Danh sách lịch trực")
        card_layout = QVBoxLayout(table_card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        self.table = AdaptiveDataTable(
            (
                ColumnSpec(
                    "ID",
                    "id",
                    minimum_width=56,
                    preferred_width=64,
                    maximum_width=72,
                    priority=int(ColumnPriority.CRITICAL),
                    preserve_full=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Bác sĩ",
                    "doctor",
                    minimum_width=220,
                    preferred_width=360,
                    maximum_width=560,
                    grow_weight=3,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Ca trực",
                    "shift",
                    minimum_width=180,
                    preferred_width=230,
                    maximum_width=300,
                    grow_weight=1,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Thời lượng",
                    "duration",
                    minimum_width=110,
                    preferred_width=120,
                    maximum_width=132,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Trạng thái",
                    "status",
                    minimum_width=124,
                    preferred_width=132,
                    maximum_width=148,
                    priority=int(ColumnPriority.CRITICAL),
                    preserve_full=True,
                    status=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Thao tác",
                    "actions",
                    minimum_width=132,
                    preferred_width=140,
                    maximum_width=152,
                    priority=int(ColumnPriority.CRITICAL),
                    preserve_full=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
            ),
            accessible_name="Danh sách lịch trực",
        )
        card_layout.addWidget(self.table)
        self.table_state = self.bind_state_host(
            table_card,
            self.load_data,
            empty_title="Chưa có lịch trực",
            empty_description="Tạo lịch trực đầu tiên để mở giờ làm việc cho bác sĩ.",
            empty_action_text="Thêm lịch trực",
            on_empty_action=self.open_create_dialog,
        )
        layout.addWidget(self.table_state, 1)
        self.load_doctors()
        self.load_data()

    def load_doctors(self):
        return self.run_admin_task(
            "load-schedule-doctors",
            lambda: require_success(
                api_client.get("/doctors/"),
                "Không thể tải danh sách bác sĩ.",
            ).json(),
            self._doctors_loaded,
            loading_text="Đang tải danh sách bác sĩ…",
        )

    def _doctors_loaded(self, doctors: list[dict]) -> None:
        self._doctors = [doctor for doctor in doctors if doctor.get("IsActive")]
        self._doctor_names = {
            int(doctor["DoctorID"]): str(doctor.get("FullName") or "—")
            for doctor in doctors
        }

    def load_data(self, *, clear_feedback: bool = True):
        return self.run_admin_task(
            "load-schedules",
            self._fetch_schedule_data,
            self._populate_schedules,
            loading_text="Đang tải lịch trực…",
            clear_feedback=clear_feedback,
            stateful=True,
            empty_when=lambda result: not result[0],
        )

    @staticmethod
    def _fetch_schedule_data():
        schedules = require_success(
            api_client.get("/schedules/"),
            "Không thể tải lịch trực.",
        ).json()
        doctors = require_success(
            api_client.get("/doctors/"),
            "Không thể tải thông tin bác sĩ.",
        ).json()
        return schedules, doctors

    def _populate_schedules(self, result) -> None:
        schedules, doctors = result
        self._doctor_names = {
            int(doctor["DoctorID"]): str(doctor.get("FullName") or "—")
            for doctor in doctors
        }
        rows = []
        for schedule in schedules:
            doctor_name = self._doctor_names.get(int(schedule["DoctorID"]), "—")
            day = DAYS_VN.get(int(schedule.get("DayOfWeek") or 0), "Không rõ ngày")
            start = _time_text(schedule.get("StartTime"))
            end = _time_text(schedule.get("EndTime"))
            rows.append(
                {
                    "id": schedule.get("ScheduleID"),
                    "doctor": doctor_name,
                    "shift": CellValue(
                        day,
                        f"{start}–{end}",
                        accessible_text=f"{day}, từ {start} đến {end}",
                    ),
                    "duration": f"{schedule.get('SlotDuration') or 30} phút",
                    "status": "ACTIVE" if schedule.get("IsActive", True) else "INACTIVE",
                    "actions": "",
                }
            )
        self.table.set_rows(rows)
        for row, schedule in enumerate(schedules):
            doctor_name = self._doctor_names.get(int(schedule["DoctorID"]), "bác sĩ")
            active = bool(schedule.get("IsActive", True))
            overflow = (
                (
                    "Xóa lịch trực",
                    lambda schedule=schedule: self._confirm_delete(schedule),
                ),
            ) if active else ()
            actions = AdminRowActions(
                f"lịch trực của {doctor_name}",
                self.table,
                on_edit=(
                    (lambda schedule=schedule: self.open_edit_dialog(schedule))
                    if active
                    else None
                ),
                overflow_actions=overflow,
            )
            set_row_actions(self.table, row, 5, actions)

    def _build_dialog(self, schedule: dict | None = None):
        editing = schedule is not None
        dialog = AdminFormDialog(
            "Chỉnh sửa lịch trực" if editing else "Thêm lịch trực",
            "Chọn ngày làm việc, khoảng giờ và thời lượng mỗi lượt khám.",
            self,
            save_text="Lưu thay đổi" if editing else "Thêm lịch trực",
        )
        doctor_combo = ChevronComboBox()
        for doctor in self._doctors:
            label = str(doctor.get("FullName") or "—")
            specialty = str(doctor.get("SpecialtyName") or "Chưa phân chuyên khoa")
            doctor_combo.addItem(f"{label} · {specialty}", doctor["DoctorID"])
        doctor_display = QLineEdit()
        doctor_display.setReadOnly(True)
        day_combo = ChevronComboBox()
        for day_id, day_name in DAYS_VN.items():
            day_combo.addItem(day_name, day_id)
        start = QTimeEdit(QTime(8, 0))
        start.setDisplayFormat("HH:mm")
        end = QTimeEdit(QTime(17, 0))
        end.setDisplayFormat("HH:mm")
        duration = QSpinBox()
        duration.setRange(5, 240)
        duration.setSuffix(" phút")
        duration.setValue(30)

        if editing:
            doctor_display.setText(
                self._doctor_names.get(int(schedule["DoctorID"]), "—")
            )
            day_combo.setCurrentIndex(
                max(0, day_combo.findData(schedule.get("DayOfWeek")))
            )
            start.setTime(_qtime(schedule.get("StartTime"), QTime(8, 0)))
            end.setTime(_qtime(schedule.get("EndTime"), QTime(17, 0)))
            duration.setValue(int(schedule.get("SlotDuration") or 30))
            dialog.add_field("Bác sĩ", doctor_display, 0, 0, column_span=2)
        else:
            dialog.add_field("Bác sĩ", doctor_combo, 0, 0, required=True, column_span=2)
        dialog.add_field("Ngày trong tuần", day_combo, 1, 0, required=True)
        dialog.add_field("Thời lượng mỗi lượt", duration, 1, 1, required=True)
        dialog.add_field("Giờ bắt đầu", start, 2, 0, required=True)
        dialog.add_field("Giờ kết thúc", end, 2, 1, required=True)
        return dialog, doctor_combo, day_combo, start, end, duration

    def open_create_dialog(self) -> None:
        if not self._doctors:
            QMessageBox.information(
                self,
                "Chưa có bác sĩ",
                "Hãy tạo ít nhất một bác sĩ đang hoạt động trước khi thêm lịch trực.",
            )
            return
        dialog, doctor, day, start, end, duration = self._build_dialog()

        def submit() -> None:
            if start.time() >= end.time():
                dialog.show_request_error(
                    "Khoảng giờ chưa hợp lệ",
                    "Giờ kết thúc phải muộn hơn giờ bắt đầu.",
                )
                return
            payload = {
                "DoctorID": doctor.currentData(),
                "DayOfWeek": day.currentData(),
                "StartTime": start.time().toString("HH:mm:ss"),
                "EndTime": end.time().toString("HH:mm:ss"),
                "SlotDuration": duration.value(),
            }
            self._submit_dialog(
                dialog,
                "create-schedule",
                lambda: require_success(
                    api_client.post("/schedules/", json=payload),
                    "Không thể thêm lịch trực.",
                ),
                "Đã thêm lịch trực",
            )

        dialog.buttons.accepted.connect(submit)
        dialog.exec()

    def open_edit_dialog(self, schedule: dict) -> None:
        dialog, _doctor, day, start, end, duration = self._build_dialog(schedule)
        schedule_id = schedule["ScheduleID"]

        def submit() -> None:
            if start.time() >= end.time():
                dialog.show_request_error(
                    "Khoảng giờ chưa hợp lệ",
                    "Giờ kết thúc phải muộn hơn giờ bắt đầu.",
                )
                return
            payload = {
                "DayOfWeek": day.currentData(),
                "StartTime": start.time().toString("HH:mm:ss"),
                "EndTime": end.time().toString("HH:mm:ss"),
                "SlotDuration": duration.value(),
            }
            self._submit_dialog(
                dialog,
                f"update-schedule:{schedule_id}",
                lambda: require_success(
                    api_client.put(f"/schedules/{schedule_id}", json=payload),
                    "Không thể cập nhật lịch trực.",
                ),
                "Đã cập nhật lịch trực",
            )

        dialog.buttons.accepted.connect(submit)
        dialog.exec()

    def _submit_dialog(self, dialog, key, operation, success_title) -> None:
        dialog.set_busy(True)
        self.run_admin_task(
            key,
            operation,
            lambda _response: self._saved(dialog, success_title),
            on_finished=lambda: dialog.set_busy(False),
            on_error=lambda error: dialog.show_request_error(
                "Không thể lưu lịch trực", self.error_message(error)
            ),
            loading_text="Đang lưu lịch trực…",
        )

    def _saved(self, dialog: AdminFormDialog, title: str) -> None:
        dialog.accept()
        self.feedback.show_message(
            title,
            "Thông tin lịch trực đã được lưu.",
            severity="success",
        )
        self.load_data(clear_feedback=False)

    def _confirm_delete(self, schedule: dict) -> None:
        doctor_name = self._doctor_names.get(int(schedule["DoctorID"]), "bác sĩ")
        answer = QMessageBox.question(
            self,
            "Xóa lịch trực",
            f"Bạn có chắc muốn xóa lịch trực của “{doctor_name}”?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        schedule_id = schedule["ScheduleID"]
        self.run_admin_task(
            f"delete-schedule:{schedule_id}",
            lambda: require_success(
                api_client.delete(f"/schedules/{schedule_id}"),
                "Không thể xóa lịch trực.",
            ),
            lambda _response: self._deleted(),
            loading_text="Đang xóa lịch trực…",
        )

    def _deleted(self) -> None:
        self.feedback.show_message(
            "Đã xóa lịch trực",
            "Lịch trực đã được ngừng sử dụng.",
            severity="success",
        )
        self.load_data(clear_feedback=False)
