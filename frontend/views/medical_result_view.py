"""Read-only examination result and prescription."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.core.i18n import get_i18n, t
from frontend.views.common import (
    BaseApiView,
    configure_table,
    display_text,
    format_datetime,
    require_dict,
    table_item,
)
from frontend.widgets.empty_state import EmptyState
from frontend.widgets.page_header import PageHeader


class MedicalResultView(BaseApiView):
    back_requested = Signal()
    appointment_requested = Signal(int)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._medical_record_id: int | None = None
        self._appointment_id: int | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(14)

        self.header = PageHeader(
            t("medical_result_title"),
            t("medical_result_subtitle"),
            show_back=True,
        )
        self.back_button = self.header.back_button
        self.title = self.header.title_label
        self.appointment_button = QPushButton(t("btn_view_appointment"))
        self.appointment_button.setObjectName("primaryButton")
        self.header.add_action(self.appointment_button)
        root.addWidget(self.header)
        root.addWidget(self.feedback)
        root.addWidget(self.loading)

        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAccessibleName("Medical result information")
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 2, 8, 4)
        content_layout.setSpacing(16)

        summary = QFrame()
        summary.setObjectName("infoCard")
        grid = QGridLayout(summary)
        grid.setContentsMargins(24, 20, 24, 20)
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(12)
        self.summary_title = QLabel(t("sec_exam_summary"))
        self.summary_title.setObjectName("sectionTitle")
        grid.addWidget(self.summary_title, 0, 0, 1, 2)
        self.values: dict[str, QLabel] = {}
        self._field_labels: dict[str, QLabel] = {}
        fields = [
            ("th_exam_date", "date"),
            ("field_doctor", "doctor"),
            ("field_specialty", "specialty"),
            ("field_clinic", "clinic"),
            ("field_symptoms", "symptoms"),
            ("th_diagnosis", "diagnosis"),
            ("field_clinical_notes", "notes"),
        ]
        for row, (label_key, key) in enumerate(fields, start=1):
            label_widget = QLabel(t(label_key))
            label_widget.setObjectName("fieldLabel")
            label_widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self._field_labels[key] = label_widget
            value = QLabel("—")
            value.setObjectName("fieldValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
            value.setAccessibleName(t(label_key))
            grid.addWidget(label_widget, row, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(value, row, 1, Qt.AlignmentFlag.AlignTop)
            self.values[key] = value
        grid.setColumnMinimumWidth(0, 142)
        grid.setColumnStretch(1, 1)
        content_layout.addWidget(summary)

        prescription_card = QFrame()
        prescription_card.setObjectName("tableCard")
        prescription_layout = QVBoxLayout(prescription_card)
        prescription_layout.setContentsMargins(20, 18, 20, 20)
        prescription_layout.setSpacing(12)
        self.prescription_title = QLabel(t("sec_prescription"))
        self.prescription_title.setObjectName("sectionTitle")
        prescription_layout.addWidget(self.prescription_title)
        self.prescription_table = QTableView()
        self.prescription_table.setAccessibleName("Prescription items")
        self.prescription_model: QStandardItemModel = configure_table(
            self.prescription_table,
            [t("th_medicine"), t("th_quantity"), t("th_dosage"), t("th_instructions")],
            stretch_column=3,
            column_widths={0: 190, 1: 90, 2: 170, 3: 300},
        )
        self.prescription_table.setMinimumHeight(190)
        self.no_prescription = EmptyState(
            t("no_prescription_title"),
            t("no_prescription_desc"),
        )
        prescription_layout.addWidget(self.prescription_table)
        prescription_layout.addWidget(self.no_prescription)
        content_layout.addWidget(prescription_card)
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self.header.back_requested.connect(self.back_requested.emit)
        self.appointment_button.clicked.connect(self._open_appointment)

        get_i18n().language_changed.connect(self.retranslate_ui)
        self.clear_data()

    def retranslate_ui(self) -> None:
        """Update all text in MedicalResultView according to current language."""
        self.header.set_title(t("medical_result_title"))
        if self._medical_record_id is not None:
            self.header.set_subtitle(f"#{self._medical_record_id:06d}")
        else:
            self.header.set_subtitle(t("medical_result_subtitle"))
        self.appointment_button.setText(t("btn_view_appointment"))
        self.summary_title.setText(t("sec_exam_summary"))

        field_key_map = {
            "date": "th_exam_date",
            "doctor": "field_doctor",
            "specialty": "field_specialty",
            "clinic": "field_clinic",
            "symptoms": "field_symptoms",
            "diagnosis": "th_diagnosis",
            "notes": "field_clinical_notes",
        }
        for key, lbl in self._field_labels.items():
            if key in field_key_map:
                lbl.setText(t(field_key_map[key]))

        self.prescription_title.setText(t("sec_prescription"))
        p_headers = [t("th_medicine"), t("th_quantity"), t("th_dosage"), t("th_instructions")]
        for col, h in enumerate(p_headers):
            self.prescription_model.setHeaderData(col, Qt.Orientation.Horizontal, h)

        self.no_prescription.set_title(t("no_prescription_title"))
        self.no_prescription.set_description(t("no_prescription_desc"))
        self.clear_data()

    def activate(self, medical_record_id: int) -> None:
        self.invalidate_pending()
        self.clear_data()
        self._medical_record_id = medical_record_id
        self.header.set_subtitle(f"Medical record #{medical_record_id:06d}")
        self.load()

    def load(self) -> None:
        if self._medical_record_id is None:
            return
        record_id = self._medical_record_id
        self.run_api_task(
            "medical-result",
            lambda: self.api_client.get(f"/api/v1/medical-records/me/{record_id}"),
            self._render,
            controls=(self.appointment_button,),
            loading_text=t("loading"),
        )

    def _render(self, payload: object) -> None:
        data = require_dict(payload)
        doctor = data.get("doctor") or {}
        clinic = data.get("clinic") or {}
        values: dict[str, Any] = {
            "date": format_datetime(data.get("examination_date")),
            "doctor": doctor.get("full_name"),
            "specialty": doctor.get("specialty"),
            "clinic": clinic.get("clinic_name"),
            "symptoms": data.get("symptoms"),
            "diagnosis": data.get("diagnosis"),
            "notes": data.get("notes"),
        }
        for key, value in values.items():
            if key in self.values:
                self.values[key].setText(display_text(value))
        appt_id = data.get("appointment_id")
        self._appointment_id = int(appt_id) if appt_id is not None else None
        self.appointment_button.show()

        self.prescription_model.removeRows(0, self.prescription_model.rowCount())
        prescription = data.get("prescription")
        items = prescription.get("items", []) if isinstance(prescription, dict) else []
        for item in items:
            self.prescription_model.appendRow(
                [
                    table_item(item.get("medicine_name")),
                    table_item(item.get("quantity")),
                    table_item(item.get("dosage")),
                    table_item(item.get("instructions")),
                ]
            )
        has_items = bool(items)
        self.prescription_table.setVisible(has_items)
        self.no_prescription.setVisible(not has_items)

    def _open_appointment(self) -> None:
        if self._appointment_id is not None:
            self.appointment_requested.emit(self._appointment_id)

    def clear_data(self) -> None:
        self._medical_record_id = None
        self._appointment_id = None
        self.header.set_subtitle("A read-only summary of your examination and prescription.")
        for value in self.values.values():
            value.setText("—")
        self.prescription_model.removeRows(0, self.prescription_model.rowCount())
        self.prescription_table.hide()
        self.no_prescription.hide()
        self.appointment_button.hide()
