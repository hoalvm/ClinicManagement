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
from frontend.ui.icons import apply_line_icon
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
            "Medical Result",
            "A read-only summary of your examination and prescription.",
            show_back=True,
        )
        self.back_button = self.header.back_button
        self.title = self.header.title_label
        self.appointment_button = QPushButton("View appointment")
        self.appointment_button.setObjectName("primaryButton")
        apply_line_icon(
            self.appointment_button,
            "calendar",
            "#FFFFFF",
            active_color="#FFFFFF",
            accessible_name="View related appointment",
        )
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
        summary_title = QLabel("Examination summary")
        summary_title.setObjectName("sectionTitle")
        grid.addWidget(summary_title, 0, 0, 1, 2)
        self.values: dict[str, QLabel] = {}
        fields = [
            ("Examination date", "date"),
            ("Doctor", "doctor"),
            ("Specialty", "specialty"),
            ("Clinic", "clinic"),
            ("Symptoms", "symptoms"),
            ("Diagnosis", "diagnosis"),
            ("Clinical notes", "notes"),
        ]
        for row, (label, key) in enumerate(fields, start=1):
            label_widget = QLabel(label)
            label_widget.setObjectName("fieldLabel")
            label_widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            value = QLabel("—")
            value.setObjectName("fieldValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
            value.setAccessibleName(label)
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
        prescription_title = QLabel("Prescription")
        prescription_title.setObjectName("sectionTitle")
        prescription_layout.addWidget(prescription_title)
        self.prescription_table = QTableView()
        self.prescription_table.setAccessibleName("Prescription items")
        self.prescription_model: QStandardItemModel = configure_table(
            self.prescription_table,
            ["Medicine", "Quantity", "Dosage", "Instructions"],
            stretch_column=3,
            column_widths={0: 190, 1: 90, 2: 170, 3: 300},
        )
        self.prescription_table.setMinimumHeight(190)
        self.no_prescription = EmptyState(
            "No prescription",
            "No medication was prescribed for this examination.",
            icon="medical",
        )
        prescription_layout.addWidget(self.prescription_table)
        prescription_layout.addWidget(self.no_prescription)
        content_layout.addWidget(prescription_card)
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self.header.back_requested.connect(self.back_requested.emit)
        self.appointment_button.clicked.connect(self._open_appointment)
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
            loading_text="Loading medical result…",
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
            self.values[key].setText(display_text(value))
        self._appointment_id = int(data["appointment_id"])
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
