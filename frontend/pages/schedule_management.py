"""Modern, clean Schedule Management page for Admin."""

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTimeEdit,
    QVBoxLayout,
)

from frontend.api_client import api_client
from frontend.pages.admin_ui import (
    AdminApiPage,
    action_cell,
    configure_admin_table,
    require_success,
    table_item,
)
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


class ScheduleManagementPage(AdminApiPage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # ------------------- Header -------------------
        self.header = PageHeader(
            "Lịch trực",
            "Phân ca làm việc của bác sĩ",
        )
        layout.addWidget(self.header)
        self.add_request_feedback(layout)

        # ------------------- Create Form Card -------------------
        form_card = QFrame()
        form_card.setObjectName("contentCard")
        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(20, 18, 20, 18)
        form_card_layout.setSpacing(14)

        form_title = QLabel("Thêm ca trực")
        form_title.setObjectName("sectionTitle")
        form_card_layout.addWidget(form_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        # Doctor
        col_doc = QVBoxLayout()
        col_doc.setSpacing(4)
        lbl_doc = QLabel("Bác sĩ")
        lbl_doc.setObjectName("fieldLabel")
        self.doctor_combo = QComboBox()
        col_doc.addWidget(lbl_doc)
        col_doc.addWidget(self.doctor_combo)
        grid.addLayout(col_doc, 0, 0, 1, 2)

        # Day of week
        col_day = QVBoxLayout()
        col_day.setSpacing(4)
        lbl_day = QLabel("Ngày trong tuần")
        lbl_day.setObjectName("fieldLabel")
        self.day_combo = QComboBox()
        for day_id, day_name in DAYS_VN.items():
            self.day_combo.addItem(day_name, day_id)
        col_day.addWidget(lbl_day)
        col_day.addWidget(self.day_combo)
        grid.addLayout(col_day, 0, 2)

        # Start Time
        col_st = QVBoxLayout()
        col_st.setSpacing(4)
        lbl_st = QLabel("Giờ bắt đầu")
        lbl_st.setObjectName("fieldLabel")
        self.start_time = QTimeEdit(QTime(8, 0))
        self.start_time.setDisplayFormat("HH:mm")
        col_st.addWidget(lbl_st)
        col_st.addWidget(self.start_time)
        grid.addLayout(col_st, 1, 0)

        # End Time
        col_et = QVBoxLayout()
        col_et.setSpacing(4)
        lbl_et = QLabel("Giờ kết thúc")
        lbl_et.setObjectName("fieldLabel")
        self.end_time = QTimeEdit(QTime(17, 0))
        self.end_time.setDisplayFormat("HH:mm")
        col_et.addWidget(lbl_et)
        col_et.addWidget(self.end_time)
        grid.addLayout(col_et, 1, 1)

        # Slot duration
        col_dur = QVBoxLayout()
        col_dur.setSpacing(4)
        lbl_dur = QLabel("Thời lượng ca (phút)")
        lbl_dur.setObjectName("fieldLabel")
        self.slot_duration = QSpinBox()
        self.slot_duration.setRange(5, 240)
        self.slot_duration.setValue(30)
        col_dur.addWidget(lbl_dur)
        col_dur.addWidget(self.slot_duration)
        grid.addLayout(col_dur, 1, 2)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.add_btn = QPushButton("Thêm mới")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setMinimumHeight(36)
        self.add_btn.setMinimumWidth(120)
        self.add_btn.setAccessibleName("Thêm ca trực mới")
        self.add_btn.clicked.connect(self.add_schedule)
        btn_layout.addWidget(self.add_btn)

        form_card_layout.addLayout(grid)
        form_card_layout.addLayout(btn_layout)
        layout.addWidget(form_card)

        # ------------------- Table Card -------------------
        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card.setAccessibleName("Nội dung danh sách lịch làm việc")
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(20, 18, 20, 18)
        table_card_layout.setSpacing(12)

        table_title = QLabel("Danh sách lịch làm việc hiện tại")
        table_title.setObjectName("sectionTitle")
        table_card_layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Bác sĩ",
            "Ngày",
            "Giờ bắt đầu",
            "Giờ kết thúc",
            "Thao tác",
        ])
        configure_admin_table(
            self.table,
            accessible_name="Danh sách lịch làm việc",
            stretch_column=1,
            fixed_widths={0: 52, 2: 116, 3: 108, 4: 108, 5: 84},
        )

        table_card_layout.addWidget(self.table)
        self.table_state = self.bind_state_host(
            table_card,
            self.load_data,
            empty_title="Chưa có lịch trực",
            empty_description="Tạo ca trực đầu tiên để mở lịch làm việc cho bác sĩ.",
            empty_action_text="Thêm ca trực",
            on_empty_action=self.doctor_combo.setFocus,
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
            self._populate_doctor_lookup,
            controls=(self.doctor_combo, self.add_btn),
            loading_text="Đang tải danh sách bác sĩ…",
        )

    def _populate_doctor_lookup(self, doctors):
        self.doctor_combo.clear()
        self.doctor_map = {}
        for doctor in doctors:
            if doctor["IsActive"]:
                label = (
                    f"{doctor['FullName']} "
                    f"({doctor.get('SpecialtyName') or 'Chưa phân khoa'})"
                )
                self.doctor_combo.addItem(label)
                self.doctor_map[label] = doctor["DoctorID"]

    def load_data(self, *, clear_feedback: bool = True):
        return self.run_admin_task(
            "load-schedules",
            self._fetch_schedule_data,
            self._populate_schedules,
            loading_text="Đang tải lịch làm việc…",
            clear_feedback=clear_feedback,
            stateful=True,
            empty_when=lambda result: not result[0],
        )

    @staticmethod
    def _fetch_schedule_data():
        schedules = require_success(
            api_client.get("/schedules/"),
            "Không thể tải lịch làm việc.",
        ).json()
        doctors = require_success(
            api_client.get("/doctors/"),
            "Không thể tải thông tin bác sĩ.",
        ).json()
        return schedules, doctors

    def _populate_schedules(self, result):
        items, doctors = result
        self.table.clearContents()
        doctors_map = {doctor["DoctorID"]: doctor["FullName"] for doctor in doctors}

        self.table.setRowCount(len(items))
        for row, s in enumerate(items):
            item_id = table_item(s["ScheduleID"], alignment=Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            doctor_name = doctors_map.get(s["DoctorID"], "—")
            self.table.setItem(row, 1, table_item(doctor_name))

            item_day = table_item(
                DAYS_VN.get(s["DayOfWeek"], "—"), alignment=Qt.AlignCenter
            )
            self.table.setItem(row, 2, item_day)

            start_text = str(s["StartTime"])
            st_item = table_item(
                start_text[:5] if len(start_text) >= 5 else start_text,
                alignment=Qt.AlignCenter,
            )
            self.table.setItem(row, 3, st_item)

            end_text = str(s["EndTime"])
            et_item = table_item(
                end_text[:5] if len(end_text) >= 5 else end_text,
                alignment=Qt.AlignCenter,
            )
            self.table.setItem(row, 4, et_item)

            # Delete button
            del_btn = QPushButton("Xóa")
            del_btn.setObjectName("actionDeleteBtn")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedSize(60, 34)
            del_btn.setAccessibleName(f"Xóa lịch của bác sĩ {doctor_name}")
            del_btn.setToolTip(del_btn.accessibleName())
            del_btn.clicked.connect(
                lambda _, sid=s["ScheduleID"], button=del_btn: self.delete_item(sid, button)
            )

            actions_widget = action_cell(
                del_btn,
                accessible_name=f"Thao tác cho lịch của bác sĩ {doctor_name}",
            )

            self.table.setCellWidget(row, 5, actions_widget)
            self.table.setRowHeight(row, 48)

    def add_schedule(self):
        doctor_label = self.doctor_combo.currentText()
        if not doctor_label:
            QMessageBox.warning(self, "Lỗi", "Chưa có bác sĩ nào — hãy tạo bác sĩ trước.")
            return

        payload = {
            "DoctorID": self.doctor_map[doctor_label],
            "DayOfWeek": self.day_combo.currentData(),
            "StartTime": self.start_time.time().toString("HH:mm:ss"),
            "EndTime": self.end_time.time().toString("HH:mm:ss"),
            "SlotDuration": self.slot_duration.value(),
        }
        self.run_admin_task(
            "create-schedule",
            lambda: require_success(
                api_client.post("/schedules/", json=payload),
                "Không thể thêm lịch làm việc.",
            ),
            self._schedule_created,
            controls=(self.add_btn,),
            loading_text="Đang thêm ca trực…",
        )

    def _schedule_created(self, _response) -> None:
        self.feedback.show_message(
            "Đã thêm ca trực",
            "Lịch làm việc đã được lưu.",
            severity="success",
        )
        self.load_data(clear_feedback=False)

    def delete_item(self, schedule_id, button: QPushButton | None = None):
        if QMessageBox.question(self, "Xác nhận", "Bạn có chắc muốn xóa lịch làm việc này?") == QMessageBox.Yes:
            controls = (button,) if button is not None else ()
            self.run_admin_task(
                f"delete-schedule:{schedule_id}",
                lambda: require_success(
                    api_client.delete(f"/schedules/{schedule_id}"),
                    "Không thể xóa lịch làm việc.",
                ),
                self._schedule_deleted,
                controls=controls,
                loading_text="Đang xóa ca trực…",
            )

    def _schedule_deleted(self, _response) -> None:
        self.feedback.show_message(
            "Đã xóa ca trực",
            "Lịch làm việc đã được xóa.",
            severity="success",
        )
        self.load_data(clear_feedback=False)
