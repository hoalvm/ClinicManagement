"""Guided staff flow for booking an appointment on a patient's behalf."""

from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
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
from frontend.views.common import BaseApiView, format_date
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.combo_box import ChevronComboBox
from frontend.widgets.page_header import PageHeader
from frontend.widgets.semantic_check_box import SemanticCheckBox
from frontend.widgets.status_badge import StatusBadge
from frontend.widgets.table_actions import table_action_cell


def _set_style_state(widget: QWidget, name: str, value: object) -> None:
    """Update a QSS state property and immediately refresh the widget."""

    if widget.property(name) == value:
        return
    widget.setProperty(name, value)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class BookForPatientView(BaseApiView):
    """Find or create a patient, then book a real available appointment slot."""

    appointment_booked = Signal(dict)
    TWO_COLUMN_BREAKPOINT = 1050
    NULL_DATE = QDate(1900, 1, 1)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._selected_patient: dict[str, Any] | None = None
        self._selected_patient_id: int | None = None
        self._doctors_cache: list[dict[str, Any]] = []
        self._slot_request_version = 0

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        container = QWidget()
        container.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        main_vbox = QVBoxLayout(container)
        main_vbox.setContentsMargins(24, 24, 24, 20)
        main_vbox.setSpacing(16)

        self.header = PageHeader(
            "Đặt lịch hộ",
            "Tìm hoặc tạo hồ sơ bệnh nhân, sau đó chọn lịch khám.",
            parent=self,
        )
        main_vbox.addWidget(self.header)
        main_vbox.addWidget(self.feedback)
        main_vbox.addWidget(self.loading)

        self.content_grid = QGridLayout()
        self.content_grid.setHorizontalSpacing(20)
        self.content_grid.setVerticalSpacing(16)
        self.content_grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.left_col = QWidget()
        self.left_col.setObjectName("layoutWrapper")
        self.left_col.setMinimumWidth(0)
        self.left_col.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        left_layout = QVBoxLayout(self.left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        left_layout.addWidget(self._build_patient_card())
        left_layout.addWidget(self._build_appointment_card())

        self.right_col = QWidget()
        self.right_col.setObjectName("layoutWrapper")
        self.right_col.setMinimumWidth(0)
        self.right_col.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        right_layout = QVBoxLayout(self.right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)
        right_layout.addWidget(self._build_preview_card())
        right_layout.addWidget(self._build_profile_card())
        right_layout.addWidget(self._build_history_card())
        right_layout.addStretch(1)

        self.content_grid.addWidget(self.left_col, 0, 0)
        self.content_grid.addWidget(self.right_col, 0, 1)
        self._content_columns = 0
        main_vbox.addLayout(self.content_grid)
        self._reflow_content(force=True)
        self.scroll_area.setWidget(container)

        self.footer = QFrame()
        self.footer.setObjectName("pageFooter")
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(24, 10, 24, 12)
        footer_layout.addStretch(1)
        self.btn_reset = QPushButton("Xóa thông tin")
        self.btn_reset.setObjectName("secondaryButton")
        self.btn_reset.clicked.connect(self._clear_form)
        footer_layout.addWidget(self.btn_reset)
        self.btn_submit = QPushButton("Tạo lịch hẹn")
        self.btn_submit.setObjectName("primaryButton")
        self.btn_submit.clicked.connect(self._submit_booking)
        footer_layout.addWidget(self.btn_submit)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.scroll_area, 1)
        root.addWidget(self.footer)

        self._load_doctors()
        self._update_booking_preview()

    def _build_patient_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("contentCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        heading = QHBoxLayout()
        title = QLabel("1. Bệnh nhân")
        title.setObjectName("sectionTitle")
        heading.addWidget(title)
        self.pt_type_badge = QLabel("Hồ sơ mới")
        self.pt_type_badge.setObjectName("patientTypeBadge")
        self.pt_type_badge.setProperty("patientState", "new")
        heading.addWidget(self.pt_type_badge)
        heading.addStretch(1)
        self.btn_unselect_pt = QPushButton("Đổi bệnh nhân")
        self.btn_unselect_pt.setObjectName("ghostButton")
        self.btn_unselect_pt.clicked.connect(self._reset_patient_selection)
        self.btn_unselect_pt.hide()
        heading.addWidget(self.btn_unselect_pt)
        layout.addLayout(heading)

        lookup = QFrame()
        lookup.setObjectName("filterCard")
        lookup_layout = QVBoxLayout(lookup)
        lookup_layout.setContentsMargins(14, 12, 14, 12)
        lookup_layout.setSpacing(8)
        lookup_title = QLabel("Tìm hồ sơ đã có")
        lookup_title.setObjectName("fieldLabel")
        lookup_layout.addWidget(lookup_title)
        lookup_row = QHBoxLayout()
        self.pt_search_input = QLineEdit()
        self.pt_search_input.setAccessibleName("Tìm hồ sơ bệnh nhân")
        self.pt_search_input.setPlaceholderText("Nhập số điện thoại hoặc họ tên")
        self.pt_search_input.returnPressed.connect(self._lookup_patient)
        lookup_row.addWidget(self.pt_search_input, 1)
        self.btn_lookup = QPushButton("Tìm hồ sơ")
        self.btn_lookup.clicked.connect(self._lookup_patient)
        lookup_row.addWidget(self.btn_lookup)
        lookup_layout.addLayout(lookup_row)

        self.search_results_table = AdaptiveDataTable(
            (
                ColumnSpec(
                    "Bệnh nhân",
                    "patient",
                    minimum_width=120,
                    preferred_width=176,
                    maximum_width=280,
                    grow_weight=2,
                    priority=ColumnPriority.CRITICAL,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                    stretch=True,
                ),
                ColumnSpec(
                    "Ngày sinh",
                    "date_of_birth",
                    minimum_width=90,
                    preferred_width=104,
                    maximum_width=118,
                    priority=ColumnPriority.HIGH,
                    formatter=format_date,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Chọn",
                    "_actions",
                    minimum_width=78,
                    preferred_width=84,
                    maximum_width=92,
                    priority=ColumnPriority.CRITICAL,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
            ),
            accessible_name="Kết quả tìm hồ sơ bệnh nhân",
        )
        self.search_results_table.setMaximumHeight(196)
        self.search_results_table.hide()
        lookup_layout.addWidget(self.search_results_table)
        layout.addWidget(lookup)

        fields = QGridLayout()
        fields.setHorizontalSpacing(12)
        fields.setVerticalSpacing(8)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nhập họ và tên đầy đủ")
        self.name_input.textChanged.connect(self._on_patient_input_changed)
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Nhập số điện thoại liên hệ")
        self.phone_input.textChanged.connect(self._on_patient_input_changed)
        self.gender_combo = ChevronComboBox()
        self.gender_combo.addItem("Chưa chọn", None)
        self.gender_combo.addItem("Nam", "MALE")
        self.gender_combo.addItem("Nữ", "FEMALE")
        self.gender_combo.addItem("Khác", "OTHER")
        self.gender_combo.currentIndexChanged.connect(self._on_patient_input_changed)
        self.dob_edit = QDateEdit()
        self.dob_edit.setCalendarPopup(True)
        self.dob_edit.setMinimumDate(self.NULL_DATE)
        self.dob_edit.setSpecialValueText("Chưa chọn")
        self.dob_edit.setDate(self.NULL_DATE)
        self.dob_edit.setDisplayFormat("dd/MM/yyyy")
        self.dob_edit.dateChanged.connect(self._on_patient_input_changed)
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Nhập địa chỉ cư trú (không bắt buộc)")
        self.address_input.textChanged.connect(self._on_patient_input_changed)

        self._add_top_field(fields, 0, 0, "Họ và tên *", self.name_input)
        self._add_top_field(fields, 0, 1, "Số điện thoại *", self.phone_input)
        self._add_top_field(fields, 1, 0, "Giới tính", self.gender_combo)
        self._add_top_field(fields, 1, 1, "Ngày sinh", self.dob_edit)
        label = QLabel("Địa chỉ")
        label.setObjectName("fieldLabel")
        fields.addWidget(label, 4, 0, 1, 2)
        fields.addWidget(self.address_input, 5, 0, 1, 2)
        fields.setColumnStretch(0, 1)
        fields.setColumnStretch(1, 1)
        layout.addLayout(fields)
        return card

    @staticmethod
    def _add_top_field(
        layout: QGridLayout,
        row: int,
        column: int,
        text: str,
        widget: QWidget,
    ) -> None:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label, row * 2, column)
        layout.addWidget(widget, row * 2 + 1, column)

    def _build_appointment_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("contentCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        title = QLabel("2. Lịch khám")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        fields = QGridLayout()
        fields.setHorizontalSpacing(12)
        fields.setVerticalSpacing(8)
        self.doctor_combo = ChevronComboBox()
        self.doctor_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        self.doctor_combo.currentIndexChanged.connect(self._schedule_context_changed)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumDate(QDate.currentDate())
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.dateChanged.connect(self._schedule_context_changed)
        self.time_combo = ChevronComboBox()
        self.time_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        self.time_combo.addItem("Chọn bác sĩ và ngày khám", None)
        self.time_combo.setEnabled(False)
        self.time_combo.currentIndexChanged.connect(self._update_booking_preview)
        self._add_top_field(fields, 0, 0, "Bác sĩ *", self.doctor_combo)
        self._add_top_field(fields, 1, 0, "Ngày khám *", self.date_edit)
        self._add_top_field(fields, 1, 1, "Khung giờ *", self.time_combo)
        fields.setColumnStretch(0, 1)
        fields.setColumnStretch(1, 1)
        layout.addLayout(fields)

        reason_label = QLabel("Lý do khám")
        reason_label.setObjectName("fieldLabel")
        layout.addWidget(reason_label)
        self.reason_input = QTextEdit()
        self.reason_input.setFixedHeight(76)
        self.reason_input.setPlaceholderText("Mô tả triệu chứng hoặc lý do đến khám")
        self.reason_input.textChanged.connect(self._update_booking_preview)
        layout.addWidget(self.reason_input)

        self.chk_autoconfirm = SemanticCheckBox("Xác nhận ngay sau khi tạo")
        self.chk_autoconfirm.setChecked(True)
        self.chk_autoconfirm.toggled.connect(self._update_booking_preview)
        layout.addWidget(self.chk_autoconfirm)
        confirm_help = QLabel("Tắt tùy chọn để lịch ở trạng thái Chờ xác nhận.")
        confirm_help.setObjectName("mutedLabel")
        confirm_help.setWordWrap(True)
        layout.addWidget(confirm_help)
        return card

    def _build_preview_card(self) -> QFrame:
        self.preview_card = QFrame()
        self.preview_card.setObjectName("contentCard")
        layout = QVBoxLayout(self.preview_card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        heading = QHBoxLayout()
        title = QLabel("Tóm tắt lịch hẹn")
        title.setObjectName("sectionTitle")
        heading.addWidget(title)
        self.prev_status_badge = StatusBadge("CONFIRMED")
        heading.addWidget(self.prev_status_badge)
        heading.addStretch(1)
        layout.addLayout(heading)
        grid = QGridLayout()
        grid.setSpacing(8)
        self.lbl_prev_doctor = self._add_preview_value(grid, 0, "Bác sĩ")
        self.lbl_prev_time = self._add_preview_value(grid, 1, "Thời gian")
        self.lbl_prev_patient = self._add_preview_value(grid, 2, "Bệnh nhân")
        self.lbl_prev_reason = self._add_preview_value(grid, 3, "Lý do")
        layout.addLayout(grid)
        return self.preview_card

    @staticmethod
    def _add_preview_value(grid: QGridLayout, row: int, label: str) -> QLabel:
        grid.addWidget(QLabel(f"{label}:"), row, 0)
        value = QLabel("—")
        value.setObjectName("bookingPreviewStrongValue")
        value.setWordWrap(True)
        grid.addWidget(value, row, 1)
        return value

    def _build_profile_card(self) -> QFrame:
        self.profile_card = QFrame()
        self.profile_card.setObjectName("contentCard")
        layout = QVBoxLayout(self.profile_card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        title = QLabel("Hồ sơ bệnh nhân")
        title.setObjectName("sectionTitle")
        heading.addWidget(title)
        self.badge_profile_status = QLabel("Chưa chọn")
        self.badge_profile_status.setObjectName("patientProfileStatusBadge")
        self.badge_profile_status.setProperty("patientState", "empty")
        heading.addWidget(self.badge_profile_status)
        heading.addStretch(1)
        layout.addLayout(heading)

        self.profile_empty_box = QWidget()
        self.profile_empty_box.setObjectName("layoutWrapper")
        empty_layout = QVBoxLayout(self.profile_empty_box)
        empty_layout.setContentsMargins(0, 4, 0, 4)
        self.lbl_profile_empty_title = QLabel(
            "Tìm hồ sơ ở bên trái hoặc nhập thông tin để tạo hồ sơ mới."
        )
        self.lbl_profile_empty_title.setObjectName("mutedLabel")
        self.lbl_profile_empty_title.setWordWrap(True)
        self.lbl_profile_empty_sub = QLabel("")
        self.lbl_profile_empty_sub.hide()
        empty_layout.addWidget(self.lbl_profile_empty_title)
        layout.addWidget(self.profile_empty_box)

        self.profile_info_box = QWidget()
        self.profile_info_box.setObjectName("layoutWrapper")
        info = QGridLayout(self.profile_info_box)
        info.setContentsMargins(0, 0, 0, 0)
        info.setHorizontalSpacing(12)
        info.setVerticalSpacing(8)
        self.val_p_name = self._add_profile_value(info, 0, "Họ và tên")
        self.val_p_phone = self._add_profile_value(info, 1, "Số điện thoại")
        self.val_p_dob = self._add_profile_value(info, 2, "Ngày sinh / Tuổi")
        self.val_p_gender = self._add_profile_value(info, 3, "Giới tính")
        self.val_p_address = self._add_profile_value(info, 4, "Địa chỉ")
        layout.addWidget(self.profile_info_box)
        self.profile_info_box.hide()
        return self.profile_card

    @staticmethod
    def _add_profile_value(grid: QGridLayout, row: int, label: str) -> QLabel:
        key = QLabel(f"{label}:")
        key.setObjectName("patientProfileMetaLabel")
        grid.addWidget(key, row, 0)
        value = QLabel("—")
        value.setObjectName("patientProfileValue")
        value.setWordWrap(True)
        grid.addWidget(value, row, 1)
        return value

    def _build_history_card(self) -> QFrame:
        self.history_card = QFrame()
        self.history_card.setObjectName("contentCard")
        layout = QVBoxLayout(self.history_card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        title = QLabel("Lịch sử khám gần đây")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        self.history_table = AdaptiveDataTable(
            (
                ColumnSpec(
                    "Ngày khám",
                    "appointment_date",
                    minimum_width=88,
                    preferred_width=100,
                    maximum_width=112,
                    priority=ColumnPriority.HIGH,
                    formatter=format_date,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Bác sĩ",
                    "doctor_name",
                    minimum_width=100,
                    preferred_width=132,
                    maximum_width=210,
                    grow_weight=2,
                    priority=ColumnPriority.NORMAL,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                    stretch=True,
                ),
                ColumnSpec(
                    "Trạng thái",
                    "status",
                    minimum_width=118,
                    preferred_width=124,
                    maximum_width=142,
                    priority=ColumnPriority.CRITICAL,
                    status=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
            ),
            accessible_name="Ba lần khám gần nhất của bệnh nhân",
        )
        self.history_table.setMaximumHeight(226)
        layout.addWidget(self.history_table)
        self.lbl_no_history = QLabel("Bệnh nhân chưa có lịch sử khám.")
        self.lbl_no_history.setObjectName("mutedLabel")
        self.lbl_no_history.setWordWrap(True)
        layout.addWidget(self.lbl_no_history)
        self.lbl_no_history.hide()
        self.history_card.hide()
        return self.history_card

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        if not self._doctors_cache:
            self._load_doctors()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reflow_content()

    def _reflow_content(self, *, force: bool = False) -> None:
        columns = 2 if self.width() >= self.TWO_COLUMN_BREAKPOINT else 1
        if not force and columns == self._content_columns:
            return
        self._content_columns = columns
        if columns == 2:
            self.content_grid.addWidget(self.left_col, 0, 0)
            self.content_grid.addWidget(self.right_col, 0, 1)
            self.content_grid.setColumnStretch(0, 3)
            self.content_grid.setColumnStretch(1, 2)
        else:
            self.content_grid.addWidget(self.left_col, 0, 0)
            self.content_grid.addWidget(self.right_col, 1, 0)
            self.content_grid.setColumnStretch(0, 1)
            self.content_grid.setColumnStretch(1, 0)

    def refresh(self) -> None:
        self._load_doctors()

    def _load_doctors(self) -> None:
        self.run_api_task(
            "load_doctors_catalog",
            lambda: self.api_client.get("/api/v1/catalog/doctors"),
            self._on_doctors_loaded,
            controls=(self.doctor_combo,),
            loading_text="Đang tải danh sách bác sĩ...",
        )

    def _on_doctors_loaded(self, docs: list[dict[str, Any]]) -> None:
        self._doctors_cache = [doc for doc in docs if doc.get("doctor_id")]
        self.doctor_combo.blockSignals(True)
        self.doctor_combo.clear()
        self.doctor_combo.addItem("Chọn bác sĩ", None)
        for doctor in self._doctors_cache:
            name = str(doctor.get("full_name", "")).strip()
            specialty = str(doctor.get("specialty_name", "")).strip()
            label = f"{name} · {specialty}" if specialty else name
            self.doctor_combo.addItem(label, doctor.get("doctor_id"))
        self.doctor_combo.blockSignals(False)
        self.time_combo.clear()
        self.time_combo.addItem(
            "Không có bác sĩ đang hoạt động"
            if not self._doctors_cache
            else "Chọn bác sĩ và ngày khám",
            None,
        )
        self.time_combo.setEnabled(False)
        self._update_booking_preview()

    def _schedule_context_changed(self) -> None:
        self._update_booking_preview()
        self._load_available_slots()

    def _load_available_slots(self) -> None:
        doctor_id = self.doctor_combo.currentData()
        if not doctor_id:
            self.time_combo.clear()
            self.time_combo.addItem("Chọn bác sĩ và ngày khám", None)
            self.time_combo.setEnabled(False)
            return
        date_string = self.date_edit.date().toString(Qt.DateFormat.ISODate)
        self._slot_request_version += 1
        request_version = self._slot_request_version
        self.time_combo.clear()
        self.time_combo.addItem("Đang tải giờ trống...", None)
        self.time_combo.setEnabled(False)
        self.run_api_task(
            f"load_staff_slots:{request_version}",
            lambda selected_doctor=doctor_id, selected_date=date_string: self.api_client.get(
                f"/api/v1/catalog/doctors/{selected_doctor}/available-slots",
                params={"appointment_date": selected_date},
            ),
            self._on_slots_loaded,
            loading_text="Đang tải khung giờ còn trống...",
            is_current=lambda: (
                request_version == self._slot_request_version
                and self.doctor_combo.currentData() == doctor_id
                and self.date_edit.date().toString(Qt.DateFormat.ISODate)
                == date_string
            ),
        )

    def _on_slots_loaded(self, result: dict[str, Any]) -> None:
        self.time_combo.blockSignals(True)
        self.time_combo.clear()
        available = [
            slot
            for slot in result.get("slots", [])
            if isinstance(slot, dict) and slot.get("is_available")
        ]
        if not result.get("has_schedule"):
            self.time_combo.addItem("Bác sĩ không làm việc ngày này", None)
        elif not available:
            self.time_combo.addItem("Ngày này đã hết giờ trống", None)
        else:
            self.time_combo.addItem("Chọn khung giờ", None)
            for slot in available:
                start = str(slot.get("start_time", ""))[:5]
                end = str(slot.get("end_time", ""))[:5]
                self.time_combo.addItem(f"{start}–{end}", (start, end))
        self.time_combo.setEnabled(bool(available))
        self.time_combo.blockSignals(False)
        self._update_booking_preview()

    def _lookup_patient(self) -> None:
        query = self.pt_search_input.text().strip()
        if not query:
            self.feedback.show_message(
                "Chưa có thông tin tìm kiếm",
                "Nhập số điện thoại hoặc tên bệnh nhân để tìm hồ sơ.",
                severity="info",
            )
            return
        self.run_api_task(
            "lookup_patient",
            lambda: self.api_client.get(
                "/api/v1/reception/patients/search", params={"q": query}
            ),
            self._on_patient_search_results,
            controls=(self.pt_search_input, self.btn_lookup),
            loading_text="Đang tìm hồ sơ bệnh nhân...",
        )

    def _on_patient_search_results(self, patients: list[dict[str, Any]]) -> None:
        if not patients:
            self.search_results_table.hide()
            self._reset_patient_selection(keep_search_text=True)
            self.feedback.show_message(
                "Chưa có hồ sơ",
                "Nhập thông tin bên dưới để tạo hồ sơ bệnh nhân mới.",
                severity="info",
            )
            return
        if len(patients) == 1:
            self._select_patient(patients[0])
            self.feedback.show_message(
                "Đã chọn hồ sơ",
                str(patients[0].get("full_name", "")),
                severity="success",
            )
            return
        self.search_results_table.show()
        self.search_results_table.set_rows(
            {
                "patient": CellValue(
                    str(patient.get("full_name", "") or "—"),
                    str(patient.get("phone", "") or "Chưa có số điện thoại"),
                ),
                "date_of_birth": patient.get("date_of_birth"),
                "_actions": "",
            }
            for patient in patients
        )
        for row, patient in enumerate(patients):
            select = QPushButton("Chọn")
            select.setObjectName("tableActionPrimary")
            select.clicked.connect(lambda _, value=patient: self._select_patient(value))
            action_cell = table_action_cell(
                select,
                accessible_name=f"Chọn bệnh nhân {patient.get('full_name', '')}",
            )
            self.search_results_table.setIndexWidget(
                self.search_results_table.model().index(row, 2),
                action_cell,
            )
            self.search_results_table.verticalHeader().resizeSection(row, 60)

    def _select_patient(self, patient: dict[str, Any]) -> None:
        self._selected_patient = patient
        self._selected_patient_id = patient.get("patient_id")
        self.search_results_table.hide()
        self.name_input.setText(str(patient.get("full_name", "")))
        self.phone_input.setText(str(patient.get("phone", "") or ""))
        self.address_input.setText(str(patient.get("address", "") or ""))
        gender = str(patient.get("gender", "") or "").upper()
        index = self.gender_combo.findData(gender)
        self.gender_combo.setCurrentIndex(max(0, index))
        raw_dob = str(patient.get("date_of_birth", "") or "")
        parsed_dob = QDate.fromString(raw_dob[:10], "yyyy-MM-dd")
        self.dob_edit.setDate(parsed_dob if parsed_dob.isValid() else self.NULL_DATE)
        self._set_patient_fields_read_only(True)
        self.pt_type_badge.setText(f"Hồ sơ #{self._selected_patient_id}")
        _set_style_state(self.pt_type_badge, "patientState", "existing")
        self.btn_unselect_pt.show()
        self._update_profile_card_view(patient)
        self.history_card.show()
        self._load_patient_history(str(patient.get("phone", "") or ""))
        self._update_booking_preview()

    def _set_patient_fields_read_only(self, read_only: bool) -> None:
        for field in (self.name_input, self.phone_input, self.address_input):
            field.setReadOnly(read_only)
            field.setProperty("readOnly", read_only)
        self.gender_combo.setEnabled(not read_only)
        self.dob_edit.setEnabled(not read_only)

    def _reset_patient_selection(self, keep_search_text: bool = False) -> None:
        self._selected_patient = None
        self._selected_patient_id = None
        self.search_results_table.hide()
        self.btn_unselect_pt.hide()
        self._set_patient_fields_read_only(False)
        self.pt_type_badge.setText("Hồ sơ mới")
        _set_style_state(self.pt_type_badge, "patientState", "new")
        if not keep_search_text:
            self.pt_search_input.clear()
        self._update_profile_card_view(None)
        self._clear_history_table()
        self.history_card.hide()
        self._update_booking_preview()

    def _update_profile_card_view(self, patient: dict[str, Any] | None) -> None:
        if patient is None:
            self.profile_empty_box.show()
            self.profile_info_box.hide()
            self.badge_profile_status.setText("Chưa chọn")
            _set_style_state(self.badge_profile_status, "patientState", "empty")
            return
        self.profile_empty_box.hide()
        self.profile_info_box.show()
        patient_id = int(patient.get("patient_id") or 0)
        self.badge_profile_status.setText(
            f"#{patient_id:04d}" if patient_id else "Hồ sơ mới"
        )
        _set_style_state(
            self.badge_profile_status,
            "patientState",
            "existing" if patient_id else "draft",
        )
        self.val_p_name.setText(str(patient.get("full_name", "") or "—"))
        self.val_p_phone.setText(str(patient.get("phone", "") or "—"))
        dob = str(patient.get("date_of_birth", "") or "")
        age = ""
        if len(dob) >= 4:
            try:
                age = f" · {date.today().year - int(dob[:4])} tuổi"
            except ValueError:
                pass
        self.val_p_dob.setText(f"{format_date(dob)}{age}" if dob else "—")
        gender = str(patient.get("gender", "") or "").upper()
        self.val_p_gender.setText(
            {"MALE": "Nam", "FEMALE": "Nữ", "OTHER": "Khác"}.get(gender, "—")
        )
        self.val_p_address.setText(str(patient.get("address", "") or "Chưa cập nhật"))
        for label in (
            self.val_p_name,
            self.val_p_phone,
            self.val_p_dob,
            self.val_p_gender,
            self.val_p_address,
        ):
            label.setToolTip(label.text())
            label.setAccessibleName(label.text())

    def _on_patient_input_changed(self) -> None:
        if self._selected_patient:
            return
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        if name or phone:
            dob = ""
            if self.dob_edit.date() != self.NULL_DATE:
                dob = self.dob_edit.date().toString(Qt.DateFormat.ISODate)
            self._update_profile_card_view(
                {
                    "patient_id": 0,
                    "full_name": name or "Bệnh nhân mới",
                    "phone": phone,
                    "date_of_birth": dob,
                    "gender": self.gender_combo.currentData(),
                    "address": self.address_input.text().strip(),
                }
            )
        else:
            self._update_profile_card_view(None)
        self._update_booking_preview()

    def _load_patient_history(self, phone: str) -> None:
        if not phone:
            self._clear_history_table()
            return
        self.run_api_task(
            "load_patient_history",
            lambda: self.api_client.get(
                "/api/v1/reception/appointments",
                params={"keyword": phone, "page_size": 3},
            ),
            self._on_history_loaded,
            loading_text="Đang tải lịch sử khám...",
        )

    def _on_history_loaded(self, data: dict[str, Any]) -> None:
        items = data.get("items", [])[:3]
        if not items:
            self._clear_history_table()
            return
        self.lbl_no_history.hide()
        self.history_table.show()
        self.history_table.set_rows(
            {
                "appointment_date": appointment.get("appointment_date"),
                "doctor_name": appointment.get("doctor", {}).get("full_name", "")
                or "—",
                "status": appointment.get("status", ""),
            }
            for appointment in items
        )
        for row in range(len(items)):
            self.history_table.verticalHeader().resizeSection(row, 60)

    def _clear_history_table(self) -> None:
        self.history_table.set_rows(())
        self.history_table.hide()
        self.lbl_no_history.show()

    def _update_booking_preview(self) -> None:
        doctor = (
            self.doctor_combo.currentText()
            if self.doctor_combo.currentData()
            else "Chưa chọn"
        )
        self.lbl_prev_doctor.setText(doctor)
        selected_slot = self.time_combo.currentData()
        date_text = self.date_edit.date().toString("dd/MM/yyyy")
        time_text = (
            self.time_combo.currentText() if selected_slot else "Chưa chọn khung giờ"
        )
        self.lbl_prev_time.setText(f"{time_text} · {date_text}")
        patient_name = self.name_input.text().strip()
        self.lbl_prev_patient.setText(patient_name or "Chưa nhập thông tin")
        reason = self.reason_input.toPlainText().strip()
        self.lbl_prev_reason.setText(reason or "Chưa nhập lý do khám")
        for label in (
            self.lbl_prev_doctor,
            self.lbl_prev_time,
            self.lbl_prev_patient,
            self.lbl_prev_reason,
        ):
            label.setToolTip(label.text())
            label.setAccessibleName(label.text())
        self.prev_status_badge.set_status(
            "CONFIRMED" if self.chk_autoconfirm.isChecked() else "PENDING"
        )

    def _clear_form(self, *, preserve_feedback: bool = False) -> None:
        self._reset_patient_selection()
        self.name_input.clear()
        self.phone_input.clear()
        self.address_input.clear()
        self.gender_combo.setCurrentIndex(0)
        self.dob_edit.setDate(self.NULL_DATE)
        self.reason_input.clear()
        self.date_edit.setDate(QDate.currentDate())
        self.doctor_combo.setCurrentIndex(0)
        self.chk_autoconfirm.setChecked(True)
        if not preserve_feedback:
            self.feedback.clear()
        self._update_booking_preview()

    def _submit_booking(self) -> None:
        full_name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        if not full_name or not phone:
            self.feedback.show_message(
                "Thiếu thông tin bắt buộc",
                "Nhập họ tên và số điện thoại bệnh nhân.",
                severity="error",
            )
            return
        doctor_id = self.doctor_combo.currentData()
        slot = self.time_combo.currentData()
        if not doctor_id or not isinstance(slot, tuple) or len(slot) != 2:
            self.feedback.show_message(
                "Chưa chọn lịch khám",
                "Chọn bác sĩ, ngày khám và một khung giờ còn trống.",
                severity="error",
            )
            return
        start, end = slot
        payload: dict[str, Any] = {
            "doctor_id": doctor_id,
            "appointment_date": self.date_edit.date().toString(Qt.DateFormat.ISODate),
            "start_time": f"{start}:00",
            "end_time": f"{end}:00",
            "reason": self.reason_input.toPlainText().strip()
            or "Đặt lịch khám tại quầy tiếp đón",
            "auto_confirm": self.chk_autoconfirm.isChecked(),
        }
        if self._selected_patient_id:
            payload["patient_id"] = self._selected_patient_id
        else:
            payload.update(
                {
                    "full_name": full_name,
                    "phone": phone,
                    "gender": self.gender_combo.currentData(),
                    "address": self.address_input.text().strip() or None,
                    "date_of_birth": (
                        self.dob_edit.date().toString(Qt.DateFormat.ISODate)
                        if self.dob_edit.date() != self.NULL_DATE
                        else None
                    ),
                }
            )
        self.run_api_task(
            "book_for_patient",
            lambda: self.api_client.post(
                "/api/v1/reception/appointments/book", json=payload
            ),
            self._on_booking_success,
            controls=(self.btn_submit, self.btn_reset),
            loading_text="Đang tạo lịch hẹn...",
        )

    def _on_booking_success(self, result: dict[str, Any]) -> None:
        appointment_id = result.get("appointment_id", 0)
        patient_name = self.name_input.text().strip()
        self._clear_form(preserve_feedback=True)
        self.feedback.show_message(
            "Tạo lịch hẹn thành công",
            f"Đã tạo lịch hẹn #{appointment_id} cho {patient_name}.",
            severity="success",
        )
        self.appointment_booked.emit(result)
