"""Paginated medical record history."""

from __future__ import annotations

from PySide6.QtCore import QDate, QModelIndex, Qt, Signal
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QCalendarWidget,
    QCheckBox,
    QFrame,
    QDateEdit,
    QLabel,
    QGridLayout,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.core.i18n import get_i18n, t
from frontend.views.common import (
    BaseApiView,
    configure_table,
    format_datetime,
    require_page,
    table_item,
)
from frontend.widgets.page_header import PageHeader
from frontend.widgets.combo_box import ChevronComboBox
from frontend.widgets.pagination import PaginationWidget
from frontend.widgets.state_host import StateHost


class MedicalHistoryView(BaseApiView):
    medical_record_requested = Signal(int)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._page = 1
        self._total_records = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        self.header = PageHeader(t("medical_history_title"), t("medical_history_subtitle"))
        root.addWidget(self.header)

        filter_card = QFrame()
        filter_card.setObjectName("filterBar")
        filters = QGridLayout(filter_card)
        filters.setContentsMargins(16, 16, 16, 16)
        filters.setHorizontalSpacing(10)
        filters.setVerticalSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText(t("medical_search_placeholder"))
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName(t("a11y_search_medical_history"))
        filters.addWidget(self.search, 0, 0, 1, 5)

        self.date_filter = QCheckBox(t("filter_by_examination_date"))
        self.date_filter.setObjectName("filterCheckBox")
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setEnabled(False)
        self.date_edit.calendarWidget().setMinimumSize(360, 280)
        self.date_edit.calendarWidget().setGridVisible(True)
        self.date_edit.calendarWidget().setHorizontalHeaderFormat(
            QCalendarWidget.HorizontalHeaderFormat.ShortDayNames
        )
        self.date_edit.setAccessibleName(t("filter_by_examination_date"))
        self.specialty_label = QLabel(t("filter_by_specialty"))
        self.specialty_label.setObjectName("fieldLabel")
        self.specialty = ChevronComboBox()
        self.specialty.setMinimumWidth(180)
        self.clinic_label = QLabel(t("filter_by_clinic"))
        self.clinic_label.setObjectName("fieldLabel")
        self.clinic = ChevronComboBox()
        self.clinic.setMinimumWidth(180)
        self._filter_options_loaded = False

        self.refresh_button = QPushButton(t("btn_refresh"))
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.setAccessibleName(t("btn_refresh"))
        self.details_button = QPushButton(t("btn_view_details"))
        self.details_button.setObjectName("primaryButton")
        self.details_button.setAccessibleName(t("btn_view_details"))
        self.details_button.setEnabled(False)

        filters.addWidget(self.date_filter, 1, 0)
        filters.addWidget(self.date_edit, 1, 1)
        filters.addWidget(self.specialty_label, 1, 2)
        filters.addWidget(self.specialty, 1, 3)
        filters.addWidget(self.refresh_button, 1, 4)
        filters.addWidget(self.clinic_label, 2, 0)
        filters.addWidget(self.clinic, 2, 1, 1, 2)
        filters.addWidget(self.details_button, 2, 4)
        root.addWidget(filter_card)
        root.addWidget(self.feedback)
        root.addWidget(self.loading)

        self.table = QTableView()
        self.table.setAccessibleName(t("a11y_medical_history_results"))
        self.table.setAccessibleDescription(t("a11y_open_selected_row"))
        self.model: QStandardItemModel = configure_table(
            self.table,
            [t("th_exam_date"), t("field_doctor"), t("field_specialty"), t("th_diagnosis")],
            stretch_column=3,
            column_widths={0: 152, 1: 152, 2: 124},
            wrap_columns={3},
        )

        self.state_host = StateHost(self.table)
        self.bind_state_host(self.state_host)
        self.empty_state = self.state_host.empty
        self.empty_state.set_title(t("no_records_found"))
        self.empty_state.set_description(t("no_records_desc"))
        self.empty_state.set_action(t("btn_refresh"))
        self.empty_state.setAccessibleName(t("no_records_found"))
        root.addWidget(self.state_host, 1)

        self.pagination = PaginationWidget()
        self.pagination.setAccessibleName(t("medical_history_title"))
        root.addWidget(self.pagination)

        self.search.returnPressed.connect(self._search)
        self.date_filter.toggled.connect(self._date_filter_changed)
        self.date_edit.dateChanged.connect(lambda: self._search() if self.date_filter.isChecked() else None)
        self.specialty.currentIndexChanged.connect(self._filter_changed)
        self.clinic.currentIndexChanged.connect(self._filter_changed)
        self.refresh_button.clicked.connect(self._search)
        self.details_button.clicked.connect(self._open_selected)
        self.table.activated.connect(self._open_index)
        self.table.selectionModel().selectionChanged.connect(
            lambda *_args: self._sync_details_button()
        )
        self.state_host.empty_action_requested.connect(self._retry)
        self.state_host.retry_requested.connect(self._retry)
        self.pagination.page_changed.connect(self._change_page)
        self.pagination.page_size_changed.connect(self._page_size_changed)

        get_i18n().language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self) -> None:
        """Update all text in MedicalHistoryView according to current language."""
        self.header.set_title(t("medical_history_title"))
        if self._total_records > 0:
            self.header.set_subtitle(t("records_count", count=self._total_records))
        else:
            self.header.set_subtitle(t("medical_history_subtitle"))
        self.search.setPlaceholderText(t("medical_search_placeholder"))
        self.date_filter.setText(t("filter_by_examination_date"))
        self.date_edit.setAccessibleName(t("filter_by_examination_date"))
        self.specialty_label.setText(t("filter_by_specialty"))
        self.clinic_label.setText(t("filter_by_clinic"))
        self.refresh_button.setText(t("btn_refresh"))
        self.details_button.setText(t("btn_view_details"))
        self.search.setAccessibleName(t("a11y_search_medical_history"))
        self.refresh_button.setAccessibleName(t("btn_refresh"))
        self.details_button.setAccessibleName(t("btn_view_details"))
        self.table.setAccessibleName(t("a11y_medical_history_results"))
        self.table.setAccessibleDescription(t("a11y_open_selected_row"))
        self.empty_state.setAccessibleName(t("no_records_found"))
        self.pagination.setAccessibleName(t("medical_history_title"))
        self.empty_state.set_title(t("no_records_found"))
        self.empty_state.set_description(t("no_records_desc"))
        self.empty_state.set_action(t("btn_refresh"))
        headers = [t("th_exam_date"), t("field_doctor"), t("field_specialty"), t("th_diagnosis")]
        for col, h in enumerate(headers):
            self.model.setHeaderData(col, Qt.Orientation.Horizontal, h)

    def activate(self) -> None:
        if self._filter_options_loaded:
            self.load()
            return
        self.run_api_task(
            "medical-filter-options",
            lambda: self.api_client.get("/api/v1/catalog/doctors"),
            self._filter_options_loaded_successfully,
            loading_text=t("loading"),
        )

    def _filter_options_loaded_successfully(self, doctors: object) -> None:
        specialty_names = sorted(
            {str(item.get("specialty_name")) for item in doctors if item.get("specialty_name")}
        ) if isinstance(doctors, list) else []
        clinic_names = sorted(
            {str(item.get("clinic_name")) for item in doctors if item.get("clinic_name")}
        ) if isinstance(doctors, list) else []
        self._populate_filter_combo(self.specialty, specialty_names)
        self._populate_filter_combo(self.clinic, clinic_names)
        self._filter_options_loaded = True
        self.load()

    @staticmethod
    def _populate_filter_combo(combo: ChevronComboBox, values: list[str]) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(t("filter_all"), "")
        for value in values:
            combo.addItem(value, value)
        combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _date_filter_changed(self, enabled: bool) -> None:
        self.date_edit.setEnabled(enabled)
        self._search()

    def load(self) -> None:
        params: dict[str, object] = {
            "page": self._page,
            "page_size": self.pagination.page_size,
        }
        keyword = self.search.text().strip()
        if keyword:
            params["keyword"] = keyword
        if self.date_filter.isChecked():
            params["examination_date"] = self.date_edit.date().toString("yyyy-MM-dd")
        specialty = str(self.specialty.currentData() or "").strip()
        clinic = str(self.clinic.currentData() or "").strip()
        if specialty:
            params["specialty"] = specialty
        if clinic:
            params["clinic"] = clinic

        self.details_button.setEnabled(False)
        self.run_api_task(
            "medical-history",
            lambda: self.api_client.get("/api/v1/medical-records/me", params=params),
            self._render,
            controls=(
                self.search,
                self.refresh_button,
                self.details_button,
                self.table,
                self.empty_state.action_button,
                self.pagination,
            ),
            loading_text=t("loading"),
            on_finished=self._sync_details_button,
        )

    def _render(self, payload: object) -> None:
        page = require_page(payload)
        items = page["items"]
        self.model.removeRows(0, self.model.rowCount())
        for record in items:
            doctor = record.get("doctor") or {}
            record_id = int(record["medical_record_id"])
            self.model.appendRow(
                [
                    table_item(
                        format_datetime(record.get("examination_date")),
                        user_data=record_id,
                    ),
                    table_item(doctor.get("full_name")),
                    table_item(doctor.get("specialty")),
                    table_item(record.get("diagnosis")),
                ]
            )

        self._page = int(page.get("page", self._page))
        total = int(page.get("total", 0))
        self._total_records = total
        self.pagination.set_page(
            self._page,
            int(page.get("total_pages", 0)),
            total,
        )
        self.header.set_subtitle(t("records_count", count=total))
        self.table.clearSelection()
        self.details_button.setEnabled(False)
        if items:
            self.state_host.show_content()
        else:
            self.state_host.show_empty(
                t("no_records_found"),
                t("no_records_desc"),
                action_text=t("btn_refresh"),
            )

    def _selected_id(self) -> int | None:
        indexes = self.table.selectionModel().selectedRows(0)
        if not indexes:
            return None
        value = indexes[0].data(role=Qt.ItemDataRole.UserRole)
        return int(value) if value is not None else None

    def _open_selected(self) -> None:
        record_id = self._selected_id()
        if record_id is not None:
            self.medical_record_requested.emit(record_id)

    def _open_index(self, index: QModelIndex) -> None:
        value = self.model.index(index.row(), 0).data(role=Qt.ItemDataRole.UserRole)
        if value is not None:
            self.medical_record_requested.emit(int(value))

    def _search(self) -> None:
        self._page = 1
        self.load()

    def _filter_changed(self, _index: int = 0) -> None:
        self._search()

    def _retry(self) -> None:
        self._page = 1
        self.load()

    def _change_page(self, page: int) -> None:
        self._page = page
        self.load()

    def _page_size_changed(self, _size: int) -> None:
        self._page = 1
        self.load()

    def _sync_details_button(self) -> None:
        has_selection = bool(self.table.selectionModel().selectedRows())
        self.details_button.setEnabled(not self._workers and has_selection)

    def clear_data(self) -> None:
        self._page = 1
        self._total_records = 0
        self.search.clear()
        self.date_filter.setChecked(False)
        self.date_edit.setDate(QDate.currentDate())
        self.specialty.setCurrentIndex(0)
        self.clinic.setCurrentIndex(0)
        self.model.removeRows(0, self.model.rowCount())
        self.table.clearSelection()
        self.pagination.reset()
        self.header.set_subtitle(t("medical_history_subtitle"))
        self.state_host.show_content()
        self.details_button.setEnabled(False)
