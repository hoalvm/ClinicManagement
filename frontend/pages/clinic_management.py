"""Modern, clean Clinic Management page for Admin."""

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


class ClinicManagementPage(AdminApiPage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # ------------------- Header -------------------
        self.header = PageHeader(
            "Phòng khám",
            "Danh mục cơ sở y tế",
        )
        layout.addWidget(self.header)
        self.add_request_feedback(layout)

        # ------------------- Create Form Card -------------------
        form_card = QFrame()
        form_card.setObjectName("contentCard")
        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(20, 18, 20, 18)
        form_card_layout.setSpacing(14)

        form_title = QLabel("Thêm phòng khám")
        form_title.setObjectName("sectionTitle")
        form_card_layout.addWidget(form_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)

        # Clinic Name
        col_n = QVBoxLayout()
        col_n.setSpacing(5)
        lbl_n = QLabel("Tên phòng khám")
        lbl_n.setObjectName("fieldLabel")
        self.name_input = QLineEdit()
        col_n.addWidget(lbl_n)
        col_n.addWidget(self.name_input)
        grid.addLayout(col_n, 0, 0)

        # Address
        col_a = QVBoxLayout()
        col_a.setSpacing(5)
        lbl_a = QLabel("Địa chỉ")
        lbl_a.setObjectName("fieldLabel")
        self.address_input = QLineEdit()
        col_a.addWidget(lbl_a)
        col_a.addWidget(self.address_input)
        grid.addLayout(col_a, 0, 1)

        # Phone
        col_p = QVBoxLayout()
        col_p.setSpacing(5)
        lbl_p = QLabel("Số điện thoại")
        lbl_p.setObjectName("fieldLabel")
        self.phone_input = QLineEdit()
        col_p.addWidget(lbl_p)
        col_p.addWidget(self.phone_input)
        grid.addLayout(col_p, 0, 2)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.add_btn = QPushButton("Thêm mới")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setMinimumHeight(36)
        self.add_btn.setMinimumWidth(120)
        self.add_btn.setAccessibleName("Thêm phòng khám mới")
        self.add_btn.clicked.connect(self.add_clinic)
        btn_layout.addWidget(self.add_btn)

        form_card_layout.addLayout(grid)
        form_card_layout.addLayout(btn_layout)
        layout.addWidget(form_card)

        # ------------------- Table Card -------------------
        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card.setAccessibleName("Nội dung danh sách phòng khám")
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(20, 18, 20, 18)
        table_card_layout.setSpacing(12)

        table_title = QLabel("Danh sách phòng khám")
        table_title.setObjectName("sectionTitle")
        table_card_layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Tên phòng khám",
            "Địa chỉ",
            "Số điện thoại",
            "Trạng thái",
            "Thao tác",
        ])
        configure_admin_table(
            self.table,
            accessible_name="Danh sách phòng khám",
            stretch_column=2,
            fixed_widths={0: 52, 1: 190, 3: 128, 4: 116, 5: 98},
        )
        self.table.setItemDelegateForColumn(4, StatusBadgeDelegate(self.table))

        table_card_layout.addWidget(self.table)
        self.table_state = self.bind_state_host(
            table_card,
            self.load_data,
            empty_title="Chưa có phòng khám",
            empty_description="Thêm cơ sở khám đầu tiên để gán bác sĩ và lịch làm việc.",
            empty_action_text="Thêm phòng khám",
            on_empty_action=self.name_input.setFocus,
        )
        layout.addWidget(self.table_state, 1)

        self.load_data()

    def load_data(self, *, clear_feedback: bool = True):
        return self.run_admin_task(
            "load-clinics",
            lambda: require_success(
                api_client.get("/clinics/"),
                "Không thể tải danh sách phòng khám.",
            ).json(),
            self._populate_clinics,
            loading_text="Đang tải danh sách phòng khám…",
            clear_feedback=clear_feedback,
            stateful=True,
            empty_when=lambda clinics: not clinics,
        )

    def _populate_clinics(self, items):
        self.table.clearContents()
        self.table.setRowCount(len(items))
        for row, c in enumerate(items):
            item_id = table_item(c["ClinicID"], alignment=Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            self.table.setItem(row, 1, table_item(c["ClinicName"]))
            self.table.setItem(row, 2, table_item(c.get("Address")))
            self.table.setItem(row, 3, table_item(c.get("Phone")))

            # Status pill (rendered via delegate)
            is_active = c["IsActive"]
            status_text = "ACTIVE" if is_active else "INACTIVE"
            status_label = STATUS_LABELS_VN[status_text]
            item_status = table_item(
                status_text,
                alignment=Qt.AlignCenter,
                tooltip=status_label,
                accessible_text=status_label,
            )
            self.table.setItem(row, 4, item_status)

            # Action button
            del_btn = QPushButton("Khóa" if is_active else "Mở khóa")
            del_btn.setObjectName("actionDeleteBtn")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedSize(76, 34)
            del_btn.setAccessibleName(
                f"{'Khóa' if is_active else 'Mở khóa'} phòng khám {c['ClinicName']}"
            )
            del_btn.setToolTip(del_btn.accessibleName())
            del_btn.clicked.connect(
                lambda _, cid=c["ClinicID"], button=del_btn: self.delete_item(cid, button)
            )

            actions_widget = action_cell(
                del_btn,
                accessible_name=f"Thao tác cho phòng khám {c['ClinicName']}",
            )

            self.table.setCellWidget(row, 5, actions_widget)
            self.table.setRowHeight(row, 48)

    def add_clinic(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên phòng khám.")
            return

        payload = {
            "ClinicName": name,
            "Address": self.address_input.text().strip(),
            "Phone": self.phone_input.text().strip(),
        }
        self.run_admin_task(
            "create-clinic",
            lambda: require_success(
                api_client.post("/clinics/", json=payload),
                "Không thể thêm phòng khám.",
            ),
            self._clinic_created,
            controls=(self.add_btn,),
            loading_text="Đang thêm phòng khám…",
        )

    def _clinic_created(self, _response) -> None:
        self.name_input.clear()
        self.address_input.clear()
        self.phone_input.clear()
        self.feedback.show_message(
            "Đã thêm phòng khám",
            "Thông tin phòng khám đã được lưu.",
            severity="success",
        )
        self.load_data(clear_feedback=False)

    def delete_item(self, clinic_id, button: QPushButton | None = None):
        if QMessageBox.question(self, "Xác nhận", "Bạn có chắc chắn muốn thay đổi trạng thái phòng khám này?") == QMessageBox.Yes:
            controls = (button,) if button is not None else ()
            self.run_admin_task(
                f"toggle-clinic:{clinic_id}",
                lambda: require_success(
                    api_client.delete(f"/clinics/{clinic_id}"),
                    "Không thể thay đổi trạng thái phòng khám.",
                ),
                self._clinic_toggled,
                controls=controls,
                loading_text="Đang cập nhật trạng thái phòng khám…",
            )

    def _clinic_toggled(self, _response) -> None:
        self.feedback.show_message(
            "Đã cập nhật",
            "Trạng thái phòng khám đã được thay đổi.",
            severity="success",
        )
        self.load_data(clear_feedback=False)
