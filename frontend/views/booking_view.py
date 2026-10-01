"""Comprehensive 4-step wizard view for patient self-service appointment booking."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
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
from frontend.views.common import BaseApiView, format_time_range
from frontend.widgets.calendar_dialog import CalendarDialog
from frontend.widgets.combo_box import ChevronComboBox
from frontend.widgets.empty_state import EmptyState
from frontend.widgets.page_header import PageHeader
from frontend.widgets.wizard_stepper import WizardStepper


def _set_style_state(widget: QWidget, name: str, value: object) -> None:
    """Update a QSS state property and immediately refresh the widget."""
    if widget.property(name) == value:
        return
    widget.setProperty(name, value)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class _SpecialtySearchComboBox(ChevronComboBox):
    """Keep mouse-wheel scrolling from changing the search selection."""

    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


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
        self._specialty_cards: list[QWidget] = []
        self._specialty_columns = 0
        self._slot_buttons: list[tuple[QPushButton, str, str]] = []
        self._slot_widgets: list[QPushButton] = []
        self._slot_columns = 0
        # Each replaceable catalog read gets its own monotonic version.  A
        # slower response is ignored as soon as the patient changes the
        # specialty, doctor, mode, or date that produced it.
        self._request_versions: dict[str, int] = {
            "doctors_by_date": 0,
            "doctors_by_specialty": 0,
            "doctor_schedule": 0,
            "slots": 0,
        }

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
        self.cancel_nav_btn.clicked.connect(self._navigate_header_back)
        self.header.add_action(self.cancel_nav_btn)
        root_layout.addWidget(self.header)

        # A single, canonical indicator avoids repeating "Bước n" inside
        # every surface and keeps the patient oriented throughout the flow.
        self.step_indicator = WizardStepper(self._step_labels())
        self.step_indicator.setMaximumWidth(900)
        self.step_indicator.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        stepper_row = QHBoxLayout()
        stepper_row.setContentsMargins(0, 0, 0, 0)
        stepper_row.addStretch(1)
        stepper_row.addWidget(self.step_indicator, 100)
        stepper_row.addStretch(1)
        root_layout.addLayout(stepper_row)

        root_layout.addWidget(self.feedback)
        root_layout.addWidget(self.loading)

        # Stacked layout for 4 steps
        self.step_container = QFrame()
        self.step_container.setObjectName("bookingWizardSurface")
        self.step_container.setMaximumWidth(1280)
        self.step_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.step_layout = QStackedLayout(self.step_container)
        canvas_row = QHBoxLayout()
        canvas_row.setContentsMargins(0, 0, 0, 0)
        canvas_row.addStretch(1)
        canvas_row.addWidget(self.step_container, 100)
        canvas_row.addStretch(1)
        root_layout.addLayout(canvas_row, 1)

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
        self.step1_title.setWordWrap(True)
        layout.addWidget(self.step1_title)

        self.step1_subtitle = QLabel(t("step_1_subtitle"))
        self.step1_subtitle.setObjectName("bookingSupportingText")
        self.step1_subtitle.setWordWrap(True)
        layout.addWidget(self.step1_subtitle)

        # Combined Searchable Dropdown bar
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        self.spec_combo = _SpecialtySearchComboBox()
        self.spec_combo.setEditable(True)
        self.spec_combo.setInsertPolicy(ChevronComboBox.InsertPolicy.NoInsert)
        self.spec_combo.setMinimumHeight(42)
        self.spec_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.spec_combo.setAccessibleName(t("step_1_title"))

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
        self.spec_continue_btn.setProperty("bookingRole", "continueAction")
        self.spec_continue_btn.setMinimumHeight(40)
        self.spec_continue_btn.clicked.connect(self._on_combo_continue_clicked)
        search_row.addWidget(self.spec_continue_btn)

        layout.addLayout(search_row)

        self.step1_divider = QLabel(t("spec_divider_lbl"))
        self.step1_divider.setObjectName("bookingSectionLead")
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
            self.spec_combo.addItem(f"{name} ({doc_text})", s)
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
        self._specialty_cards = []

        if not specialties:
            empty = EmptyState(t("no_specialty_found"), t("no_specialty_found_desc"))
            self.spec_grid_layout.addWidget(empty, 0, 0)
            return

        for spec in specialties:
            card = QFrame()
            card.setObjectName("card")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)

            name_lbl = QLabel(spec.get("specialty_name", ""))
            name_lbl.setObjectName("bookingSpecialtyName")
            name_lbl.setWordWrap(True)
            card_layout.addWidget(name_lbl)

            desc = spec.get("description") or "Chăm sóc và điều trị chuyên sâu theo tiêu chuẩn."
            desc_lbl = QLabel(desc)
            desc_lbl.setObjectName("bookingSupportingText")
            desc_lbl.setWordWrap(True)
            card_layout.addWidget(desc_lbl)

            doc_count = spec.get("doctor_count", 0)
            count_lbl = QLabel(t("affiliated_doctors", count=doc_count))
            count_lbl.setObjectName("bookingAccentMeta")
            card_layout.addWidget(count_lbl)

            # Button to select
            btn = QPushButton(t("select_this_specialty"))
            btn.setObjectName("secondaryButton")
            btn.clicked.connect(lambda _, s=spec: self._select_specialty(s))
            card_layout.addWidget(btn)

            self._specialty_cards.append(card)

        self._layout_specialty_cards(force=True)

    def _layout_specialty_cards(self, *, force: bool = False) -> None:
        if not self._specialty_cards:
            return
        columns = 2 if self.width() >= 980 else 1
        if not force and columns == self._specialty_columns:
            return
        self._specialty_columns = columns
        while self.spec_grid_layout.count():
            self.spec_grid_layout.takeAt(0)
        for index, card in enumerate(self._specialty_cards):
            self.spec_grid_layout.addWidget(card, index // columns, index % columns)
        for column in range(columns):
            self.spec_grid_layout.setColumnStretch(column, 1)

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

    def _next_request_version(self, scope: str) -> int:
        """Invalidate older reads in a UI scope and return the new version."""

        next_version = self._request_versions[scope] + 1
        self._request_versions[scope] = next_version
        return next_version

    # --------------------------------------------------------------------------
    # Step 2: DoctorList (with 2 Booking Modes: By Date vs By Doctor)
    # --------------------------------------------------------------------------
    def _build_step2_doctors(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Clear title and one compact context chip.  The global stepper already
        # communicates that this is step two.
        self.step2_title = QLabel(t("step_2_title_by_date"))
        self.step2_title.setObjectName("sectionTitle")
        self.step2_title.setWordWrap(True)
        layout.addWidget(self.step2_title)

        top_nav = QHBoxLayout()
        self.step2_back_btn = QPushButton("Đổi chuyên khoa")
        self.step2_back_btn.setObjectName("bookingContextChip")
        self.step2_back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.step2_back_btn.clicked.connect(lambda: self._go_to_step(0))
        top_nav.addWidget(self.step2_back_btn)
        top_nav.addStretch(1)
        layout.addLayout(top_nav)

        # One segmented control, instead of two independent bordered buttons.
        mode_section = QWidget()
        mode_section.setObjectName("bookingModeSection")
        mode_section_layout = QVBoxLayout(mode_section)
        mode_section_layout.setContentsMargins(0, 0, 0, 0)
        mode_section_layout.setSpacing(8)
        self.mode_label = QLabel(t("lbl_booking_mode"))
        self.mode_label.setObjectName("bookingModeLabel")
        mode_section_layout.addWidget(self.mode_label)

        self.mode_segment = QFrame()
        self.mode_segment.setObjectName("bookingSegmentedControl")
        mode_row = QHBoxLayout(self.mode_segment)
        mode_row.setContentsMargins(3, 3, 3, 3)
        mode_row.setSpacing(0)

        self.mode_by_date_btn = QPushButton(t("mode_by_date"))
        self.mode_by_date_btn.setObjectName("bookingModeOption")
        self.mode_by_date_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_by_date_btn.clicked.connect(lambda: self._set_booking_mode("by_date"))
        mode_row.addWidget(self.mode_by_date_btn, 1)

        self.mode_by_doctor_btn = QPushButton(t("mode_by_doctor"))
        self.mode_by_doctor_btn.setObjectName("bookingModeOption")
        self.mode_by_doctor_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_by_doctor_btn.clicked.connect(lambda: self._set_booking_mode("by_doctor"))
        mode_row.addWidget(self.mode_by_doctor_btn, 1)
        mode_section_layout.addWidget(self.mode_segment)
        layout.addWidget(mode_section)

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
        s2_quick_row = QGridLayout()
        s2_quick_row.setHorizontalSpacing(6)
        s2_quick_row.setVerticalSpacing(6)
        self.s2_quick_date_lbl = QLabel(t("quick_select_date", default="Chọn nhanh ngày:"))
        self.s2_quick_date_lbl.setObjectName("fieldLabel")
        s2_quick_row.addWidget(self.s2_quick_date_lbl, 0, 0, 1, 3)

        self._s2_quick_chip_buttons: list[tuple[QPushButton, QDate]] = []
        today = QDate.currentDate()
        for offset in range(6):
            target_d = today.addDays(offset)
            chip_btn = QPushButton()
            chip_btn.setObjectName("bookingDateChip")
            chip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            chip_btn.setProperty("active", False)
            chip_btn.clicked.connect(lambda _, d=target_d: self._select_s2_quick_date(d))
            self._s2_quick_chip_buttons.append((chip_btn, target_d))
            s2_quick_row.addWidget(chip_btn, 1 + offset // 3, offset % 3)
        for column in range(3):
            s2_quick_row.setColumnStretch(column, 1)

        # Keep the date editor as the canonical value/model for compatibility,
        # but expose only one date-picking affordance to the patient.
        self.step2_date_edit = QDateEdit()
        self.step2_date_edit.setCalendarPopup(True)
        self.step2_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.step2_date_edit.setDate(QDate.currentDate().addDays(1))
        self.step2_date_edit.setMinimumDate(QDate.currentDate())
        self.step2_date_edit.setMaximumDate(QDate.currentDate().addDays(60))
        self.step2_date_edit.dateChanged.connect(self._load_doctors_for_date)
        self.step2_date_edit.hide()

        self.s2_date_lbl = QLabel()
        self.s2_date_lbl.hide()

        self.s2_open_cal_btn = QPushButton(t("btn_other_date", default="Ngày khác…"))
        self.s2_open_cal_btn.setObjectName("bookingDateChip")
        self.s2_open_cal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.s2_open_cal_btn.clicked.connect(self._open_s2_calendar_dialog)
        s2_quick_row.addWidget(self.s2_open_cal_btn, 3, 0, 1, 3)
        by_date_layout.addLayout(s2_quick_row)
        self._update_s2_quick_chip_labels()

        self.step2_day_of_week_lbl = QLabel()
        self.step2_day_of_week_lbl.setObjectName("bookingAccentLabel")
        self.step2_day_of_week_lbl.hide()

        self.by_date_doc_header = QLabel(t("lbl_choose_doctor_on_date"))
        self.by_date_doc_header.setObjectName("bookingSectionLead")
        self.by_date_doc_header.setWordWrap(True)
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
        self.by_doctor_header.setObjectName("bookingSectionLead")
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
        by_date = getattr(self, "_booking_mode", "by_date") == "by_date"
        _set_style_state(self.mode_by_date_btn, "selected", by_date)
        _set_style_state(self.mode_by_doctor_btn, "selected", not by_date)

    def _update_step2_heading(self) -> None:
        """Keep the page title simple and put the current specialty in context."""

        self.step2_title.setText(t("step_2_title_by_date"))
        specialty_name = (
            str(self.selected_specialty.get("specialty_name", "")).strip()
            if self.selected_specialty
            else ""
        )
        change_label = t("change_short", default="Thay đổi")
        self.step2_back_btn.setText(
            f"{specialty_name} · {change_label}" if specialty_name else t("step_2_back")
        )

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
            _set_style_state(btn, "active", d == current_date)

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

        self._update_step2_heading()
        self.by_date_doc_header.setText(
            t(
                "doctors_working_heading",
                weekday=t(f"day_{day_num}"),
                date=qdate.toString("dd/MM/yyyy"),
            )
        )

        request_version = self._next_request_version("doctors_by_date")
        self.run_api_task(
            f"load_doctors_by_date:{request_version}",
            lambda specialty_id=spec_id, requested_date=date_str: self.api_client.get(
                "/api/v1/catalog/doctors",
                params={
                    "specialty_id": specialty_id,
                    "appointment_date": requested_date,
                },
            ),
            lambda result, requested_date=date_str: self._on_doctors_by_date_loaded(
                result,
                requested_date,
            ),
            loading_text="Đang tìm bác sĩ có lịch trực vào ngày này…",
            is_current=lambda: (
                self._request_versions["doctors_by_date"] == request_version
                and getattr(self, "_booking_mode", "by_date") == "by_date"
                and bool(self.selected_specialty)
                and self.selected_specialty.get("specialty_id") == spec_id
                and self.step2_date_edit.date().toString(Qt.DateFormat.ISODate)
                == date_str
            ),
        )

    def _on_doctors_by_date_loaded(self, result: Any, requested_date: str | None = None) -> None:
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

        date_str = requested_date or self.step2_date_edit.date().toString(Qt.DateFormat.ISODate)
        for doc in doctors:
            card = QFrame()
            card.setObjectName("card")
            card_layout = QHBoxLayout(card)
            card_layout.setSpacing(14)

            avatar = QLabel("BS")
            avatar.setObjectName("bookingDoctorAvatar")
            avatar.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(avatar)

            info_layout = QVBoxLayout()
            info_layout.setSpacing(4)
            name_lbl = QLabel(str(doc.get("full_name", "")))
            name_lbl.setObjectName("bookingDoctorName")
            name_lbl.setWordWrap(True)
            info_layout.addWidget(name_lbl)

            spec_lbl = QLabel(f"Chuyên khoa: {doc.get('specialty_name', '')}")
            spec_lbl.setObjectName("bookingDoctorSpecialty")
            info_layout.addWidget(spec_lbl)

            clinic_info = doc.get("clinic_name") or "Phòng khám chính"
            clinic_addr = doc.get("clinic_address") or ""
            clinic_lbl = QLabel(f"Cơ sở: {clinic_info} - {clinic_addr}")
            clinic_lbl.setObjectName("bookingCompactText")
            clinic_lbl.setWordWrap(True)
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
        signals_were_blocked = self.slot_date_edit.blockSignals(True)
        try:
            self.slot_date_edit.setDate(qdate)
        finally:
            self.slot_date_edit.blockSignals(signals_were_blocked)
        self._go_to_step(2)
        self._load_doctor_schedules_info(doc.get("doctor_id"))
        self._load_available_slots()

    def _load_doctors_for_specialty(self, specialty_id: int | None) -> None:
        self._update_step2_heading()
        request_version = self._next_request_version("doctors_by_specialty")
        self.run_api_task(
            f"load_doctors:{request_version}",
            lambda requested_specialty_id=specialty_id: self.api_client.get(
                "/api/v1/catalog/doctors",
                params={"specialty_id": requested_specialty_id},
            ),
            self._on_doctors_loaded,
            loading_text="Đang tải danh sách bác sĩ…",
            is_current=lambda: (
                self._request_versions["doctors_by_specialty"] == request_version
                and getattr(self, "_booking_mode", "by_date") == "by_doctor"
                and bool(self.selected_specialty)
                and self.selected_specialty.get("specialty_id") == specialty_id
            ),
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
            card_layout = QHBoxLayout(card)
            card_layout.setSpacing(14)

            avatar = QLabel("BS")
            avatar.setObjectName("bookingDoctorAvatar")
            avatar.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(avatar)

            info_layout = QVBoxLayout()
            info_layout.setSpacing(4)
            name_lbl = QLabel(str(doc.get("full_name", "")))
            name_lbl.setObjectName("bookingDoctorName")
            name_lbl.setWordWrap(True)
            info_layout.addWidget(name_lbl)

            spec_lbl = QLabel(f"Chuyên khoa: {doc.get('specialty_name', '')}")
            spec_lbl.setObjectName("bookingDoctorSpecialty")
            info_layout.addWidget(spec_lbl)

            clinic_info = doc.get("clinic_name") or "Phòng khám chính"
            clinic_addr = doc.get("clinic_address") or ""
            clinic_lbl = QLabel(f"Cơ sở: {clinic_info} - {clinic_addr}")
            clinic_lbl.setObjectName("bookingCompactText")
            clinic_lbl.setWordWrap(True)
            info_layout.addWidget(clinic_lbl)

            card_layout.addLayout(info_layout, 1)

            btn = QPushButton(t("select_this_specialty", default="Chọn lịch khám"))
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
            signals_were_blocked = self.slot_date_edit.blockSignals(True)
            try:
                self.slot_date_edit.setDate(QDate.currentDate().addDays(1))
            finally:
                self.slot_date_edit.blockSignals(signals_were_blocked)
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
                    parts.append(f"{day_name} ({format_time_range(st, et)})")
                schedule_text = ", ".join(parts)
                self.doc_schedule_lbl.setText(f"<b>{t('doctor_schedule_info')}</b> {schedule_text}")
                self.doc_schedule_lbl.show()
            else:
                if hasattr(self, "doc_schedule_lbl"):
                    self.doc_schedule_lbl.hide()

        request_version = self._next_request_version("doctor_schedule")
        self.run_api_task(
            f"load_doctor_schedules:{request_version}",
            _fetch,
            _on_done,
            loading_text="",
            is_current=lambda: (
                self._request_versions["doctor_schedule"] == request_version
                and bool(self.selected_doctor)
                and self.selected_doctor.get("doctor_id") == doctor_id
            ),
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
        self.step3_back_btn = QPushButton("Đổi bác sĩ")
        self.step3_back_btn.setObjectName("secondaryButton")
        self.step3_back_btn.clicked.connect(lambda: self._go_to_step(1))
        top_nav.addWidget(self.step3_back_btn)

        self.step3_title = QLabel("Bước 3: Chọn ngày và khung giờ khám")
        self.step3_title.setObjectName("sectionTitle")
        self.step3_title.setWordWrap(True)
        top_nav.addWidget(self.step3_title, 1)
        layout.addLayout(top_nav)

        # Doctor banner
        self.doc_banner = QFrame()
        self.doc_banner.setObjectName("card")
        self.doc_banner.setProperty("bookingRole", "doctorBanner")
        banner_layout = QVBoxLayout(self.doc_banner)
        banner_layout.setSpacing(4)
        self.doc_banner_lbl = QLabel()
        self.doc_banner_lbl.setWordWrap(True)
        banner_layout.addWidget(self.doc_banner_lbl)

        self.doc_schedule_lbl = QLabel()
        self.doc_schedule_lbl.setObjectName("bookingScheduleText")
        self.doc_schedule_lbl.setWordWrap(True)
        banner_layout.addWidget(self.doc_schedule_lbl)
        self.doc_schedule_lbl.hide()
        layout.addWidget(self.doc_banner)

        # Warning banner for anti-spam/active specialty
        self.specialty_warning_frame = QFrame()
        self.specialty_warning_frame.setObjectName("bookingWarningBanner")
        warn_layout = QHBoxLayout(self.specialty_warning_frame)
        warn_layout.setContentsMargins(10, 8, 10, 8)
        self.specialty_warning_lbl = QLabel()
        self.specialty_warning_lbl.setObjectName("bookingWarningText")
        self.specialty_warning_lbl.setWordWrap(True)
        warn_layout.addWidget(self.specialty_warning_lbl)
        self.specialty_warning_frame.hide()
        layout.addWidget(self.specialty_warning_frame)

        # Quick date chips row
        quick_row = QGridLayout()
        quick_row.setHorizontalSpacing(6)
        quick_row.setVerticalSpacing(6)
        self.quick_date_lbl = QLabel(t("quick_select_date", default="Chọn nhanh ngày:"))
        self.quick_date_lbl.setObjectName("fieldLabel")
        quick_row.addWidget(self.quick_date_lbl, 0, 0, 1, 3)

        self._quick_chip_buttons: list[tuple[QPushButton, QDate]] = []
        today = QDate.currentDate()
        for offset in range(6):
            target_d = today.addDays(offset)
            chip_btn = QPushButton()
            chip_btn.setObjectName("bookingDateChip")
            chip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            chip_btn.setProperty("active", False)
            chip_btn.clicked.connect(lambda _, d=target_d: self._select_quick_date(d))
            self._quick_chip_buttons.append((chip_btn, target_d))
            quick_row.addWidget(chip_btn, 1 + offset // 3, offset % 3)
        for column in range(3):
            quick_row.setColumnStretch(column, 1)

        # The hidden editor remains the canonical model; patients choose via
        # quick dates or the single "Ngày khác…" calendar action.
        self.slot_date_edit = QDateEdit()
        self.slot_date_edit.setCalendarPopup(True)
        self.slot_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.slot_date_edit.setDate(QDate.currentDate().addDays(1))
        self.slot_date_edit.setMinimumDate(QDate.currentDate())
        self.slot_date_edit.setMaximumDate(QDate.currentDate().addDays(60))
        self.slot_date_edit.dateChanged.connect(self._load_available_slots)
        self.slot_date_edit.hide()

        self.date_lbl = QLabel()
        self.date_lbl.hide()

        self.open_cal_btn = QPushButton(t("btn_other_date", default="Ngày khác…"))
        self.open_cal_btn.setObjectName("bookingDateChip")
        self.open_cal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_cal_btn.clicked.connect(self._open_calendar_dialog)
        quick_row.addWidget(self.open_cal_btn, 3, 0, 1, 3)
        layout.addLayout(quick_row)
        self._update_quick_chip_labels()

        self.day_of_week_lbl = QLabel()
        self.day_of_week_lbl.setObjectName("bookingAccentLabel")
        self.day_of_week_lbl.hide()

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
        self.slot_selected_lbl.setObjectName("bookingSelectionText")
        bottom_row.addWidget(self.slot_selected_lbl, 1)

        self.to_confirm_btn = QPushButton("Tiếp tục")
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
            _set_style_state(btn, "active", d == current_date)

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
        request_version = self._next_request_version("slots")
        self.run_api_task(
            f"load_slots:{request_version}",
            lambda requested_doctor_id=doctor_id, requested_date=date_str: self.api_client.get(
                f"/api/v1/catalog/doctors/{requested_doctor_id}/available-slots",
                params={"appointment_date": requested_date},
            ),
            self._on_slots_loaded,
            loading_text="Đang kiểm tra lịch làm việc & giờ còn trống…",
            is_current=lambda: (
                self._request_versions["slots"] == request_version
                and bool(self.selected_doctor)
                and self.selected_doctor.get("doctor_id") == doctor_id
                and self.slot_date_edit.date().toString(Qt.DateFormat.ISODate)
                == date_str
            ),
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
            self.specialty_warning_lbl.setText(spam_reason)
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

        self._slot_buttons = []
        self._slot_widgets = []

        for s in slots:
            start_t = s["start_time"]
            end_t = s["end_time"]
            is_avail = s.get("is_available", False)
            reason = s.get("reason") or "Không khả dụng"

            btn = QPushButton(format_time_range(start_t, end_t))
            btn.setObjectName("bookingSlotButton")
            btn.setProperty("selected", False)
            btn.setMinimumHeight(44)
            if is_avail:
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(
                    lambda _, st=start_t, et=end_t, b=btn: self._select_slot(st, et, b)
                )
                self._slot_buttons.append((btn, start_t, end_t))
            else:
                btn.setEnabled(False)
                btn.setToolTip(reason)

            self._slot_widgets.append(btn)
        self._layout_slot_buttons(force=True)

    def _layout_slot_buttons(self, *, force: bool = False) -> None:
        if not self._slot_widgets:
            return
        columns = 4 if self.width() >= 980 else 2
        if not force and columns == self._slot_columns:
            return
        self._slot_columns = columns
        while self.slots_layout.count():
            self.slots_layout.takeAt(0)
        for index, button in enumerate(self._slot_widgets):
            self.slots_layout.addWidget(button, index // columns, index % columns)
        for column in range(columns):
            self.slots_layout.setColumnStretch(column, 1)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._layout_specialty_cards()
        self._layout_slot_buttons()

    def _select_slot(self, start_t: str, end_t: str, active_btn: QPushButton) -> None:
        self.selected_slot = (start_t, end_t)
        self.slot_selected_lbl.setText(f"Đã chọn: {format_time_range(start_t, end_t)}")
        self.to_confirm_btn.setEnabled(True)

        for btn, _, _ in self._slot_buttons:
            _set_style_state(btn, "selected", btn is active_btn)

    # --------------------------------------------------------------------------
    # Step 4: AppointmentBooking Confirmation
    # --------------------------------------------------------------------------
    def _build_step4_confirm(self) -> QWidget:
        container = QWidget()
        container.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        top_nav = QHBoxLayout()
        self.step4_back_btn = QPushButton("Đổi giờ khám")
        self.step4_back_btn.setObjectName("secondaryButton")
        self.step4_back_btn.clicked.connect(lambda: self._go_to_step(2))
        top_nav.addWidget(self.step4_back_btn)

        self.step4_title = QLabel("Bước 4: Xác nhận thông tin đặt lịch")
        self.step4_title.setObjectName("sectionTitle")
        self.step4_title.setWordWrap(True)
        top_nav.addWidget(self.step4_title, 1)
        layout.addLayout(top_nav)

        # Summary review card
        self.confirm_card = QFrame()
        self.confirm_card.setObjectName("card")
        self.confirm_card.setProperty("bookingRole", "confirmation")
        self.confirm_card_layout = QVBoxLayout(self.confirm_card)
        self.confirm_card_layout.setSpacing(8)
        self.summary_details_lbl = QLabel()
        self.summary_details_lbl.setWordWrap(True)
        self.summary_details_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.summary_details_lbl.setObjectName("bookingSummaryDetails")
        self.confirm_card_layout.addWidget(self.summary_details_lbl)
        layout.addWidget(self.confirm_card)

        # Reason text edit
        self.step4_reason_label = QLabel(
            "Lý do khám bệnh / Triệu chứng lâm sàng:"
        )
        self.step4_reason_label.setObjectName("fieldLabel")
        self.step4_reason_label.setWordWrap(True)
        layout.addWidget(self.step4_reason_label)

        self.booking_reason_edit = QTextEdit()
        self.booking_reason_edit.setPlaceholderText(
            "Mô tả cụ thể triệu chứng, tình trạng sức khỏe hoặc yêu cầu khám bệnh..."
        )
        self.booking_reason_edit.setMaximumHeight(100)
        layout.addWidget(self.booking_reason_edit)

        # Final action buttons
        actions_row = QHBoxLayout()
        actions_row.addStretch(1)

        self.submit_booking_btn = QPushButton("Xác nhận đặt lịch")
        self.submit_booking_btn.setObjectName("primaryButton")
        self.submit_booking_btn.setProperty("bookingRole", "submitAction")
        self.submit_booking_btn.setMinimumHeight(44)
        self.submit_booking_btn.clicked.connect(self._submit_booking)
        actions_row.addWidget(self.submit_booking_btn)

        layout.addLayout(actions_row)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("bookingConfirmScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(container)
        return scroll

    def _render_confirmation_summary(self) -> None:
        if not self.selected_doctor or not self.selected_slot:
            return

        doc_name = self.selected_doctor.get("full_name", "")
        spec_name = self.selected_doctor.get("specialty_name", "")
        clinic_name = self.selected_doctor.get("clinic_name", "Phòng khám chính")
        clinic_addr = self.selected_doctor.get("clinic_address", "")
        start_t, end_t = self.selected_slot

        html = f"""
        <h3>{t("summary_title")}</h3>
        <p><b>{t("summary_specialty")}:</b> {spec_name}</p>
        <p><b>{t("summary_doctor")}:</b> {doc_name}</p>
        <p><b>{t("summary_location")}:</b> {clinic_name} ({clinic_addr})</p>
        <p><b>{t("summary_date")}:</b> <b>{self.selected_date}</b></p>
        <p><b>{t("summary_time")}:</b> <b>{format_time_range(start_t, end_t)}</b></p>
        <p><i>{t("summary_note")}</i></p>
        """
        self.summary_details_lbl.setText(html)

    def _submit_booking(self) -> None:
        if not self.selected_doctor or not self.selected_slot:
            self.feedback.show_message(
                "Chưa đủ thông tin đặt lịch",
                "Vui lòng chọn bác sĩ và khung giờ trước khi xác nhận.",
                severity="warning",
            )
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
    def _navigate_header_back(self) -> None:
        if self._current_step_index > 0:
            self._go_to_step(self._current_step_index - 1)
            return
        self.back_requested.emit()

    def _go_to_step(self, step_index: int) -> None:
        self._current_step_index = step_index
        self._update_step_indicator()
        self._update_header_back_label()
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
            self._update_step2_heading()
        elif step_index == 3:
            self._render_confirmation_summary()

    def _update_step_indicator(self) -> None:
        labels = self._step_labels()
        if self.step_indicator.steps != tuple(labels):
            self.step_indicator.set_steps(labels)
        self.step_indicator.set_current_step(self._current_step_index)

    def _update_header_back_label(self) -> None:
        if self._current_step_index > 0:
            self.cancel_nav_btn.setText(t("back_to_previous_step"))
        else:
            self.cancel_nav_btn.setText(t("back_to_booking_list"))

    @staticmethod
    def _step_labels() -> list[str]:
        return [
            t("wizard_specialty", default="Chuyên khoa"),
            t("wizard_doctor", default="Bác sĩ"),
            t("wizard_datetime", default="Ngày & giờ"),
            t("wizard_confirm", default="Xác nhận"),
        ]

    def retranslate_ui(self) -> None:
        """Dynamically update all visible text in BookingView."""
        self.header.title_label.setText(t("booking_header_title"))
        self.header.subtitle_label.setText(t("booking_header_subtitle"))
        self._update_header_back_label()
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
        self._update_step2_heading()
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
            self.s2_open_cal_btn.setText(t("btn_other_date", default="Ngày khác…"))
        self._update_s2_quick_chip_labels()
        if hasattr(self, "step2_date_edit") and hasattr(self, "step2_day_of_week_lbl"):
            day_num = self.step2_date_edit.date().dayOfWeek()
            self.step2_day_of_week_lbl.setText(f"({t(f'day_{day_num}')})")
            if hasattr(self, "by_date_doc_header"):
                self.by_date_doc_header.setText(
                    t(
                        "doctors_working_heading",
                        weekday=t(f"day_{day_num}"),
                        date=self.step2_date_edit.date().toString("dd/MM/yyyy"),
                    )
                )

        # Step 3
        self.step3_back_btn.setText(t("step_3_back"))
        self.step3_title.setText(t("step_3_title"))
        if hasattr(self, "quick_date_lbl"):
            self.quick_date_lbl.setText(t("quick_select_date", default="Chọn nhanh ngày:"))
        if hasattr(self, "date_lbl"):
            self.date_lbl.setText(t("field_appointment_date", default="Chọn ngày khám:"))
        if hasattr(self, "open_cal_btn"):
            self.open_cal_btn.setText(t("btn_other_date", default="Ngày khác…"))
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
        for scope in self._request_versions:
            self._request_versions[scope] += 1
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
