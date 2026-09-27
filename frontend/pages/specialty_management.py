"""Modern, clean Specialty Management page for Admin."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)

from frontend.api_client import api_client
from frontend.pages.admin_ui import (
    AdminApiPage,
    action_cell,
    configure_admin_table,
    require_success,
    table_item,
)
from frontend.widgets.page_header import PageHeader
from frontend.widgets.status_badge import STATUS_LABELS_VN, StatusBadgeDelegate


class SpecialtyManagementPage(AdminApiPage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # ------------------- Header -------------------
        self.header = PageHeader(
            "Chuyên khoa",
            "Danh mục chuyên khoa y tế",
        )
        layout.addWidget(self.header)
        self.add_request_feedback(layout)

        # ------------------- Create Form Card -------------------
        form_card = QFrame()
        form_card.setObjectName("contentCard")
        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(20, 18, 20, 18)
        form_card_layout.setSpacing(14)

        form_title = QLabel("Thêm chuyên khoa")
        form_title.setObjectName("sectionTitle")
        form_card_layout.addWidget(form_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)

        # Name
        col_n = QVBoxLayout()
        col_n.setSpacing(5)
        lbl_n = QLabel("Tên chuyên khoa")
        lbl_n.setObjectName("fieldLabel")
        self.name_input = QLineEdit()
        col_n.addWidget(lbl_n)
        col_n.addWidget(self.name_input)
        grid.addLayout(col_n, 0, 0)

        # Description
        col_d = QVBoxLayout()
        col_d.setSpacing(5)
        lbl_d = QLabel("Mô tả")
        lbl_d.setObjectName("fieldLabel")
        self.desc_input = QLineEdit()
        col_d.addWidget(lbl_d)
        col_d.addWidget(self.desc_input)
        grid.addLayout(col_d, 0, 1)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.add_btn = QPushButton("Thêm mới")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setMinimumHeight(36)
        self.add_btn.setMinimumWidth(120)
        self.add_btn.setAccessibleName("Thêm chuyên khoa mới")
        self.add_btn.clicked.connect(self.add_specialty)
        btn_layout.addWidget(self.add_btn)

        form_card_layout.addLayout(grid)
        form_card_layout.addLayout(btn_layout)
        layout.addWidget(form_card)

        # ------------------- Table Card -------------------
        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card.setAccessibleName("Nội dung danh sách chuyên khoa")
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(20, 18, 20, 18)
        table_card_layout.setSpacing(12)

        table_title = QLabel("Danh sách chuyên khoa")
        table_title.setObjectName("sectionTitle")
        table_card_layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Tên chuyên khoa",
            "Mô tả",
            "Trạng thái",
            "Thao tác",
        ])
        configure_admin_table(
            self.table,
            accessible_name="Danh sách chuyên khoa",
            stretch_column=2,
            fixed_widths={0: 52, 1: 220, 3: 116, 4: 98},
        )
        self.table.setItemDelegateForColumn(3, StatusBadgeDelegate(self.table))

        table_card_layout.addWidget(self.table)
        self.table_state = self.bind_state_host(
            table_card,
            self.load_data,
            empty_title="Chưa có chuyên khoa",
            empty_description="Thêm chuyên khoa đầu tiên để phân loại dịch vụ và bác sĩ.",
            empty_action_text="Thêm chuyên khoa",
            on_empty_action=self.name_input.setFocus,
        )
        layout.addWidget(self.table_state, 1)

        self.load_data()

    def load_data(self, *, clear_feedback: bool = True):
        return self.run_admin_task(
            "load-specialties",
            lambda: require_success(
                api_client.get("/specialties/"),
                "Không thể tải danh sách chuyên khoa.",
            ).json(),
            self._populate_specialties,
            loading_text="Đang tải danh sách chuyên khoa…",
            clear_feedback=clear_feedback,
            stateful=True,
            empty_when=lambda specialties: not specialties,
        )

    def _populate_specialties(self, items):
        self.table.clearContents()
        self.table.setRowCount(len(items))
        for row, s in enumerate(items):
            item_id = table_item(s["SpecialtyID"], alignment=Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            self.table.setItem(row, 1, table_item(s["SpecialtyName"]))
            self.table.setItem(row, 2, table_item(s.get("Description")))

            # Status pill (rendered via delegate)
            is_active = s["IsActive"]
            status_text = "ACTIVE" if is_active else "INACTIVE"
            status_label = STATUS_LABELS_VN[status_text]
            item_status = table_item(
                status_text,
                alignment=Qt.AlignCenter,
                tooltip=status_label,
                accessible_text=status_label,
            )
            self.table.setItem(row, 3, item_status)

            # Action button
            del_btn = QPushButton("Khóa" if is_active else "Mở khóa")
            del_btn.setObjectName("actionDeleteBtn")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedSize(76, 34)
            del_btn.setAccessibleName(
                f"{'Khóa' if is_active else 'Mở khóa'} chuyên khoa {s['SpecialtyName']}"
            )
            del_btn.setToolTip(del_btn.accessibleName())
            del_btn.clicked.connect(
                lambda _, sid=s["SpecialtyID"], button=del_btn: self.delete_item(sid, button)
            )

            actions_widget = action_cell(
                del_btn,
                accessible_name=f"Thao tác cho chuyên khoa {s['SpecialtyName']}",
            )

            self.table.setCellWidget(row, 4, actions_widget)
            self.table.setRowHeight(row, 48)

    def add_specialty(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên chuyên khoa.")
            return

        payload = {"SpecialtyName": name, "Description": self.desc_input.text().strip()}
        self.run_admin_task(
            "create-specialty",
            lambda: require_success(
                api_client.post("/specialties/", json=payload),
                "Không thể thêm chuyên khoa.",
            ),
            self._specialty_created,
            controls=(self.add_btn,),
            loading_text="Đang thêm chuyên khoa…",
        )

    def _specialty_created(self, _response) -> None:
        self.name_input.clear()
        self.desc_input.clear()
        self.feedback.show_message(
            "Đã thêm chuyên khoa",
            "Thông tin chuyên khoa đã được lưu.",
            severity="success",
        )
        self.load_data(clear_feedback=False)

    def delete_item(self, specialty_id, button: QPushButton | None = None):
        if QMessageBox.question(self, "Xác nhận", "Bạn có chắc chắn muốn thay đổi trạng thái chuyên khoa này?") == QMessageBox.Yes:
            controls = (button,) if button is not None else ()
            self.run_admin_task(
                f"toggle-specialty:{specialty_id}",
                lambda: require_success(
                    api_client.delete(f"/specialties/{specialty_id}"),
                    "Không thể thay đổi trạng thái chuyên khoa.",
                ),
                self._specialty_toggled,
                controls=controls,
                loading_text="Đang cập nhật trạng thái chuyên khoa…",
            )

    def _specialty_toggled(self, _response) -> None:
        self.feedback.show_message(
            "Đã cập nhật",
            "Trạng thái chuyên khoa đã được thay đổi.",
            severity="success",
        )
        self.load_data(clear_feedback=False)
