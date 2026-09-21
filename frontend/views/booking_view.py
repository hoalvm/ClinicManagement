"""Comprehensive 4-step wizard view for patient self-service appointment booking."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.core.i18n import get_i18n, t
from frontend.views.common import BaseApiView
from frontend.widgets.calendar_dialog import CalendarDialog
from frontend.widgets.empty_state import EmptyState
from frontend.widgets.page_header import PageHeader


class BookingView(BaseApiView):
    """Four-step appointment booking wizard: Specialty -> Doctor -> Date/Slot -> Confirm."""

    appointment_booked = Signal(int)
    back_requested = Signal()

    DAY_NAMES = {
        1: "Thứ Hai",
        2: "Thứ Ba",
        3: "Thứ Tư",
        4: "Thứ Năm",
        5: "Thứ Sáu",
        6: "Thứ Bảy",
        7: "Chủ Nhật",
    }

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self.setObjectName("bookingView")

        # Selection state
        self.selected_specialty: dict[str, Any] | None = None
        self.selected_doctor: dict[str, Any] | None = None
        self.selected_date: str = ""
        self.selected_slot: tuple[str, str] | None = None
        self.specialties_data: list[dict[str, Any]] = []
        self.doctors_data: list[dict[str, Any]] = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(28, 24, 28, 24)
        root_layout.setSpacing(14)

        # Header
        self.header = PageHeader(
            "Đặt lịch khám bệnh",
            "Chọn chuyên khoa, bác sĩ và khung giờ phù hợp để đặt lịch khám",
        )
        self.cancel_nav_btn = QPushButton("Quay lại danh sách")
        self.cancel_nav_btn.setObjectName("secondaryButton")
        self.cancel_nav_btn.clicked.connect(self.back_requested.emit)
        self.header.add_action(self.cancel_nav_btn)
        root_layout.addWidget(self.header)

        # Step indicator
        self.step_indicator = QLabel()
        self.step_indicator.setObjectName("sectionEyebrow")
        self.step_indicator.setStyleSheet("color: #0f766e; font-size: 13px; font-weight: 700;")
        root_layout.addWidget(self.step_indicator)

        root_layout.addWidget(self.feedback)
        root_layout.addWidget(self.loading)

        # Stacked layout for 4 steps
        self.step_container = QFrame()
        self.step_container.setObjectName("card")
        self.step_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.step_layout = QStackedLayout(self.step_container)
        root_layout.addWidget(self.step_container, 1)

        self._current_step_index = 0

        # Build individual step widgets
        self.step1_widget = self._build_step1_specialties()
        self.step2_widget = self._build_step2_doctors()
        self.step3_widget = self._build_step3_slots()
        self.step4_widget = self._build_step4_confirm()

        self.step_layout.addWidget(self.step1_widget)
        self.step_layout.addWidget(self.step2_widget)
        self.step_layout.addWidget(self.step3_widget)
        self.step_layout.addWidget(self.step4_widget)

        get_i18n().language_changed.connect(self.retranslate_ui)
        self._go_to_step(0)
        self.retranslate_ui()

    # --------------------------------------------------------------------------
    # Step 1: SpecialtyList
    # --------------------------------------------------------------------------
    def _build_step1_specialties(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        self.step1_title = QLabel(t("step_1_title"))
        self.step1_title.setObjectName("sectionTitle")
        layout.addWidget(self.step1_title)

        self.step1_subtitle = QLabel(t("step_1_subtitle"))
        self.step1_subtitle.setStyleSheet("color: #64748b; font-size: 13px;")
        layout.addWidget(self.step1_subtitle)

        # Combined Searchable Dropdown bar
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        self.spec_combo = QComboBox()
        self.spec_combo.setEditable(True)
        self.spec_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.spec_combo.setMinimumHeight(42)
        self.spec_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.spec_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                border: 1.5px solid #cbd5e1;
                border-radius: 8px;
                padding-left: 10px;
                padding-right: 36px;
                min-height: 40px;
                font-size: 13px;
                color: #0f172a;
            }
            QComboBox:focus {
                border-color: #0f766e;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 36px;
                border-left: 1.5px solid #cbd5e1;
                border-top-right-radius: 7px;
                border-bottom-right-radius: 7px;
                background: #f8fafc;
            }
            QComboBox::drop-down:hover {
                background: #e6fffa;
                border-left-color: #0f766e;
            }
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 7px solid #0f766e;
                margin-right: 2px;
            }
            QComboBox::down-arrow:hover {
                border-top: 7px solid #0d5f58;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #0f172a;
                border: 1.5px solid #0f766e;
                border-radius: 8px;
                selection-background-color: #ccfbf1;
                selection-color: #0f766e;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                background-color: #ffffff;
                color: #0f172a;
                padding: 8px 12px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView::item:hover,
            QComboBox QAbstractItemView::item:selected {
                background-color: #e6fffa;
                color: #0f766e;
                font-weight: 700;
            }
        """)

        self.spec_search_edit = self.spec_combo.lineEdit()
        if self.spec_search_edit:
            self.spec_search_edit.setPlaceholderText(t("spec_search_placeholder"))
            self.spec_search_edit.setClearButtonEnabled(True)
            self.spec_search_edit.textChanged.connect(self._filter_specialties)
            self.spec_search_edit.returnPressed.connect(self._on_combo_continue_clicked)

        completer = self.spec_combo.completer()
        if completer:
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.spec_combo.activated.connect(self._on_combo_activated)
        search_row.addWidget(self.spec_combo, 1)

        self.spec_continue_btn = QPushButton(t("spec_continue_btn"))
        self.spec_continue_btn.setObjectName("primaryButton")
        self.spec_continue_btn.setMinimumHeight(40)
        self.spec_continue_btn.setStyleSheet("font-weight: 600; padding: 0 18px;")
        self.spec_continue_btn.clicked.connect(self._on_combo_continue_clicked)
        search_row.addWidget(self.spec_continue_btn)

        layout.addLayout(search_row)

        self.step1_divider = QLabel(t("spec_divider_lbl"))
        self.step1_divider.setStyleSheet(
            "color: #475569; font-weight: 600; font-size: 13px; margin-top: 4px;"
        )
        layout.addWidget(self.step1_divider)

        # Scroll area for specialties grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.spec_grid_widget = QWidget()
        self.spec_grid_layout = QGridLayout(self.spec_grid_widget)
        self.spec_grid_layout.setSpacing(12)
        scroll.setWidget(self.spec_grid_widget)
        layout.addWidget(scroll, 1)

        return container

    def _populate_specialties_combo(self, specialties: list[dict[str, Any]]) -> None:
        self.spec_combo.blockSignals(True)
        self.spec_combo.clear()
        self.spec_combo.addItem(t("spec_combo_default"), None)
        for s in specialties:
            name = s.get("specialty_name", "")
            count = s.get("doctor_count", 0)
            doc_text = t("affiliated_doctors", count=count)
            self.spec_combo.addItem(f"🩺 {name} ({doc_text})", s)
        self.spec_combo.setCurrentIndex(0)
        self.spec_combo.blockSignals(False)

    def _on_combo_activated(self, index: int) -> None:
        if index <= 0:
            return
        spec = self.spec_combo.itemData(index)
        if spec and isinstance(spec, dict):
            self._select_specialty(spec)

    def _on_combo_continue_clicked(self) -> None:
        idx = self.spec_combo.currentIndex()
        if idx > 0:
            spec = self.spec_combo.itemData(idx)
            if spec and isinstance(spec, dict):
                self._select_specialty(spec)
                return

        # Fallback: check if text entered in lineEdit matches any specialty
        text = self.spec_search_edit.text().strip().lower() if self.spec_search_edit else ""
        if text:
            matches = [
                s
                for s in self.specialties_data
                if text in s.get("specialty_name", "").lower()
                or text in (s.get("description") or "").lower()
            ]
            if matches:
                self._select_specialty(matches[0])
                return

        self.feedback.show_message(
            t("no_specialty_found"),
            t("no_specialty_found_desc"),
            severity="warning",
        )

    def _render_specialties_grid(self, specialties: list[dict[str, Any]]) -> None:
        # Clear existing items
        while self.spec_grid_layout.count():
            item = self.spec_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not specialties:
            empty = EmptyState(t("no_specialty_found"), t("no_specialty_found_desc"))
            self.spec_grid_layout.addWidget(empty, 0, 0)
            return

        row, col = 0, 0
        cols_count = 2
        for spec in specialties:
            card = QFrame()
            card.setObjectName("card")
            card.setStyleSheet(
                "QFrame#card { background: #ffffff; border: 1px solid #e2e8f0; "
                "border-radius: 10px; padding: 14px; }"
                "QFrame#card:hover { border-color: #0f766e; background: #f0fdfa; }"
            )
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)

            name_lbl = QLabel(spec.get("specialty_name", ""))
            name_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a;")
            card_layout.addWidget(name_lbl)

            desc = spec.get("description") or "Chăm sóc và điều trị chuyên sâu theo tiêu chuẩn."
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet("color: #64748b; font-size: 13px;")
            desc_lbl.setWordWrap(True)
            card_layout.addWidget(desc_lbl)

            doc_count = spec.get("doctor_count", 0)
            count_lbl = QLabel(t("affiliated_doctors", count=doc_count))
            count_lbl.setStyleSheet("color: #0f766e; font-weight: 600; font-size: 12px;")
            card_layout.addWidget(count_lbl)

            # Button to select
            btn = QPushButton(t("select_this_specialty"))
            btn.setObjectName("secondaryButton")
            btn.clicked.connect(lambda _, s=spec: self._select_specialty(s))
            card_layout.addWidget(btn)

            self.spec_grid_layout.addWidget(card, row, col)
            col += 1
            if col >= cols_count:
                col = 0
                row += 1

    def _filter_specialties(self, query: str) -> None:
        q = query.strip().lower()
        if not q:
            self._render_specialties_grid(self.specialties_data)
            return
        filtered = [
            s
            for s in self.specialties_data
            if q in s.get("specialty_name", "").lower() or q in (s.get("description") or "").lower()
        ]
        self._render_specialties_grid(filtered)

    def _select_specialty(self, spec: dict[str, Any]) -> None:
        self.selected_specialty = spec
        self._go_to_step(1)
        if getattr(self, "_booking_mode", "by_date") == "by_date":
            self._load_doctors_for_date()
        else:
            self._load_doctors_for_specialty(spec.get("specialty_id"))

    # --------------------------------------------------------------------------
    # Step 2: DoctorList (with 2 Booking Modes: By Date vs By Doctor)
    # --------------------------------------------------------------------------
    def _build_step2_doctors(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Top navigation
        top_nav = QHBoxLayout()
        self.step2_back_btn = QPushButton("← Đổi chuyên khoa")
        self.step2_back_btn.setObjectName("secondaryButton")
        self.step2_back_btn.clicked.connect(lambda: self._go_to_step(0))
        top_nav.addWidget(self.step2_back_btn)

        self.step2_title = QLabel("Bước 2: Chọn lịch khám")
        self.step2_title.setObjectName("sectionTitle")
        top_nav.addWidget(self.step2_title, 1)
        layout.addLayout(top_nav)

        # Mode selection bar
        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        self.mode_label = QLabel(t("lbl_booking_mode"))
        self.mode_label.setStyleSheet("font-weight: 700; color: #334155; font-size: 13px;")
        mode_row.addWidget(self.mode_label)

        self.mode_by_date_btn = QPushButton(t("mode_by_date"))
        self.mode_by_date_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_by_date_btn.clicked.connect(lambda: self._set_booking_mode("by_date"))
        mode_row.addWidget(self.mode_by_date_btn)

        self.mode_by_doctor_btn = QPushButton(t("mode_by_doctor"))
        self.mode_by_doctor_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_by_doctor_btn.clicked.connect(lambda: self._set_booking_mode("by_doctor"))
        mode_row.addWidget(self.mode_by_doctor_btn)
        mode_row.addStretch(1)
        layout.addLayout(mode_row)

        # Stacked layout for the 2 modes
        self.step2_stack = QStackedLayout()

        # -----------------------------
        # Page 0: Mode A - By Date
        # -----------------------------
        self.by_date_widget = QWidget()
        by_date_layout = QVBoxLayout(self.by_date_widget)
        by_date_layout.setContentsMargins(0, 4, 0, 0)
        by_date_layout.setSpacing(10)

        # Quick date chips
        s2_quick_row = QHBoxLayout()
        s2_quick_row.setSpacing(6)
        self.s2_quick_date_lbl = QLabel(t("quick_select_date", default="Chọn nhanh ngày:"))
        self.s2_quick_date_lbl.setObjectName("fieldLabel")
        s2_quick_row.addWidget(self.s2_quick_date_lbl)

        self._s2_quick_chip_buttons: list[tuple[QPushButton, QDate]] = []
        today = QDate.currentDate()
        for offset in range(6):
            target_d = today.addDays(offset)
            chip_btn = QPushButton()
            chip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            chip_btn.setStyleSheet(
                "QPushButton { background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; "
                "border-radius: 14px; padding: 4px 10px; font-size: 12px; font-weight: 500; }"
                "QPushButton:hover { background: #e2e8f0; border-color: #94a3b8; }"
                'QPushButton[active="true"] { background: #0f766e; color: #ffffff; border-color: #0f766e; font-weight: 700; }'
            )
            chip_btn.clicked.connect(lambda _, d=target_d: self._select_s2_quick_date(d))
            self._s2_quick_chip_buttons.append((chip_btn, target_d))
            s2_quick_row.addWidget(chip_btn)
        s2_quick_row.addStretch(1)
        by_date_layout.addLayout(s2_quick_row)
        self._update_s2_quick_chip_labels()

        # Date picker row
        s2_date_row = QHBoxLayout()
        self.s2_date_lbl = QLabel(t("field_appointment_date", default="Chọn ngày khám:"))
        self.s2_date_lbl.setObjectName("fieldLabel")
        s2_date_row.addWidget(self.s2_date_lbl)

        self.step2_date_edit = QDateEdit()
        self.step2_date_edit.setCalendarPopup(True)
        self.step2_date_edit.setDate(QDate.currentDate().addDays(1))
        self.step2_date_edit.setMinimumDate(QDate.currentDate())
        self.step2_date_edit.setMaximumDate(QDate.currentDate().addDays(60))
        self.step2_date_edit.dateChanged.connect(self._load_doctors_for_date)
        s2_date_row.addWidget(self.step2_date_edit)

        self.s2_open_cal_btn = QPushButton(t("btn_open_calendar", default="📅 Mở lịch"))
        self.s2_open_cal_btn.setObjectName("secondaryButton")
        self.s2_open_cal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.s2_open_cal_btn.clicked.connect(self._open_s2_calendar_dialog)
        s2_date_row.addWidget(self.s2_open_cal_btn)

        self.step2_day_of_week_lbl = QLabel()
        self.step2_day_of_week_lbl.setStyleSheet("font-weight: 600; color: #0f766e;")
        s2_date_row.addWidget(self.step2_day_of_week_lbl)
        s2_date_row.addStretch(1)
        by_date_layout.addLayout(s2_date_row)

        self.by_date_doc_header = QLabel(t("lbl_choose_doctor_on_date"))
        self.by_date_doc_header.setStyleSheet(
            "color: #475569; font-weight: 600; font-size: 13px; margin-top: 4px;"
        )
        by_date_layout.addWidget(self.by_date_doc_header)

        # Scroll area for doctors on date
        s2_scroll = QScrollArea()
        s2_scroll.setWidgetResizable(True)
        s2_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.by_date_doc_widget = QWidget()
        self.by_date_doc_layout = QVBoxLayout(self.by_date_doc_widget)
        self.by_date_doc_layout.setSpacing(10)
        s2_scroll.setWidget(self.by_date_doc_widget)
        by_date_layout.addWidget(s2_scroll, 1)

        # -----------------------------
        # Page 1: Mode B - By Doctor
        # -----------------------------
        self.by_doctor_widget = QWidget()
        by_doc_layout = QVBoxLayout(self.by_doctor_widget)
        by_doc_layout.setContentsMargins(0, 4, 0, 0)
        by_doc_layout.setSpacing(10)

        self.by_doctor_header = QLabel(t("lbl_all_doctors_in_spec"))
        self.by_doctor_header.setStyleSheet(
            "color: #475569; font-weight: 600; font-size: 13px; margin-top: 4px;"
        )
        by_doc_layout.addWidget(self.by_doctor_header)

        doc_scroll = QScrollArea()
        doc_scroll.setWidgetResizable(True)
        doc_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.doc_grid_widget = QWidget()
        self.doc_grid_layout = QVBoxLayout(self.doc_grid_widget)
        self.doc_grid_layout.setSpacing(10)
        doc_scroll.setWidget(self.doc_grid_widget)
        by_doc_layout.addWidget(doc_scroll, 1)

        self.step2_stack.addWidget(self.by_date_widget)
        self.step2_stack.addWidget(self.by_doctor_widget)
        layout.addLayout(self.step2_stack, 1)

        self._booking_mode = "by_date"
        self._update_mode_buttons()

        return container

    def _set_booking_mode(self, mode: str) -> None:
        self._booking_mode = mode
        self._update_mode_buttons()
        if mode == "by_date":
            self.step2_stack.setCurrentIndex(0)
            self._load_doctors_for_date()
        else:
            self.step2_stack.setCurrentIndex(1)
            if self.selected_specialty:
                self._load_doctors_for_specialty(self.selected_specialty.get("specialty_id"))
        self._update_step_indicator()

    def _update_mode_buttons(self) -> None:
        active_style = (
            "QPushButton { background: #0f766e; color: #ffffff; border: 1.5px solid #0f766e; "
            "border-radius: 8px; padding: 6px 14px; font-weight: 700; }"
        )
        inactive_style = (
            "QPushButton { background: #ffffff; color: #475569; border: 1.5px solid #cbd5e1; "
            "border-radius: 8px; padding: 6px 14px; font-weight: 600; }"
            "QPushButton:hover { background: #f8fafc; border-color: #94a3b8; }"
        )
        if getattr(self, "_booking_mode", "by_date") == "by_date":
            self.mode_by_date_btn.setStyleSheet(active_style)
            self.mode_by_doctor_btn.setStyleSheet(inactive_style)
        else:
            self.mode_by_date_btn.setStyleSheet(inactive_style)
            self.mode_by_doctor_btn.setStyleSheet(active_style)

    def _open_s2_calendar_dialog(self) -> None:
        dlg = CalendarDialog(
            current_date=self.step2_date_edit.date(),
            min_date=QDate.currentDate(),
            max_date=QDate.currentDate().addDays(60),
            parent=self,
        )
        if dlg.exec():
            selected = dlg.selected_date()
            self.step2_date_edit.setDate(selected)
            self._highlight_s2_quick_chips(selected)

    def _select_s2_quick_date(self, target_date: QDate) -> None:
        self.step2_date_edit.setDate(target_date)
        self._highlight_s2_quick_chips(target_date)

    def _highlight_s2_quick_chips(self, current_date: QDate) -> None:
        if not hasattr(self, "_s2_quick_chip_buttons"):
            return
        for btn, d in self._s2_quick_chip_buttons:
            is_active = d == current_date
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _update_s2_quick_chip_labels(self) -> None:
        if not hasattr(self, "_s2_quick_chip_buttons"):
            return
        for idx, (btn, target_d) in enumerate(self._s2_quick_chip_buttons):
            if idx == 0:
                text = f"{t('chip_today')} ({target_d.toString('dd/MM')})"
            elif idx == 1:
                text = f"{t('chip_tomorrow')} ({target_d.toString('dd/MM')})"
            else:
                day_name = t(f"day_{target_d.dayOfWeek()}")
                text = f"{day_name} ({target_d.toString('dd/MM')})"
            btn.setText(text)
        if hasattr(self, "step2_date_edit"):
            self._highlight_s2_quick_chips(self.step2_date_edit.date())

    def _load_doctors_for_date(self) -> None:
        if not self.selected_specialty:
            return
        spec_id = self.selected_specialty.get("specialty_id")
        qdate = self.step2_date_edit.date()
        date_str = qdate.toString(Qt.DateFormat.ISODate)
        day_num = qdate.dayOfWeek()
        self.step2_day_of_week_lbl.setText(f"({t(f'day_{day_num}')})")
        self._highlight_s2_quick_chips(qdate)

        spec_name = self.selected_specialty.get("specialty_name", "")
        self.step2_title.setText(
            f"{t('step_2_title_by_date')} ({spec_name})" if spec_name else t("step_2_title_by_date")
        )
        self.by_date_doc_header.setText(
            f"{t('lbl_choose_doctor_on_date')} ({qdate.toString('dd/MM/yyyy')} - {t(f'day_{day_num}')})"
        )

        self.run_api_task(
            "load_doctors_by_date",
            lambda: self.api_client.get(
                "/api/v1/catalog/doctors",
                params={"specialty_id": spec_id, "appointment_date": date_str},
            ),
            self._on_doctors_by_date_loaded,
            loading_text="Đang tìm bác sĩ có lịch trực vào ngày này…",
        )

    def _on_doctors_by_date_loaded(self, result: Any) -> None:
        doctors = result if isinstance(result, list) else []
        while self.by_date_doc_layout.count():
            item = self.by_date_doc_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not doctors:
            empty = EmptyState(
                t("no_doctor_on_date"),
                "Vui lòng chọn ngày khác trên thanh chọn ngày.",
            )
            self.by_date_doc_layout.addWidget(empty)
            return

        date_str = self.step2_date_edit.date().toString(Qt.DateFormat.ISODate)
        for doc in doctors:
            card = QFrame()
            card.setObjectName("card")
            card.setStyleSheet(
                "QFrame#card { background: #ffffff; border: 1px solid #e2e8f0; "
                "border-radius: 10px; padding: 14px; }"
                "QFrame#card:hover { border-color: #0f766e; background: #f0fdfa; }"
            )
            card_layout = QHBoxLayout(card)
            card_layout.setSpacing(14)

            avatar = QLabel("👨‍⚕️")
            avatar.setStyleSheet("font-size: 32px; padding: 6px;")
            card_layout.addWidget(avatar)

            info_layout = QVBoxLayout()
            info_layout.setSpacing(4)
            name_lbl = QLabel(f"Bác sĩ: {doc.get('full_name', '')}")
            name_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a;")
            info_layout.addWidget(name_lbl)

            spec_lbl = QLabel(f"Chuyên khoa: {doc.get('specialty_name', '')}")
            spec_lbl.setStyleSheet("color: #0f766e; font-weight: 600; font-size: 13px;")
            info_layout.addWidget(spec_lbl)

            clinic_info = doc.get("clinic_name") or "Phòng khám chính"
            clinic_addr = doc.get("clinic_address") or ""
            clinic_lbl = QLabel(f"🏥 {clinic_info} - {clinic_addr}")
            clinic_lbl.setStyleSheet("color: #64748b; font-size: 12px;")
            info_layout.addWidget(clinic_lbl)

            card_layout.addLayout(info_layout, 1)

            btn = QPushButton(t("choose_this_doctor_and_slot"))
            btn.setObjectName("primaryButton")
            btn.clicked.connect(lambda _, d=doc, ds=date_str: self._select_doctor_and_date(d, ds))
            card_layout.addWidget(btn)

            self.by_date_doc_layout.addWidget(card)

        self.by_date_doc_layout.addStretch(1)

    def _select_doctor_and_date(self, doc: dict[str, Any], date_str: str) -> None:
        self.selected_doctor = doc
        self.selected_date = date_str
        self.selected_slot = None
        qdate = QDate.fromString(date_str, Qt.DateFormat.ISODate)
        self.slot_date_edit.setDate(qdate)
        self._go_to_step(2)
        self._load_doctor_schedules_info(doc.get("doctor_id"))
        self._load_available_slots()

    def _load_doctors_for_specialty(self, specialty_id: int | None) -> None:
        spec_name = self.selected_specialty.get("specialty_name", "") if self.selected_specialty else ""
        self.step2_title.setText(
            f"{t('step_2_title_by_doctor')} ({spec_name})" if spec_name else t("step_2_title_by_doctor")
        )
        self.run_api_task(
            "load_doctors",
            lambda: self.api_client.get(
                "/api/v1/catalog/doctors", params={"specialty_id": specialty_id}
            ),
            self._on_doctors_loaded,
            loading_text="Đang tải danh sách bác sĩ…",
        )

    def _on_doctors_loaded(self, result: Any) -> None:
        self.doctors_data = result if isinstance(result, list) else []
        while self.doc_grid_layout.count():
            item = self.doc_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.doctors_data:
            empty = EmptyState("Không có bác sĩ nào", "Chuyên khoa này hiện chưa có bác sĩ trực.")
            self.doc_grid_layout.addWidget(empty)
            return

        for doc in self.doctors_data:
            card = QFrame()
            card.setObjectName("card")
            card.setStyleSheet(
                "QFrame#card { background: #ffffff; border: 1px solid #e2e8f0; "
                "border-radius: 10px; padding: 14px; }"
                "QFrame#card:hover { border-color: #0f766e; background: #f0fdfa; }"
            )
            card_layout = QHBoxLayout(card)
            card_layout.setSpacing(14)

            avatar = QLabel("👨‍⚕️")
            avatar.setStyleSheet("font-size: 32px; padding: 6px;")
            card_layout.addWidget(avatar)

            info_layout = QVBoxLayout()
            info_layout.setSpacing(4)
            name_lbl = QLabel(f"Bác sĩ: {doc.get('full_name', '')}")
            name_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a;")
            info_layout.addWidget(name_lbl)

            spec_lbl = QLabel(f"Chuyên khoa: {doc.get('specialty_name', '')}")
            spec_lbl.setStyleSheet("color: #0f766e; font-weight: 600; font-size: 13px;")
            info_layout.addWidget(spec_lbl)

            clinic_info = doc.get("clinic_name") or "Phòng khám chính"
            clinic_addr = doc.get("clinic_address") or ""
            clinic_lbl = QLabel(f"🏥 {clinic_info} - {clinic_addr}")
            clinic_lbl.setStyleSheet("color: #64748b; font-size: 12px;")
            info_layout.addWidget(clinic_lbl)

            card_layout.addLayout(info_layout, 1)

            btn = QPushButton(t("select_this_specialty", default="Chọn lịch khám →"))
            btn.setObjectName("primaryButton")
            btn.clicked.connect(lambda _, d=doc: self._select_doctor_only(d))
            card_layout.addWidget(btn)

            self.doc_grid_layout.addWidget(card)

        self.doc_grid_layout.addStretch(1)

    def _select_doctor_only(self, doc: dict[str, Any]) -> None:
        self.selected_doctor = doc
        self.selected_slot = None
        self._go_to_step(2)
        self._load_doctor_schedules_info(doc.get("doctor_id"))
        if not self.slot_date_edit.date().isValid() or self.slot_date_edit.date() < QDate.currentDate():
            self.slot_date_edit.setDate(QDate.currentDate().addDays(1))
        self._load_available_slots()

    def _load_doctor_schedules_info(self, doctor_id: int | None) -> None:
        if not doctor_id:
            if hasattr(self, "doc_schedule_lbl"):
                self.doc_schedule_lbl.hide()
            return

        def _fetch() -> Any:
            return self.api_client.get(f"/api/v1/catalog/doctors/{doctor_id}/schedules")

        def _on_done(result: Any) -> None:
            if isinstance(result, list) and result:
                parts = []
                for item in result:
                    d = item.get("day_of_week")
                    day_name = t(f"day_{d}") if d else ""
                    st = str(item.get("start_time", ""))[:5]
                    et = str(item.get("end_time", ""))[:5]
                    parts.append(f"{day_name} ({st} - {et})")
                schedule_text = ", ".join(parts)
                self.doc_schedule_lbl.setText(f"🗓 <b>{t('doctor_schedule_info')}</b> {schedule_text}")
                self.doc_schedule_lbl.show()
            else:
                if hasattr(self, "doc_schedule_lbl"):
                    self.doc_schedule_lbl.hide()

        self.run_api_task(
            "load_doctor_schedules",
            _fetch,
            _on_done,
            loading_text="",
        )

    # --------------------------------------------------------------------------
    # Step 3: DoctorSchedule & Slot Picker
    # --------------------------------------------------------------------------
    def _build_step3_slots(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        top_nav = QHBoxLayout()
        self.step3_back_btn = QPushButton("← Đổi bác sĩ")
        self.step3_back_btn.setObjectName("secondaryButton")
        self.step3_back_btn.clicked.connect(lambda: self._go_to_step(1))
        top_nav.addWidget(self.step3_back_btn)

        self.step3_title = QLabel("Bước 3: Chọn ngày và khung giờ khám")
        self.step3_title.setObjectName("sectionTitle")
        top_nav.addWidget(self.step3_title, 1)
        layout.addLayout(top_nav)

        # Doctor banner
        self.doc_banner = QFrame()
        self.doc_banner.setObjectName("card")
        self.doc_banner.setStyleSheet(
            "QFrame#card { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px; }"
        )
        banner_layout = QVBoxLayout(self.doc_banner)
        banner_layout.setSpacing(4)
        self.doc_banner_lbl = QLabel()
        banner_layout.addWidget(self.doc_banner_lbl)

        self.doc_schedule_lbl = QLabel()
        self.doc_schedule_lbl.setStyleSheet(
            "color: #0f766e; font-size: 12px; font-weight: 500;"
        )
        self.doc_schedule_lbl.setWordWrap(True)
        banner_layout.addWidget(self.doc_schedule_lbl)
        self.doc_schedule_lbl.hide()
        layout.addWidget(self.doc_banner)

        # Warning banner for anti-spam/active specialty
        self.specialty_warning_frame = QFrame()
        self.specialty_warning_frame.setStyleSheet(
            "background: #fffbeb; border: 1.5px solid #fde68a; border-radius: 8px; padding: 10px;"
        )
        warn_layout = QHBoxLayout(self.specialty_warning_frame)
        warn_layout.setContentsMargins(10, 8, 10, 8)
        self.specialty_warning_lbl = QLabel()
        self.specialty_warning_lbl.setStyleSheet(
            "color: #b45309; font-size: 13px; font-weight: 600;"
        )
        self.specialty_warning_lbl.setWordWrap(True)
        warn_layout.addWidget(self.specialty_warning_lbl)
        self.specialty_warning_frame.hide()
        layout.addWidget(self.specialty_warning_frame)

        # Quick date chips row
        quick_row = QHBoxLayout()
        quick_row.setSpacing(6)
        self.quick_date_lbl = QLabel(t("quick_select_date", default="Chọn nhanh ngày:"))
        self.quick_date_lbl.setObjectName("fieldLabel")
        quick_row.addWidget(self.quick_date_lbl)

        self._quick_chip_buttons: list[tuple[QPushButton, QDate]] = []
        today = QDate.currentDate()
        for offset in range(6):
            target_d = today.addDays(offset)
            chip_btn = QPushButton()
            chip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            chip_btn.setStyleSheet(
                "QPushButton { background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; "
                "border-radius: 14px; padding: 4px 10px; font-size: 12px; font-weight: 500; }"
                "QPushButton:hover { background: #e2e8f0; border-color: #94a3b8; }"
                'QPushButton[active="true"] { background: #0f766e; color: #ffffff; border-color: #0f766e; font-weight: 700; }'
            )
            chip_btn.clicked.connect(lambda _, d=target_d: self._select_quick_date(d))
            self._quick_chip_buttons.append((chip_btn, target_d))
            quick_row.addWidget(chip_btn)
        quick_row.addStretch(1)
        layout.addLayout(quick_row)
        self._update_quick_chip_labels()

        # Date picker row
        date_row = QHBoxLayout()
        self.date_lbl = QLabel(t("field_appointment_date", default="Chọn ngày khám:"))
        self.date_lbl.setObjectName("fieldLabel")
        date_row.addWidget(self.date_lbl)

        self.slot_date_edit = QDateEdit()
        self.slot_date_edit.setCalendarPopup(True)
        self.slot_date_edit.setDate(QDate.currentDate().addDays(1))
        self.slot_date_edit.setMinimumDate(QDate.currentDate())
        self.slot_date_edit.setMaximumDate(QDate.currentDate().addDays(60))
        self.slot_date_edit.dateChanged.connect(self._load_available_slots)
        date_row.addWidget(self.slot_date_edit)

        self.open_cal_btn = QPushButton(t("btn_open_calendar", default="📅 Mở lịch"))
        self.open_cal_btn.setObjectName("secondaryButton")
        self.open_cal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_cal_btn.setToolTip("Nhấp để mở bảng lịch chọn ngày trực quan")
        self.open_cal_btn.clicked.connect(self._open_calendar_dialog)
        date_row.addWidget(self.open_cal_btn)

        self.day_of_week_lbl = QLabel()
        self.day_of_week_lbl.setStyleSheet("font-weight: 600; color: #0f766e;")
        date_row.addWidget(self.day_of_week_lbl)
        date_row.addStretch(1)
        layout.addLayout(date_row)

        # Slots container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.slots_widget = QWidget()
        self.slots_layout = QGridLayout(self.slots_widget)
        self.slots_layout.setSpacing(10)
        scroll.setWidget(self.slots_widget)
        layout.addWidget(scroll, 1)

        # Bottom nav to step 4
        bottom_row = QHBoxLayout()
        self.slot_selected_lbl = QLabel("Chưa chọn khung giờ khám")
        self.slot_selected_lbl.setStyleSheet("font-weight: 600; color: #334155;")
        bottom_row.addWidget(self.slot_selected_lbl, 1)

        self.to_confirm_btn = QPushButton("Tiếp tục: Xác nhận đặt lịch →")
        self.to_confirm_btn.setObjectName("primaryButton")
        self.to_confirm_btn.setEnabled(False)
        self.to_confirm_btn.clicked.connect(lambda: self._go_to_step(3))
        bottom_row.addWidget(self.to_confirm_btn)
        layout.addLayout(bottom_row)

        return container

    def _open_calendar_dialog(self) -> None:
        dlg = CalendarDialog(
            current_date=self.slot_date_edit.date(),
            min_date=QDate.currentDate(),
            max_date=QDate.currentDate().addDays(60),
            parent=self,
        )
        if dlg.exec():
            selected = dlg.selected_date()
            self.slot_date_edit.setDate(selected)
            self._highlight_quick_chips(selected)

    def _select_quick_date(self, target_date: QDate) -> None:
        self.slot_date_edit.setDate(target_date)
        self._highlight_quick_chips(target_date)

    def _update_quick_chip_labels(self) -> None:
        if not hasattr(self, "_quick_chip_buttons"):
            return
        for idx, (btn, target_d) in enumerate(self._quick_chip_buttons):
            if idx == 0:
                text = f"{t('chip_today')} ({target_d.toString('dd/MM')})"
            elif idx == 1:
                text = f"{t('chip_tomorrow')} ({target_d.toString('dd/MM')})"
            else:
                day_name = t(f"day_{target_d.dayOfWeek()}")
                text = f"{day_name} ({target_d.toString('dd/MM')})"
            btn.setText(text)
        if hasattr(self, "slot_date_edit"):
            self._highlight_quick_chips(self.slot_date_edit.date())

    def _highlight_quick_chips(self, current_date: QDate) -> None:
        if not hasattr(self, "_quick_chip_buttons"):
            return
        for btn, d in self._quick_chip_buttons:
            is_active = d == current_date
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _load_available_slots(self) -> None:
        if not self.selected_doctor:
            return

        doc_name = self.selected_doctor.get("full_name", "")
        spec_name = self.selected_doctor.get("specialty_name", "")
        clinic_name = self.selected_doctor.get("clinic_name", "")
        self.doc_banner_lbl.setText(
            f"<b>Bác sĩ:</b> {doc_name} | <b>Chuyên khoa:</b> {spec_name} | <b>Cơ sở:</b> {clinic_name}"
        )

        qdate = self.slot_date_edit.date()
        date_str = qdate.toString(Qt.DateFormat.ISODate)
        self.selected_date = date_str
        day_num = qdate.dayOfWeek()  # Qt: 1=Mon .. 7=Sun
        self.day_of_week_lbl.setText(f"({t(f'day_{day_num}')})")
        self._highlight_quick_chips(qdate)

        self.selected_slot = None
        self.slot_selected_lbl.setText("Chưa chọn khung giờ khám")
        self.to_confirm_btn.setEnabled(False)

        doctor_id = self.selected_doctor.get("doctor_id")
        self.run_api_task(
            "load_slots",
            lambda: self.api_client.get(
                f"/api/v1/catalog/doctors/{doctor_id}/available-slots",
                params={"appointment_date": date_str},
            ),
            self._on_slots_loaded,
            loading_text="Đang kiểm tra lịch làm việc & giờ còn trống…",
        )

    def _on_slots_loaded(self, result: Any) -> None:
        while self.slots_layout.count():
            item = self.slots_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not isinstance(result, dict):
            return

        has_schedule = result.get("has_schedule", False)
        slots = result.get("slots", [])

        # Check if any slot is blocked by anti-spam rule
        spam_reason = next(
            (
                s.get("reason")
                for s in slots
                if s.get("reason")
                and (
                    "chuyên khoa này" in s.get("reason", "")
                    or "phòng khám này trong ngày" in s.get("reason", "")
                )
            ),
            None,
        )
        if spam_reason and hasattr(self, "specialty_warning_frame"):
            self.specialty_warning_lbl.setText(f"⚠️ {spam_reason}")
            self.specialty_warning_frame.show()
        elif hasattr(self, "specialty_warning_frame"):
            self.specialty_warning_frame.hide()

        if not has_schedule:
            empty = EmptyState(
                "Bác sĩ không có lịch làm việc", "Vui lòng chọn ngày khác để tiếp tục."
            )
            self.slots_layout.addWidget(empty, 0, 0)
            return

        if not slots:
            empty = EmptyState(
                "Không có khung giờ khám", "Tất cả các ca khám trong ngày đã kết thúc."
            )
            self.slots_layout.addWidget(empty, 0, 0)
            return

        row, col = 0, 0
        cols_count = 4
        self._slot_buttons: list[tuple[QPushButton, str, str]] = []

        for s in slots:
            start_t = s["start_time"]
            end_t = s["end_time"]
            is_avail = s.get("is_available", False)
            reason = s.get("reason") or "Không khả dụng"

            btn = QPushButton(f"{start_t} - {end_t}")
            btn.setMinimumHeight(44)
            if is_avail:
                btn.setObjectName("secondaryButton")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(
                    "QPushButton { background: #ffffff; border: 1.5px solid #0f766e; color: #0f766e; font-weight: 700; border-radius: 8px; }"
                    "QPushButton:hover { background: #0f766e; color: #ffffff; }"
                )
                btn.clicked.connect(
                    lambda _, st=start_t, et=end_t, b=btn: self._select_slot(st, et, b)
                )
                self._slot_buttons.append((btn, start_t, end_t))
            else:
                btn.setEnabled(False)
                btn.setToolTip(reason)
                btn.setStyleSheet(
                    "QPushButton:disabled { background: #f1f5f9; border: 1px solid #e2e8f0; color: #94a3b8; border-radius: 8px; }"
                )

            self.slots_layout.addWidget(btn, row, col)
            col += 1
            if col >= cols_count:
                col = 0
                row += 1

    def _select_slot(self, start_t: str, end_t: str, active_btn: QPushButton) -> None:
        self.selected_slot = (start_t, end_t)
        self.slot_selected_lbl.setText(f"✓ Đã chọn: {start_t} - {end_t}")
        self.to_confirm_btn.setEnabled(True)

        for btn, _, _ in self._slot_buttons:
            btn.setStyleSheet(
                "QPushButton { background: #ffffff; border: 1.5px solid #0f766e; color: #0f766e; font-weight: 700; border-radius: 8px; }"
                "QPushButton:hover { background: #0f766e; color: #ffffff; }"
            )
        active_btn.setStyleSheet(
            "QPushButton { background: #0f766e; border: 2px solid #0d5f58; color: #ffffff; font-weight: 700; border-radius: 8px; }"
        )

    # --------------------------------------------------------------------------
    # Step 4: AppointmentBooking Confirmation
    # --------------------------------------------------------------------------
    def _build_step4_confirm(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        top_nav = QHBoxLayout()
        self.step4_back_btn = QPushButton("← Chọn lại giờ khám")
        self.step4_back_btn.setObjectName("secondaryButton")
        self.step4_back_btn.clicked.connect(lambda: self._go_to_step(2))
        top_nav.addWidget(self.step4_back_btn)

        self.step4_title = QLabel("Bước 4: Xác nhận thông tin đặt lịch")
        self.step4_title.setObjectName("sectionTitle")
        top_nav.addWidget(self.step4_title, 1)
        layout.addLayout(top_nav)

        # Summary review card
        self.confirm_card = QFrame()
        self.confirm_card.setObjectName("card")
        self.confirm_card.setStyleSheet(
            "QFrame#card { background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 10px; padding: 18px; }"
        )
        self.confirm_card_layout = QVBoxLayout(self.confirm_card)
        self.confirm_card_layout.setSpacing(8)
        self.summary_details_lbl = QLabel()
        self.summary_details_lbl.setStyleSheet("font-size: 14px; line-height: 1.6; color: #1e293b;")
        self.confirm_card_layout.addWidget(self.summary_details_lbl)
        layout.addWidget(self.confirm_card)

        # Reason text edit
        lbl_reason = QLabel("Lý do khám bệnh / Triệu chứng lâm sàng:")
        lbl_reason.setObjectName("fieldLabel")
        layout.addWidget(lbl_reason)

        self.booking_reason_edit = QTextEdit()
        self.booking_reason_edit.setPlaceholderText(
            "Mô tả cụ thể triệu chứng, tình trạng sức khỏe hoặc yêu cầu khám bệnh..."
        )
        self.booking_reason_edit.setMaximumHeight(100)
        layout.addWidget(self.booking_reason_edit)

        # Final action buttons
        actions_row = QHBoxLayout()
        actions_row.addStretch(1)

        self.submit_booking_btn = QPushButton("✓ Xác nhận đặt lịch khám")
        self.submit_booking_btn.setObjectName("primaryButton")
        self.submit_booking_btn.setMinimumHeight(44)
        self.submit_booking_btn.setStyleSheet(
            "min-width: 220px; font-size: 15px; font-weight: 700;"
        )
        self.submit_booking_btn.clicked.connect(self._submit_booking)
        actions_row.addWidget(self.submit_booking_btn)

        layout.addLayout(actions_row)
        layout.addStretch(1)

        return container

    def _render_confirmation_summary(self) -> None:
        if not self.selected_doctor or not self.selected_slot:
            return

        doc_name = self.selected_doctor.get("full_name", "")
        spec_name = self.selected_doctor.get("specialty_name", "")
        clinic_name = self.selected_doctor.get("clinic_name", "Phòng khám chính")
        clinic_addr = self.selected_doctor.get("clinic_address", "")
        start_t, end_t = self.selected_slot

        html = f"""
        <h3 style="margin-top:0; color:#0f766e;">{t("summary_title")}</h3>
        <p><b>{t("summary_specialty")}:</b> {spec_name}</p>
        <p><b>{t("summary_doctor")}:</b> {doc_name}</p>
        <p><b>{t("summary_location")}:</b> {clinic_name} ({clinic_addr})</p>
        <p><b>{t("summary_date")}:</b> <span style="color:#0f766e; font-weight:bold;">{self.selected_date}</span></p>
        <p><b>{t("summary_time")}:</b> <span style="color:#0f766e; font-weight:bold;">{start_t} - {end_t}</span></p>
        <p style="color:#64748b; font-size:12px;"><i>{t("summary_note")}</i></p>
        """
        self.summary_details_lbl.setText(html)

    def _submit_booking(self) -> None:
        if not self.selected_doctor or not self.selected_slot:
            return

        start_t, end_t = self.selected_slot
        payload = {
            "doctor_id": self.selected_doctor.get("doctor_id"),
            "appointment_date": self.selected_date,
            "start_time": start_t,
            "end_time": end_t,
            "reason": self.booking_reason_edit.toPlainText().strip() or None,
        }

        self.run_api_task(
            "submit_booking",
            lambda: self.api_client.post("/api/v1/appointments", json=payload),
            self._on_booking_success,
            controls=(self.submit_booking_btn, self.step4_back_btn),
            loading_text="Đang tạo lịch khám và kiểm tra lịch trùng…",
        )

    def _on_booking_success(self, result: Any) -> None:
        self.feedback.show_message(
            "Đặt lịch khám thành công!",
            "Lịch khám của bạn đã được ghi nhận vào hệ thống.",
            severity="success",
        )
        appointment_id = result.get("appointment_id", 0) if isinstance(result, dict) else 0
        self.appointment_booked.emit(appointment_id)

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    # Wizard Navigation
    # --------------------------------------------------------------------------
    def _go_to_step(self, step_index: int) -> None:
        self._current_step_index = step_index
        self._update_step_indicator()
        self.step_layout.setCurrentIndex(step_index)

        if step_index == 0:
            if not self.specialties_data:
                self.run_api_task(
                    "load_specialties",
                    lambda: self.api_client.get("/api/v1/catalog/specialties"),
                    self._on_specialties_loaded,
                    loading_text="Đang tải danh mục chuyên khoa…",
                )
        elif step_index == 1:
            spec_name = (
                self.selected_specialty.get("specialty_name", "") if self.selected_specialty else ""
            )
            title_key = (
                "step_2_title_by_date"
                if getattr(self, "_booking_mode", "by_date") == "by_date"
                else "step_2_title_by_doctor"
            )
            self.step2_title.setText(f"{t(title_key)} ({spec_name})" if spec_name else t(title_key))
        elif step_index == 3:
            self._render_confirmation_summary()

    def _update_step_indicator(self) -> None:
        if self._current_step_index == 1:
            mode_text = (
                t("mode_by_date")
                if getattr(self, "_booking_mode", "by_date") == "by_date"
                else t("mode_by_doctor")
            )
            self.step_indicator.setText(f"Bước 2/4: {mode_text}")
        else:
            step_keys = [
                "step_1_indicator",
                "step_2_indicator",
                "step_3_indicator",
                "step_4_indicator",
            ]
            self.step_indicator.setText(t(step_keys[self._current_step_index]))

    def retranslate_ui(self) -> None:
        """Dynamically update all visible text in BookingView."""
        self.header.title_label.setText(t("booking_header_title"))
        self.header.subtitle_label.setText(t("booking_header_subtitle"))
        self.cancel_nav_btn.setText(t("back_to_appointments"))
        self._update_step_indicator()

        # Step 1
        self.step1_title.setText(t("step_1_title"))
        self.step1_subtitle.setText(t("step_1_subtitle"))
        if self.spec_search_edit:
            self.spec_search_edit.setPlaceholderText(t("spec_search_placeholder"))
        self.spec_continue_btn.setText(t("spec_continue_btn"))
        self.step1_divider.setText(t("spec_divider_lbl"))
        if self.specialties_data:
            self._populate_specialties_combo(self.specialties_data)
            self._render_specialties_grid(self.specialties_data)

        # Step 2
        self.step2_back_btn.setText(t("step_2_back"))
        spec_name = (
            self.selected_specialty.get("specialty_name", "") if self.selected_specialty else ""
        )
        title_key = (
            "step_2_title_by_date"
            if getattr(self, "_booking_mode", "by_date") == "by_date"
            else "step_2_title_by_doctor"
        )
        self.step2_title.setText(f"{t(title_key)} ({spec_name})" if spec_name else t(title_key))
        if hasattr(self, "mode_label"):
            self.mode_label.setText(t("lbl_booking_mode"))
        if hasattr(self, "mode_by_date_btn"):
            self.mode_by_date_btn.setText(t("mode_by_date"))
        if hasattr(self, "mode_by_doctor_btn"):
            self.mode_by_doctor_btn.setText(t("mode_by_doctor"))
        if hasattr(self, "by_doctor_header"):
            self.by_doctor_header.setText(t("lbl_all_doctors_in_spec"))
        if hasattr(self, "s2_quick_date_lbl"):
            self.s2_quick_date_lbl.setText(t("quick_select_date", default="Chọn nhanh ngày:"))
        if hasattr(self, "s2_date_lbl"):
            self.s2_date_lbl.setText(t("field_appointment_date", default="Chọn ngày khám:"))
        if hasattr(self, "s2_open_cal_btn"):
            self.s2_open_cal_btn.setText(t("btn_open_calendar", default="📅 Mở lịch"))
        self._update_s2_quick_chip_labels()
        if hasattr(self, "step2_date_edit") and hasattr(self, "step2_day_of_week_lbl"):
            day_num = self.step2_date_edit.date().dayOfWeek()
            self.step2_day_of_week_lbl.setText(f"({t(f'day_{day_num}')})")
            if hasattr(self, "by_date_doc_header"):
                self.by_date_doc_header.setText(
                    f"{t('lbl_choose_doctor_on_date')} ({self.step2_date_edit.date().toString('dd/MM/yyyy')} - {t(f'day_{day_num}')})"
                )

        # Step 3
        self.step3_back_btn.setText(t("step_3_back"))
        self.step3_title.setText(t("step_3_title"))
        if hasattr(self, "quick_date_lbl"):
            self.quick_date_lbl.setText(t("quick_select_date", default="Chọn nhanh ngày:"))
        if hasattr(self, "date_lbl"):
            self.date_lbl.setText(t("field_appointment_date", default="Chọn ngày khám:"))
        if hasattr(self, "open_cal_btn"):
            self.open_cal_btn.setText(t("btn_open_calendar", default="📅 Mở lịch"))
        self._update_quick_chip_labels()
        if hasattr(self, "slot_date_edit") and hasattr(self, "day_of_week_lbl"):
            day_num = self.slot_date_edit.date().dayOfWeek()
            self.day_of_week_lbl.setText(f"({t(f'day_{day_num}')})")

        # Step 4
        self.step4_back_btn.setText(t("step_4_back"))
        self.step4_title.setText(t("step_4_title"))
        if hasattr(self, "step4_reason_label"):
            self.step4_reason_label.setText(t("reason_label"))
        self.booking_reason_edit.setPlaceholderText(t("reason_placeholder"))
        self.submit_booking_btn.setText(t("confirm_booking_btn"))
        if self._current_step_index == 3:
            self._render_confirmation_summary()

    def _on_specialties_loaded(self, result: Any) -> None:
        self.specialties_data = result if isinstance(result, list) else []
        self._populate_specialties_combo(self.specialties_data)
        self._render_specialties_grid(self.specialties_data)

    def reset_flow(self) -> None:
        """Reset wizard state to start fresh."""
        self.selected_specialty = None
        self.selected_doctor = None
        self.selected_date = ""
        self.selected_slot = None
        self.booking_reason_edit.clear()
        if hasattr(self, "spec_combo"):
            self.spec_combo.blockSignals(True)
            self.spec_combo.setCurrentIndex(0)
            if self.spec_search_edit:
                self.spec_search_edit.clear()
            self.spec_combo.blockSignals(False)
        self._booking_mode = "by_date"
        if hasattr(self, "step2_stack"):
            self.step2_stack.setCurrentIndex(0)
        self._update_mode_buttons()
        self._go_to_step(0)
