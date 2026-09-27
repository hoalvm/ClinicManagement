"""Book Appointment for Patient (Walk-in or Phone Call) View with Live Patient Profile Panel."""

from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.views.common import BaseApiView
from frontend.widgets.page_header import PageHeader
from frontend.widgets.status_badge import StatusBadge


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
    """View allowing clinic receptionist to book an appointment with live patient profile sidebar."""

    appointment_booked = Signal(dict)
    TWO_COLUMN_BREAKPOINT = 1050

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)

        self._selected_patient: dict[str, Any] | None = None
        self._selected_patient_id: int | None = None
        self._doctors_cache: list[dict[str, Any]] = []

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        container = QWidget()
        # The page body must follow the viewport width. Long combo-box items and
        # form labels otherwise leak their size hint into QScrollArea and create
        # a hidden/clipped horizontal overflow at the supported minimum size.
        container.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        main_vbox = QVBoxLayout(container)
        main_vbox.setContentsMargins(24, 24, 24, 24)
        main_vbox.setSpacing(16)

        self.header = PageHeader(
            "Đặt lịch cho bệnh nhân",
            "Tiếp nhận đặt lịch trực tiếp tại quầy hoặc qua điện thoại",
            action_label="Làm mới form",
            parent=self,
        )
        self.header.action_clicked.connect(self._clear_form)
        main_vbox.addWidget(self.header)
        main_vbox.addWidget(self.feedback)
        main_vbox.addWidget(self.loading)

        # 2-Column Layout: Left Column (Form) & Right Column (Patient Profile & Live Preview)
        self.content_grid = QGridLayout()
        self.content_grid.setHorizontalSpacing(20)
        self.content_grid.setVerticalSpacing(16)
        self.content_grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        # =========================================================================
        # LEFT COLUMN: Booking Form & Patient Intake (Stretch: 3)
        # =========================================================================
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

        # Card 1: Patient Search & Demographics
        pt_card = QFrame()
        pt_card.setObjectName("contentCard")
        pt_card_layout = QVBoxLayout(pt_card)
        pt_card_layout.setContentsMargins(20, 18, 20, 18)
        pt_card_layout.setSpacing(14)

        pt_sec_header = QHBoxLayout()
        pt_sec_title = QLabel("1. Thông tin bệnh nhân")
        pt_sec_title.setObjectName("sectionTitle")
        pt_sec_title.setWordWrap(True)
        pt_sec_header.addWidget(pt_sec_title)

        self.pt_type_badge = QLabel("Bệnh nhân mới")
        self.pt_type_badge.setObjectName("patientTypeBadge")
        self.pt_type_badge.setProperty("patientState", "new")
        self.pt_type_badge.setWordWrap(True)
        pt_sec_header.addWidget(self.pt_type_badge)
        pt_sec_header.addStretch(1)

        self.btn_unselect_pt = QPushButton("Bỏ chọn (Tạo mới)")
        self.btn_unselect_pt.setObjectName("ghostButton")
        self.btn_unselect_pt.setProperty("bookingRole", "unselectPatient")
        self.btn_unselect_pt.setCursor(Qt.PointingHandCursor)
        self.btn_unselect_pt.clicked.connect(self._reset_patient_selection)
        self.btn_unselect_pt.hide()
        pt_sec_header.addWidget(self.btn_unselect_pt)

        pt_card_layout.addLayout(pt_sec_header)

        # Lookup Row
        lookup_box = QFrame()
        lookup_box.setObjectName("filterCard")
        lookup_layout = QVBoxLayout(lookup_box)
        lookup_layout.setContentsMargins(14, 12, 14, 12)
        lookup_layout.setSpacing(8)

        lookup_input_row = QHBoxLayout()
        lookup_lbl = QLabel("Tra cứu hồ sơ cũ:")
        lookup_lbl.setObjectName("fieldLabel")
        lookup_input_row.addWidget(lookup_lbl)

        self.pt_search_input = QLineEdit()
        self.pt_search_input.setAccessibleName("Tra cứu hồ sơ bệnh nhân")
        self.pt_search_input.setPlaceholderText(
            "Nhập số điện thoại hoặc họ tên bệnh nhân..."
        )
        self.pt_search_input.returnPressed.connect(self._lookup_patient)
        lookup_input_row.addWidget(self.pt_search_input, 1)

        self.btn_lookup = QPushButton("Tra cứu")
        self.btn_lookup.setCursor(Qt.PointingHandCursor)
        self.btn_lookup.clicked.connect(self._lookup_patient)
        lookup_input_row.addWidget(self.btn_lookup)

        lookup_layout.addLayout(lookup_input_row)

        # Quick Results Picker (hidden by default)
        self.search_results_table = QTableWidget()
        self.search_results_table.setAccessibleName("Kết quả tra cứu bệnh nhân")
        self.search_results_table.setColumnCount(4)
        self.search_results_table.setHorizontalHeaderLabels(
            ["Họ tên", "Số điện thoại", "Ngày sinh", "Thao tác"]
        )
        self.search_results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.search_results_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.search_results_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.search_results_table.setMaximumHeight(130)
        self.search_results_table.hide()
        lookup_layout.addWidget(self.search_results_table)

        pt_card_layout.addWidget(lookup_box)

        # Patient Demographics Form
        pt_form = QFormLayout()
        pt_form.setSpacing(12)
        pt_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        pt_form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        pt_form.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nhập họ và tên đầy đủ")
        self.name_input.textChanged.connect(self._on_patient_input_changed)
        pt_form.addRow("Họ và tên (*):", self.name_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Nhập số điện thoại liên hệ")
        self.phone_input.textChanged.connect(self._on_patient_input_changed)
        pt_form.addRow("Số điện thoại (*):", self.phone_input)

        gender_dob_row = QHBoxLayout()
        self.gender_combo = QComboBox()
        self.gender_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        self.gender_combo.addItem("Nam", "MALE")
        self.gender_combo.addItem("Nữ", "FEMALE")
        self.gender_combo.addItem("Khác", "OTHER")
        self.gender_combo.currentIndexChanged.connect(self._on_patient_input_changed)
        gender_dob_row.addWidget(self.gender_combo, 1)

        dob_lbl = QLabel("Ngày sinh:")
        dob_lbl.setObjectName("bookingInlineFieldLabel")
        gender_dob_row.addWidget(dob_lbl)

        self.dob_edit = QDateEdit()
        self.dob_edit.setCalendarPopup(True)
        self.dob_edit.setDate(QDate.currentDate().addYears(-30))
        self.dob_edit.setDisplayFormat("yyyy-MM-dd")
        self.dob_edit.dateChanged.connect(self._on_patient_input_changed)
        gender_dob_row.addWidget(self.dob_edit, 1)

        pt_form.addRow("Giới tính & Ngày sinh:", gender_dob_row)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Nhập địa chỉ cư trú (tùy chọn)")
        self.address_input.textChanged.connect(self._on_patient_input_changed)
        pt_form.addRow("Địa chỉ:", self.address_input)

        pt_card_layout.addLayout(pt_form)
        left_layout.addWidget(pt_card)

        # Card 2: Appointment Scheduling
        appt_card = QFrame()
        appt_card.setObjectName("contentCard")
        appt_card_layout = QVBoxLayout(appt_card)
        appt_card_layout.setContentsMargins(20, 18, 20, 18)
        appt_card_layout.setSpacing(14)

        appt_sec_title = QLabel("2. Thông tin lịch khám")
        appt_sec_title.setObjectName("sectionTitle")
        appt_card_layout.addWidget(appt_sec_title)

        appt_form = QFormLayout()
        appt_form.setSpacing(12)
        appt_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        appt_form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        appt_form.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self.doctor_combo = QComboBox()
        self.doctor_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        self.doctor_combo.currentIndexChanged.connect(self._update_booking_preview)
        appt_form.addRow("Bác sĩ phụ trách (*):", self.doctor_combo)

        date_time_row = QHBoxLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.dateChanged.connect(self._update_booking_preview)
        date_time_row.addWidget(self.date_edit, 1)

        time_lbl = QLabel("Khung giờ:")
        time_lbl.setObjectName("bookingInlineFieldLabel")
        date_time_row.addWidget(time_lbl)

        self.time_combo = QComboBox()
        self.time_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        self.time_combo.addItems(
            [
                "08:00 - 08:30",
                "08:30 - 09:00",
                "09:00 - 09:30",
                "09:30 - 10:00",
                "10:00 - 10:30",
                "10:30 - 11:00",
                "13:30 - 14:00",
                "14:00 - 14:30",
                "14:30 - 15:00",
                "15:00 - 15:30",
                "15:30 - 16:00",
                "16:00 - 16:30",
            ]
        )
        self.time_combo.currentIndexChanged.connect(self._update_booking_preview)
        date_time_row.addWidget(self.time_combo, 1)

        appt_form.addRow("Ngày & Giờ khám (*):", date_time_row)

        self.reason_input = QTextEdit()
        self.reason_input.setMaximumHeight(70)
        self.reason_input.setPlaceholderText("Mô tả triệu chứng hoặc lý do đến khám...")
        self.reason_input.textChanged.connect(self._update_booking_preview)
        appt_form.addRow("Lý do khám:", self.reason_input)

        self.chk_autoconfirm = QCheckBox(
            "Tự động xác nhận lịch hẹn (Trạng thái: Đã xác nhận)"
        )
        self.chk_autoconfirm.setChecked(True)
        self.chk_autoconfirm.toggled.connect(self._update_booking_preview)
        appt_form.addRow("", self.chk_autoconfirm)

        appt_card_layout.addLayout(appt_form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_reset = QPushButton("Làm mới")
        self.btn_reset.setObjectName("secondaryButton")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self._clear_form)
        btn_row.addWidget(self.btn_reset)

        self.btn_submit = QPushButton("Tạo lịch khám")
        self.btn_submit.setObjectName("primaryButton")
        self.btn_submit.setCursor(Qt.PointingHandCursor)
        self.btn_submit.clicked.connect(self._submit_booking)
        btn_row.addWidget(self.btn_submit)

        appt_card_layout.addLayout(btn_row)
        left_layout.addWidget(appt_card)

        self.content_grid.addWidget(self.left_col, 0, 0)

        # =========================================================================
        # RIGHT COLUMN: "Thanh bên phải" - Patient Profile, History & Booking Preview (Stretch: 2)
        # =========================================================================
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

        # Panel 1: Patient Profile Card
        self.profile_card = QFrame()
        self.profile_card.setObjectName("contentCard")
        profile_layout = QVBoxLayout(self.profile_card)
        profile_layout.setContentsMargins(18, 16, 18, 16)
        profile_layout.setSpacing(14)

        card1_top = QHBoxLayout()
        card1_title = QLabel("Hồ sơ bệnh nhân")
        card1_title.setObjectName("sectionTitle")
        card1_top.addWidget(card1_title)

        self.badge_profile_status = QLabel("Chưa chọn")
        self.badge_profile_status.setObjectName("patientProfileStatusBadge")
        self.badge_profile_status.setProperty("patientState", "empty")
        card1_top.addWidget(self.badge_profile_status)
        card1_top.addStretch(1)
        profile_layout.addLayout(card1_top)

        # Empty state inside profile card
        self.profile_empty_box = QFrame()
        self.profile_empty_box.setObjectName("patientProfileEmptyState")
        empty_box_layout = QVBoxLayout(self.profile_empty_box)
        empty_box_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_profile_empty_title = QLabel("Chưa có thông tin bệnh nhân")
        self.lbl_profile_empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_profile_empty_title.setObjectName("patientProfileEmptyTitle")
        self.lbl_profile_empty_sub = QLabel("N/A")
        self.lbl_profile_empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_profile_empty_sub.setObjectName("patientProfileEmptyDescription")
        self.lbl_profile_empty_sub.setWordWrap(True)
        empty_box_layout.addWidget(self.lbl_profile_empty_title)
        empty_box_layout.addWidget(self.lbl_profile_empty_sub)
        profile_layout.addWidget(self.profile_empty_box)

        # Populated info grid
        self.profile_info_box = QWidget()
        self.profile_info_box.setObjectName("layoutWrapper")
        info_grid = QGridLayout(self.profile_info_box)
        info_grid.setContentsMargins(0, 0, 0, 0)
        info_grid.setHorizontalSpacing(12)
        info_grid.setVerticalSpacing(8)

        lbl_c_name = QLabel("Họ và tên:")
        lbl_c_name.setObjectName("patientProfileMetaLabel")
        self.val_p_name = QLabel("—")
        self.val_p_name.setWordWrap(True)
        self.val_p_name.setObjectName("patientProfileName")
        info_grid.addWidget(lbl_c_name, 0, 0)
        info_grid.addWidget(self.val_p_name, 0, 1)

        lbl_c_phone = QLabel("Số điện thoại:")
        lbl_c_phone.setObjectName("patientProfileMetaLabel")
        self.val_p_phone = QLabel("—")
        self.val_p_phone.setObjectName("patientProfileStrongValue")
        info_grid.addWidget(lbl_c_phone, 1, 0)
        info_grid.addWidget(self.val_p_phone, 1, 1)

        lbl_c_dob = QLabel("Ngày sinh / Tuổi:")
        lbl_c_dob.setObjectName("patientProfileMetaLabel")
        self.val_p_dob = QLabel("—")
        self.val_p_dob.setObjectName("patientProfileValue")
        info_grid.addWidget(lbl_c_dob, 2, 0)
        info_grid.addWidget(self.val_p_dob, 2, 1)

        lbl_c_gender = QLabel("Giới tính:")
        lbl_c_gender.setObjectName("patientProfileMetaLabel")
        self.val_p_gender = QLabel("—")
        self.val_p_gender.setObjectName("patientProfileValue")
        info_grid.addWidget(lbl_c_gender, 3, 0)
        info_grid.addWidget(self.val_p_gender, 3, 1)

        lbl_c_addr = QLabel("Địa chỉ:")
        lbl_c_addr.setObjectName("patientProfileMetaLabel")
        self.val_p_address = QLabel("—")
        self.val_p_address.setObjectName("patientProfileValue")
        self.val_p_address.setWordWrap(True)
        info_grid.addWidget(lbl_c_addr, 4, 0)
        info_grid.addWidget(self.val_p_address, 4, 1)

        profile_layout.addWidget(self.profile_info_box)
        self.profile_info_box.hide()

        right_layout.addWidget(self.profile_card)

        # Panel 2: Recent Appointment History Card
        self.history_card = QFrame()
        self.history_card.setObjectName("contentCard")
        history_layout = QVBoxLayout(self.history_card)
        history_layout.setContentsMargins(18, 16, 18, 16)
        history_layout.setSpacing(10)

        card2_title = QLabel("Lịch sử khám gần đây")
        card2_title.setObjectName("sectionTitle")
        history_layout.addWidget(card2_title)

        self.history_table = QTableWidget()
        self.history_table.setAccessibleName("Lịch sử khám gần đây của bệnh nhân")
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(
            ["Ngày", "Bác sĩ", "Trạng thái", "Lý do"]
        )
        self.history_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.history_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setMaximumHeight(140)
        history_layout.addWidget(self.history_table)

        self.lbl_no_history = QLabel("Chưa có lịch sử khám bệnh trước đây.")
        self.lbl_no_history.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_history.setObjectName("patientHistoryEmptyText")
        history_layout.addWidget(self.lbl_no_history)
        self.lbl_no_history.hide()

        right_layout.addWidget(self.history_card)

        # Panel 3: Live Booking Preview Card
        self.preview_card = QFrame()
        self.preview_card.setObjectName("previewCard")
        prev_layout = QVBoxLayout(self.preview_card)
        prev_layout.setContentsMargins(18, 16, 18, 16)
        prev_layout.setSpacing(10)

        prev_header = QHBoxLayout()
        prev_title = QLabel("Tóm tắt lịch khám dự kiến")
        prev_title.setObjectName("sectionTitle")
        prev_title.setProperty("bookingRole", "previewTitle")
        prev_title.setWordWrap(True)
        prev_header.addWidget(prev_title)

        self.prev_status_badge = StatusBadge("CONFIRMED")
        prev_header.addWidget(self.prev_status_badge)
        prev_header.addStretch(1)
        prev_layout.addLayout(prev_header)

        prev_grid = QGridLayout()
        prev_grid.setSpacing(8)

        prev_grid.addWidget(QLabel("Bác sĩ:"), 0, 0)
        self.lbl_prev_doctor = QLabel("—")
        self.lbl_prev_doctor.setWordWrap(True)
        self.lbl_prev_doctor.setObjectName("bookingPreviewStrongValue")
        prev_grid.addWidget(self.lbl_prev_doctor, 0, 1)

        prev_grid.addWidget(QLabel("Thời gian:"), 1, 0)
        self.lbl_prev_time = QLabel("—")
        self.lbl_prev_time.setObjectName("bookingPreviewStrongValue")
        prev_grid.addWidget(self.lbl_prev_time, 1, 1)

        prev_grid.addWidget(QLabel("Bệnh nhân:"), 2, 0)
        self.lbl_prev_patient = QLabel("—")
        self.lbl_prev_patient.setWordWrap(True)
        self.lbl_prev_patient.setObjectName("bookingPreviewStrongValue")
        prev_grid.addWidget(self.lbl_prev_patient, 2, 1)

        prev_grid.addWidget(QLabel("Lý do khám:"), 3, 0)
        self.lbl_prev_reason = QLabel("Khám thông thường")
        self.lbl_prev_reason.setObjectName("bookingPreviewReason")
        self.lbl_prev_reason.setWordWrap(True)
        prev_grid.addWidget(self.lbl_prev_reason, 3, 1)

        prev_layout.addLayout(prev_grid)
        right_layout.addWidget(self.preview_card)

        self.content_grid.addWidget(self.right_col, 0, 1)
        self._content_columns = 0
        main_vbox.addLayout(self.content_grid)
        self._reflow_content(force=True)

        self.scroll_area.setWidget(container)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.scroll_area)

        # Load initial doctors and refresh UI
        self._load_doctors()
        self._update_booking_preview()

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        if not self._doctors_cache:
            self._load_doctors()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reflow_content()

    def _reflow_content(self, *, force: bool = False) -> None:
        # The shell consumes 78 px in compact mode at the supported 1100 px
        # viewport.  Base the breakpoint on the page width so that that case
        # never selects the two-column layout and creates page-level overflow.
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
            loading_text="Đang tải danh sách bác sĩ...",
        )

    def _on_doctors_loaded(self, docs: list[dict[str, Any]]) -> None:
        if not docs:
            # Fallback mock items if server returns empty
            self._populate_fallback_doctors()
            return

        self._doctors_cache = docs
        self.doctor_combo.blockSignals(True)
        self.doctor_combo.clear()
        for d in docs:
            doc_id = d.get("doctor_id")
            doc_name = d.get("full_name", "")
            spec_name = d.get("specialty_name", "")
            label = f"BS. {doc_name} ({spec_name})" if spec_name else f"BS. {doc_name}"
            self.doctor_combo.addItem(label, doc_id)
        self.doctor_combo.blockSignals(False)
        self._update_booking_preview()

    def _populate_fallback_doctors(self) -> None:
        self.doctor_combo.blockSignals(True)
        self.doctor_combo.clear()
        self.doctor_combo.addItem("BS. Lê Thị Mai (Nội tổng quát)", 1)
        self.doctor_combo.addItem("BS. Trần Văn Đức (Tim mạch)", 2)
        self.doctor_combo.addItem("BS. Phạm Minh Trí (Nhi khoa)", 3)
        self.doctor_combo.blockSignals(False)
        self._update_booking_preview()

    # -------------------------------------------------------------------------
    # Patient Lookup & Selection Logic
    # -------------------------------------------------------------------------
    def _lookup_patient(self) -> None:
        q = self.pt_search_input.text().strip()
        if not q:
            self.feedback.show_message(
                "Tìm kiếm",
                "Vui lòng nhập số điện thoại hoặc tên bệnh nhân.",
                severity="info",
            )
            return

        self.run_api_task(
            "lookup_patient",
            lambda: self.api_client.get(
                "/api/v1/reception/patients/search", params={"q": q}
            ),
            self._on_patient_search_results,
            loading_text="Đang tra cứu hồ sơ bệnh nhân...",
        )

    def _on_patient_search_results(self, patients: list[dict[str, Any]]) -> None:
        if not patients:
            self.search_results_table.hide()
            self.feedback.show_message(
                "Không tìm thấy",
                "Chưa có hồ sơ cho thông tin này. Bạn có thể nhập thông tin bên dưới để tạo bệnh nhân mới.",
                severity="info",
            )
            self._reset_patient_selection(keep_search_text=True)
            return

        if len(patients) == 1:
            self.search_results_table.hide()
            self._select_patient(patients[0])
            self.feedback.show_message(
                "Đã tìm thấy",
                f"Đã nạp hồ sơ bệnh nhân cũ: {patients[0].get('full_name')}",
                severity="success",
            )
        else:
            # Show list so receptionist can pick the exact patient
            self.search_results_table.show()
            self.search_results_table.setRowCount(len(patients))
            for row, p in enumerate(patients):
                name_item = QTableWidgetItem(p.get("full_name", ""))
                phone_item = QTableWidgetItem(p.get("phone", "") or "—")
                dob_item = QTableWidgetItem(str(p.get("date_of_birth", "")) or "—")
                for result_item in (name_item, phone_item, dob_item):
                    result_item.setToolTip(result_item.text())

                self.search_results_table.setItem(row, 0, name_item)
                self.search_results_table.setItem(row, 1, phone_item)
                self.search_results_table.setItem(row, 2, dob_item)

                btn_select = QPushButton("Chọn")
                btn_select.setObjectName("tableActionPrimary")
                btn_select.setCursor(Qt.PointingHandCursor)
                btn_select.setAccessibleName(
                    f"Chọn bệnh nhân {p.get('full_name', '')}"
                )
                btn_select.clicked.connect(lambda _, pat=p: self._select_patient(pat))
                self.search_results_table.setCellWidget(row, 3, btn_select)
                self.search_results_table.setRowHeight(row, 40)

            self.feedback.show_message(
                "Tìm thấy nhiều kết quả",
                f"Tìm thấy {len(patients)} bệnh nhân. Vui lòng bấm 'Chọn' ở bệnh nhân tương ứng.",
                severity="info",
            )

    def _select_patient(self, p: dict[str, Any]) -> None:
        self._selected_patient = p
        self._selected_patient_id = p.get("patient_id")
        self.search_results_table.hide()

        # Update left form fields
        self.name_input.setText(p.get("full_name", ""))
        self.phone_input.setText(p.get("phone", "") or "")
        self.address_input.setText(p.get("address", "") or "")

        gender = (p.get("gender") or "MALE").upper()
        for i in range(self.gender_combo.count()):
            if self.gender_combo.itemData(i) == gender:
                self.gender_combo.setCurrentIndex(i)
                break

        dob_str = str(p.get("date_of_birth") or "")
        if dob_str:
            qdate = QDate.fromString(dob_str[:10], "yyyy-MM-dd")
            if qdate.isValid():
                self.dob_edit.setDate(qdate)

        # Update patient status indicator
        self.pt_type_badge.setText(
            f"Hồ sơ bệnh nhân cũ (#PT-{self._selected_patient_id})"
        )
        _set_style_state(self.pt_type_badge, "patientState", "existing")
        self.btn_unselect_pt.show()

        # Update right panel profile card
        self._update_profile_card_view(p)

        # Fetch recent appointments history for this patient
        phone = p.get("phone") or ""
        self._load_patient_history(phone)
        self._update_booking_preview()

    def _reset_patient_selection(self, keep_search_text: bool = False) -> None:
        self._selected_patient = None
        self._selected_patient_id = None
        self.search_results_table.hide()
        self.btn_unselect_pt.hide()

        self.pt_type_badge.setText("Bệnh nhân mới")
        _set_style_state(self.pt_type_badge, "patientState", "new")

        if not keep_search_text:
            self.pt_search_input.clear()

        # Reset right profile panel
        self._update_profile_card_view(None)
        self._clear_history_table()
        self._update_booking_preview()

    def _update_profile_card_view(self, p: dict[str, Any] | None) -> None:
        if not p:
            # Show empty state in card 1
            self.profile_empty_box.show()
            self.profile_info_box.hide()
            self.badge_profile_status.setText("Chưa chọn")
            _set_style_state(self.badge_profile_status, "patientState", "empty")
            return

        self.profile_empty_box.hide()
        self.profile_info_box.show()

        pt_id = p.get("patient_id", 0)
        self.badge_profile_status.setText(f"#PT-{pt_id:04d} • Bệnh nhân cũ")
        _set_style_state(self.badge_profile_status, "patientState", "existing")

        self.val_p_name.setText(p.get("full_name", "—"))
        self.val_p_name.setToolTip(self.val_p_name.text())
        self.val_p_name.setAccessibleName(self.val_p_name.text())
        self.val_p_phone.setText(p.get("phone", "—") or "—")

        # Calculate age if DOB available
        dob_str = str(p.get("date_of_birth", "") or "")
        age_str = ""
        if dob_str and len(dob_str) >= 4:
            try:
                birth_year = int(dob_str[:4])
                curr_year = date.today().year
                age_str = f" ({curr_year - birth_year} tuổi)"
            except ValueError:
                pass
        self.val_p_dob.setText(f"{dob_str}{age_str}" if dob_str else "—")

        gender_code = (p.get("gender") or "").upper()
        gender_map = {"MALE": "Nam", "FEMALE": "Nữ", "OTHER": "Khác"}
        self.val_p_gender.setText(gender_map.get(gender_code, gender_code or "—"))
        self.val_p_address.setText(p.get("address", "") or "Chưa cập nhật")
        self.val_p_address.setToolTip(self.val_p_address.text())
        self.val_p_address.setAccessibleName(self.val_p_address.text())

    def _on_patient_input_changed(self) -> None:
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()

        # If receptionist is manually typing and no old patient was selected:
        if not self._selected_patient:
            if name or phone:
                # Update right profile card live with new patient draft info
                draft = {
                    "patient_id": 0,
                    "full_name": name or "Bệnh nhân mới",
                    "phone": phone or "Chưa có SĐT",
                    "date_of_birth": self.dob_edit.date().toString("yyyy-MM-dd"),
                    "gender": self.gender_combo.currentData(),
                    "address": self.address_input.text().strip() or "Chưa có địa chỉ",
                }
                self.profile_empty_box.hide()
                self.profile_info_box.show()
                self.badge_profile_status.setText("Bệnh nhân mới (Dự thảo)")
                _set_style_state(self.badge_profile_status, "patientState", "draft")
                self.val_p_name.setText(draft["full_name"])
                self.val_p_phone.setText(draft["phone"])
                self.val_p_dob.setText(draft["date_of_birth"])
                gender_map = {"MALE": "Nam", "FEMALE": "Nữ", "OTHER": "Khác"}
                self.val_p_gender.setText(gender_map.get(draft["gender"], "Khác"))
                self.val_p_address.setText(draft["address"])
            else:
                self._update_profile_card_view(None)

        self._update_booking_preview()

    # -------------------------------------------------------------------------
    # Appointment History Logic
    # -------------------------------------------------------------------------
    def _load_patient_history(self, phone: str) -> None:
        if not phone:
            self._clear_history_table()
            return

        self.run_api_task(
            "load_patient_history",
            lambda: self.api_client.get(
                "/api/v1/reception/appointments",
                params={"keyword": phone, "page_size": 10},
            ),
            self._on_history_loaded,
            loading_text="Đang tải lịch sử khám...",
        )

    def _on_history_loaded(self, data: dict[str, Any]) -> None:
        items = data.get("items", [])
        if not items:
            self._clear_history_table()
            return

        self.lbl_no_history.hide()
        self.history_table.show()
        self.history_table.setRowCount(len(items))

        for row, appt in enumerate(items):
            appt_date = str(appt.get("appointment_date", ""))
            doctor = appt.get("doctor", {})
            doc_name = doctor.get("full_name", "Bác sĩ")
            status = appt.get("status", "")
            reason = appt.get("reason", "") or "—"

            item_date = QTableWidgetItem(appt_date)
            item_date.setToolTip(appt_date)
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_table.setItem(row, 0, item_date)

            item_doc = QTableWidgetItem(f"BS. {doc_name}")
            item_doc.setToolTip(item_doc.text())
            self.history_table.setItem(row, 1, item_doc)

            item_status = QTableWidgetItem(status)
            item_status.setToolTip(status)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_table.setItem(row, 2, item_status)

            item_reason = QTableWidgetItem(reason)
            item_reason.setToolTip(reason)
            self.history_table.setItem(row, 3, item_reason)
            self.history_table.setRowHeight(row, 32)

    def _clear_history_table(self) -> None:
        self.history_table.setRowCount(0)
        self.history_table.hide()
        self.lbl_no_history.show()

    # -------------------------------------------------------------------------
    # Live Booking Preview Logic
    # -------------------------------------------------------------------------
    def _update_booking_preview(self) -> None:
        # Doctor
        doc_text = self.doctor_combo.currentText() or "Chưa chọn bác sĩ"
        self.lbl_prev_doctor.setText(doc_text)
        self.lbl_prev_doctor.setToolTip(doc_text)
        self.lbl_prev_doctor.setAccessibleName(doc_text)

        # Date & Time
        appt_date_str = self.date_edit.date().toString("dd/MM/yyyy")
        time_slot = self.time_combo.currentText() or ""
        self.lbl_prev_time.setText(f"{time_slot}, {appt_date_str}")

        # Patient name
        pt_name = self.name_input.text().strip()
        if self._selected_patient:
            self.lbl_prev_patient.setText(
                f"{pt_name} (#PT-{self._selected_patient_id})"
            )
        elif pt_name:
            self.lbl_prev_patient.setText(f"{pt_name} (BN mới)")
        else:
            self.lbl_prev_patient.setText("Chưa nhập tên bệnh nhân")
        self.lbl_prev_patient.setToolTip(self.lbl_prev_patient.text())
        self.lbl_prev_patient.setAccessibleName(self.lbl_prev_patient.text())

        # Reason
        reason_text = self.reason_input.toPlainText().strip()
        self.lbl_prev_reason.setText(
            reason_text if reason_text else "Tiếp nhận tại quầy phòng khám"
        )
        self.lbl_prev_reason.setToolTip(self.lbl_prev_reason.text())
        self.lbl_prev_reason.setAccessibleName(self.lbl_prev_reason.text())

        # Status badge
        is_autoconfirm = self.chk_autoconfirm.isChecked()
        self.prev_status_badge.set_status("CONFIRMED" if is_autoconfirm else "PENDING")

    # -------------------------------------------------------------------------
    # Form Reset & Booking Submission
    # -------------------------------------------------------------------------
    def _clear_form(self) -> None:
        self._reset_patient_selection()
        self.name_input.clear()
        self.phone_input.clear()
        self.address_input.clear()
        self.reason_input.clear()
        self.date_edit.setDate(QDate.currentDate())
        self.chk_autoconfirm.setChecked(True)
        self.feedback.clear()
        self._update_booking_preview()

    def _submit_booking(self) -> None:
        full_name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()

        if not full_name or not phone:
            self.feedback.show_message(
                "Thiếu thông tin bắt buộc",
                "Vui lòng nhập họ tên và số điện thoại người bệnh trước khi đặt lịch.",
                severity="error",
            )
            return

        doctor_id = self.doctor_combo.currentData()
        if not doctor_id:
            self.feedback.show_message(
                "Chưa chọn bác sĩ",
                "Vui lòng chọn bác sĩ phụ trách khám.",
                severity="error",
            )
            return

        time_parts = self.time_combo.currentText().split(" - ")
        start_str = time_parts[0] + ":00" if len(time_parts) > 0 else "08:00:00"
        end_str = time_parts[1] + ":00" if len(time_parts) > 1 else "08:30:00"

        appt_date = self.date_edit.date().toString("yyyy-MM-dd")
        dob = self.dob_edit.date().toString("yyyy-MM-dd")
        gender_code = self.gender_combo.currentData() or "MALE"

        payload: dict[str, Any] = {
            "doctor_id": doctor_id,
            "appointment_date": appt_date,
            "start_time": start_str,
            "end_time": end_str,
            "reason": self.reason_input.toPlainText().strip()
            or "Đặt lịch khám tại quầy tiếp đón",
            "auto_confirm": self.chk_autoconfirm.isChecked(),
        }

        # If old patient is chosen, pass patient_id. Otherwise pass demographics for new patient creation.
        if self._selected_patient_id:
            payload["patient_id"] = self._selected_patient_id
            payload["full_name"] = full_name
            payload["phone"] = phone
        else:
            payload["full_name"] = full_name
            payload["phone"] = phone
            payload["date_of_birth"] = dob
            payload["gender"] = gender_code
            payload["address"] = self.address_input.text().strip() or None

        self.run_api_task(
            "book_for_patient",
            lambda: self.api_client.post(
                "/api/v1/reception/appointments/book", json=payload
            ),
            self._on_booking_success,
            controls=(self.btn_submit,),
            loading_text="Đang lưu lịch hẹn khám...",
        )

    def _on_booking_success(self, result: dict[str, Any]) -> None:
        appt_id = result.get("appointment_id", 0)
        patient_name = self.name_input.text().strip()
        self.feedback.show_message(
            "Đặt lịch thành công",
            f"Đã tạo thành công lịch hẹn #{appt_id} cho bệnh nhân {patient_name}!",
            severity="success",
        )
        self.appointment_booked.emit(result)
        self._clear_form()
