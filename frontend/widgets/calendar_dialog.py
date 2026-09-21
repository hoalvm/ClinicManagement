"""Visual calendar selection dialog for PySide6 patient portal."""

from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCalendarWidget,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from frontend.core.i18n import get_i18n, t
from frontend.ui.icons import line_icon


class CalendarDialog(QDialog):
    """Modern modal dialog allowing patients to visually pick an appointment date."""

    def __init__(
        self,
        current_date: QDate | None = None,
        min_date: QDate | None = None,
        max_date: QDate | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("calendar_dialog_title", default="Chọn ngày khám"))
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setMinimumHeight(390)

        self._selected_date = current_date or QDate.currentDate()
        self._min_date = min_date or QDate.currentDate()
        self._max_date = max_date or QDate.currentDate().addDays(60)

        self._build_ui()
        get_i18n().language_changed.connect(self.retranslate_ui)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header title
        self.header_lbl = QLabel(t("calendar_dialog_title", default="Chọn ngày khám bệnh"))
        self.header_lbl.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #0f766e; margin-bottom: 4px;"
        )
        layout.addWidget(self.header_lbl)

        # Calendar Widget
        self.calendar = QCalendarWidget(self)
        self.calendar.setGridVisible(True)
        self.calendar.setMinimumDate(self._min_date)
        self.calendar.setMaximumDate(self._max_date)
        self.calendar.setSelectedDate(self._selected_date)
        self.calendar.setNavigationBarVisible(True)
        self.calendar.activated.connect(self._on_date_activated)
        layout.addWidget(self.calendar, 1)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        self.cancel_btn = QPushButton(t("calendar_dialog_close", default="Đóng"))
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.select_btn = QPushButton(t("calendar_dialog_select", default="Chọn ngày này"))
        self.select_btn.setObjectName("primaryButton")
        self.select_btn.setIcon(line_icon("calendar", "#ffffff", size=16))
        self.select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_btn.clicked.connect(self._on_confirmed)
        btn_layout.addWidget(self.select_btn)

        layout.addLayout(btn_layout)

    def _on_date_activated(self, date: QDate) -> None:
        self._selected_date = date
        self.accept()

    def _on_confirmed(self) -> None:
        self._selected_date = self.calendar.selectedDate()
        self.accept()

    def selected_date(self) -> QDate:
        return self._selected_date

    def retranslate_ui(self) -> None:
        self.setWindowTitle(t("calendar_dialog_title", default="Chọn ngày khám"))
        self.header_lbl.setText(t("calendar_dialog_title", default="Chọn ngày khám bệnh"))
        self.select_btn.setText(t("calendar_dialog_select", default="Chọn ngày này"))
        self.cancel_btn.setText(t("calendar_dialog_close", default="Đóng"))
