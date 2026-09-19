"""Read-only examination result and prescription."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.views.common import (
    BaseApiView,
    configure_table,
    display_text,
    format_datetime,
    require_dict,
    table_item,
)


class MedicalResultView(BaseApiView):
    back_requested = Signal()
    appointment_requested = Signal(int)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._medical_record_id: int | None = None
        self._appointment_id: int | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        header = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("secondaryButton")
        title = QLabel("Medical Result")
        title.setObjectName("pageTitle")
        header.addWidget(self.back_button)
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)
        root.addWidget(self.loading)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(16)

        summary = QFrame()
        summary.setObjectName("contentCard")
        grid = QGridLayout(summary)
        grid.setContentsMargins(22, 18, 22, 18)
        self.values: dict[str, QLabel] = {}
        fields = [
            ("Examination Date", "date"),
            ("Doctor", "doctor"),
            ("Specialty", "specialty"),
            ("Clinic", "clinic"),
            ("Symptoms", "symptoms"),
            ("Diagnosis", "diagnosis"),
            ("Notes", "notes"),
        ]
        for index, (label, key) in enumerate(fields):
            label_widget = QLabel(label)
            label_widget.setObjectName("fieldLabel")
            value = QLabel("—")
            value.setWordWrap(True)
            grid.addWidget(label_widget, index, 0)
            grid.addWidget(value, index, 1)
            self.values[key] = value
        grid.setColumnStretch(1, 1)
        content_layout.addWidget(summary)

        prescription_title = QLabel("Prescription")
        prescription_title.setObjectName("sectionTitle")
        content_layout.addWidget(prescription_title)
        self.prescription_table = QTableView()
        self.prescription_model: QStandardItemModel = configure_table(
            self.prescription_table,
            ["Medicine", "Quantity", "Dosage", "Instructions"],
        )
        self.prescription_table.setMinimumHeight(180)
        self.no_prescription = QLabel("No prescription for this examination.")
        self.no_prescription.setObjectName("emptyState")
        content_layout.addWidget(self.prescription_table)
        content_layout.addWidget(self.no_prescription)

        actions = QHBoxLayout()
        actions.addStretch()
        self.appointment_button = QPushButton("View Appointment")
        self.appointment_button.setObjectName("primaryButton")
        actions.addWidget(self.appointment_button)
        content_layout.addLayout(actions)
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self.back_button.clicked.connect(self.back_requested)
        self.appointment_button.clicked.connect(self._open_appointment)
        self.clear_data()

    def activate(self, medical_record_id: int) -> None:
        self.invalidate_pending()
        self.clear_data()
        self._medical_record_id = medical_record_id
        self.load()

    def load(self) -> None:
        if self._medical_record_id is None:
            return
        record_id = self._medical_record_id
        self.run_api_task(
            "medical-result",
            lambda: self.api_client.get(f"/api/v1/medical-records/me/{record_id}"),
            self._render,
            controls=(self.back_button, self.appointment_button),
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
        has_prescription = isinstance(prescription, dict)
        self.prescription_table.setVisible(has_prescription)
        self.no_prescription.setVisible(not has_prescription)

    def _open_appointment(self) -> None:
        if self._appointment_id is not None:
            self.appointment_requested.emit(self._appointment_id)

    def clear_data(self) -> None:
        self._medical_record_id = None
        self._appointment_id = None
        for value in self.values.values():
            value.setText("—")
        self.prescription_model.removeRows(0, self.prescription_model.rowCount())
        self.prescription_table.hide()
        self.no_prescription.show()
        self.appointment_button.hide()
