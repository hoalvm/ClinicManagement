"""Modern, clean Statistics and Overview page for Admin."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from frontend.api_client import api_client
from frontend.pages.admin_ui import AdminApiPage, require_success
from frontend.ui.design_system import ColumnDisplayMode, ColumnPriority, ColumnSpec
from frontend.views.common import format_money
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.page_header import PageHeader
from frontend.widgets.stat_card import ModernStatCard


class StatisticsPage(AdminApiPage):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(28, 24, 28, 24)
        self.main_layout.setSpacing(20)

        # ------------------- Header -------------------
        self.header = PageHeader(
            "Thống kê",
            "Tổng quan số liệu hoạt động",
        )
        self.main_layout.addWidget(self.header)
        self.add_request_feedback(self.main_layout)

        self.statistics_content = QWidget()
        self.statistics_content.setObjectName("statisticsContent")
        self.statistics_content.setProperty("uiSurface", "transparent")
        self.statistics_content.setAccessibleName("Nội dung thống kê quản trị")
        content_layout = QVBoxLayout(self.statistics_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # ------------------- Stat Cards Grid -------------------
        self.cards_layout = QGridLayout()
        self.cards_layout.setHorizontalSpacing(14)
        self.cards_layout.setVerticalSpacing(14)
        content_layout.addLayout(self.cards_layout)
        self._stat_cards: list[ModernStatCard] = []

        # ------------------- 2 Sub Tables -------------------
        # Tables are placed in a grid that reflows from two-column to one-column
        # at narrow widths.  Each card is a top-level widget so the grid can
        # reposition them without reparenting.
        self._dist_grid = QGridLayout()
        self._dist_grid.setHorizontalSpacing(16)
        self._dist_grid.setVerticalSpacing(16)

        # Table 1: Doctors by Specialty
        card_sp = QFrame()
        card_sp.setObjectName("contentCard")
        layout_sp = QVBoxLayout(card_sp)
        layout_sp.setContentsMargins(20, 18, 20, 18)
        layout_sp.setSpacing(12)

        lbl_sp = QLabel("Phân bổ bác sĩ theo chuyên khoa")
        lbl_sp.setObjectName("sectionTitle")
        layout_sp.addWidget(lbl_sp)

        self.specialty_table = AdaptiveDataTable(
            (
                ColumnSpec(
                    "Chuyên khoa",
                    "name",
                    minimum_width=180,
                    preferred_width=280,
                    maximum_width=520,
                    grow_weight=1,
                    line_limit=2,
                    wrap=True,
                ),
                ColumnSpec(
                    "Số bác sĩ",
                    "count",
                    minimum_width=100,
                    preferred_width=112,
                    maximum_width=128,
                    priority=int(ColumnPriority.CRITICAL),
                    preserve_full=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
            ),
            accessible_name="Phân bổ bác sĩ theo chuyên khoa",
        )
        layout_sp.addWidget(self.specialty_table)
        self._dist_grid.addWidget(card_sp, 0, 0)

        # Table 2: Doctors by Clinic
        card_cl = QFrame()
        card_cl.setObjectName("contentCard")
        layout_cl = QVBoxLayout(card_cl)
        layout_cl.setContentsMargins(20, 18, 20, 18)
        layout_cl.setSpacing(12)

        lbl_cl = QLabel("Phân bổ bác sĩ theo phòng khám")
        lbl_cl.setObjectName("sectionTitle")
        layout_cl.addWidget(lbl_cl)

        self.clinic_table = AdaptiveDataTable(
            (
                ColumnSpec(
                    "Phòng khám",
                    "name",
                    minimum_width=180,
                    preferred_width=280,
                    maximum_width=520,
                    grow_weight=1,
                    line_limit=2,
                    wrap=True,
                    display_mode=ColumnDisplayMode.WRAP_2,
                ),
                ColumnSpec(
                    "Số bác sĩ",
                    "count",
                    minimum_width=100,
                    preferred_width=112,
                    maximum_width=128,
                    priority=int(ColumnPriority.CRITICAL),
                    preserve_full=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
            ),
            accessible_name="Phân bổ bác sĩ theo phòng khám",
        )
        layout_cl.addWidget(self.clinic_table)
        self._dist_grid.addWidget(card_cl, 0, 1)

        content_layout.addLayout(self._dist_grid, 1)

        self.statistics_state = self.bind_state_host(
            self.statistics_content,
            self.load_data,
            empty_title="Chưa có dữ liệu thống kê",
            empty_description="Số liệu tổng quan sẽ xuất hiện sau khi hệ thống có dữ liệu hoạt động.",
            empty_action_text="Tải lại",
            on_empty_action=self.load_data,
        )
        self.main_layout.addWidget(self.statistics_state, 1)

    def load_data(self, *, clear_feedback: bool = True):
        return self.run_admin_task(
            "load-statistics",
            lambda: require_success(
                api_client.get("/statistics/overview"),
                "Không thể tải số liệu thống kê.",
            ).json(),
            self._populate_statistics,
            loading_text="Đang tải số liệu thống kê…",
            clear_feedback=clear_feedback,
            stateful=True,
            empty_when=self._statistics_are_empty,
        )

    @staticmethod
    def _statistics_are_empty(data) -> bool:
        total_keys = (
            "total_users",
            "total_doctors",
            "total_clinics",
            "total_specialties",
            "total_schedules",
            "total_appointments",
            "completed_appointments",
            "paid_revenue",
        )
        return not any(data.get(key, 0) for key in total_keys) and not any(
            data.get(key) for key in ("doctors_by_specialty", "doctors_by_clinic")
        )

    def _populate_statistics(self, d):

        cards_data = [
            ("Tổng tài khoản", d.get("total_users", 0), "#0284c7"),
            ("Bác sĩ đang hoạt động", d.get("total_doctors", 0), "#0f766e"),
            ("Phòng khám đang hoạt động", d.get("total_clinics", 0), "#d97706"),
            ("Chuyên khoa đang hoạt động", d.get("total_specialties", 0), "#7c3aed"),
            ("Lịch trực đang mở", d.get("total_schedules", 0), "#059669"),
            ("Lượt hẹn", d.get("total_appointments", 0), "#0369a1"),
            ("Đã khám", d.get("completed_appointments", 0), "#0f766e"),
            ("Đã thu", format_money(d.get("paid_revenue", 0)), "#047857"),
        ]

        if not self._stat_cards:
            for title, value, color in cards_data:
                card = ModernStatCard(title, value, color)
                card.setMinimumWidth(0)
                # ModernStatCard intentionally keeps a compact default.  Admin
                # can display longer Vietnamese labels, so allow those labels
                # to wrap instead of painting beneath the neighbouring card.
                card._title_label.setWordWrap(True)
                card._title_label.setMinimumWidth(0)
                self._stat_cards.append(card)
        else:
            for card, (title, value, _color) in zip(self._stat_cards, cards_data, strict=True):
                card.set_title(title)
                card.set_value(value)

        for card, (title, value, _color) in zip(self._stat_cards, cards_data, strict=True):
            card.setToolTip(f"{title}: {value}")
        self._relayout_cards()

        # Populate specialty table
        doc_sp = d.get("doctors_by_specialty", [])
        self.specialty_table.set_rows(doc_sp)

        # Populate clinic table
        doc_cl = d.get("doctors_by_clinic", [])
        self.clinic_table.set_rows(doc_cl)

    def _card_column_count(self) -> int:
        width = self.width()
        if width >= 1320:
            return 4
        if width >= 1040:
            return 3
        return 2

    def _relayout_cards(self) -> None:
        if not self._stat_cards:
            return

        columns = self._card_column_count()
        # QGridLayout retains a layout item when the same widget is added at a
        # new position.  Remove the items first so repeated resize events never
        # leave blank cells or duplicate cards behind.
        while self.cards_layout.count():
            self.cards_layout.takeAt(0)
        for column in range(8):
            self.cards_layout.setColumnStretch(column, 1 if column < columns else 0)
        for index, card in enumerate(self._stat_cards):
            self.cards_layout.addWidget(card, index // columns, index % columns)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._relayout_cards()
        self._relayout_dist_tables()

    def _relayout_dist_tables(self) -> None:
        """Stack distribution tables in two columns or one depending on width."""
        wide = self.width() >= 900
        card_sp = self._dist_grid.itemAtPosition(0, 0)
        card_cl = self._dist_grid.itemAtPosition(0, 1) or self._dist_grid.itemAtPosition(1, 0)
        if card_sp is None or card_cl is None:
            return
        card_sp.widget()
        w_cl = card_cl.widget()
        if wide:
            # Two-column layout
            if self._dist_grid.itemAtPosition(0, 1) is None:
                self._dist_grid.removeWidget(w_cl)
                self._dist_grid.addWidget(w_cl, 0, 1)
            self._dist_grid.setColumnStretch(0, 1)
            self._dist_grid.setColumnStretch(1, 1)
        else:
            # Single-column stacked layout
            if self._dist_grid.itemAtPosition(1, 0) is None:
                self._dist_grid.removeWidget(w_cl)
                self._dist_grid.addWidget(w_cl, 1, 0)
            self._dist_grid.setColumnStretch(0, 1)
            self._dist_grid.setColumnStretch(1, 0)
