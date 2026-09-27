"""Modern, clean User Management page for Admin."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
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
from frontend.widgets.feedback_banner import FeedbackBanner
from frontend.widgets.page_header import PageHeader
from frontend.widgets.status_badge import STATUS_LABELS_VN, StatusBadgeDelegate


class UserManagementPage(AdminApiPage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # ------------------- Page Header -------------------
        self.header = PageHeader(
            "Tài khoản",
            "Quản trị danh sách và phân quyền",
        )
        layout.addWidget(self.header)
        self.add_request_feedback(layout)

        # ------------------- Create Form Card -------------------
        form_card = QFrame()
        form_card.setObjectName("contentCard")
        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(20, 18, 20, 18)
        form_card_layout.setSpacing(14)

        form_title = QLabel("Thêm tài khoản")
        form_title.setObjectName("sectionTitle")
        form_card_layout.addWidget(form_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)

        # Username
        col_u = QVBoxLayout()
        col_u.setSpacing(5)
        lbl_u = QLabel("Tên đăng nhập")
        lbl_u.setObjectName("fieldLabel")
        self.username_input = QLineEdit()
        col_u.addWidget(lbl_u)
        col_u.addWidget(self.username_input)
        grid.addLayout(col_u, 0, 0)

        # Fullname
        col_fn = QVBoxLayout()
        col_fn.setSpacing(5)
        lbl_fn = QLabel("Họ và tên")
        lbl_fn.setObjectName("fieldLabel")
        self.fullname_input = QLineEdit()
        col_fn.addWidget(lbl_fn)
        col_fn.addWidget(self.fullname_input)
        grid.addLayout(col_fn, 0, 1)

        # Password
        col_p = QVBoxLayout()
        col_p.setSpacing(5)
        lbl_p = QLabel("Mật khẩu")
        lbl_p.setObjectName("fieldLabel")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        col_p.addWidget(lbl_p)
        col_p.addWidget(self.password_input)
        grid.addLayout(col_p, 0, 2)

        # Role
        col_r = QVBoxLayout()
        col_r.setSpacing(5)
        lbl_r = QLabel("Vai trò")
        lbl_r.setObjectName("fieldLabel")
        self.role_input = QComboBox()
        self.role_input.addItem("Bệnh nhân", "PATIENT")
        self.role_input.addItem("Bác sĩ", "DOCTOR")
        self.role_input.addItem("Nhân viên", "STAFF")
        self.role_input.addItem("Quản trị viên", "ADMIN")
        col_r.addWidget(lbl_r)
        col_r.addWidget(self.role_input)
        grid.addLayout(col_r, 0, 3)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.add_btn = QPushButton("Thêm mới")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setMinimumHeight(36)
        self.add_btn.setMinimumWidth(120)
        self.add_btn.setAccessibleName("Thêm tài khoản mới")
        self.add_btn.clicked.connect(self.add_user)
        btn_layout.addWidget(self.add_btn)

        form_card_layout.addLayout(grid)
        form_card_layout.addLayout(btn_layout)
        layout.addWidget(form_card)

        # ------------------- Data Table Card -------------------
        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card.setAccessibleName("Nội dung danh sách tài khoản")
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(20, 18, 20, 18)
        table_card_layout.setSpacing(12)

        table_title = QLabel("Danh sách tài khoản")
        table_title.setObjectName("sectionTitle")
        table_card_layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Tên đăng nhập", "Họ và tên", "Vai trò", "Trạng thái", "Thao tác"]
        )
        configure_admin_table(
            self.table,
            accessible_name="Danh sách tài khoản",
            stretch_column=2,
            fixed_widths={0: 54, 1: 150, 3: 112, 4: 118, 5: 160},
        )
        self.table.setItemDelegateForColumn(4, StatusBadgeDelegate(self.table))

        table_card_layout.addWidget(self.table)
        self.table_state = self.bind_state_host(
            table_card,
            self.load_data,
            empty_title="Chưa có tài khoản",
            empty_description="Tạo tài khoản đầu tiên để bắt đầu phân quyền người dùng.",
            empty_action_text="Thêm tài khoản",
            on_empty_action=self.username_input.setFocus,
        )
        layout.addWidget(self.table_state, 1)

        self.load_data()

    def load_data(self, *, clear_feedback: bool = True):
        return self.run_admin_task(
            "load-users",
            lambda: require_success(
                api_client.get("/users/"),
                "Không thể tải danh sách tài khoản.",
            ).json(),
            self._populate_users,
            loading_text="Đang tải danh sách tài khoản…",
            clear_feedback=clear_feedback,
            stateful=True,
            empty_when=lambda users: not users,
        )

    def _populate_users(self, users):
        self.table.clearContents()
        self.table.setRowCount(len(users))
        for row, u in enumerate(users):
            item_id = table_item(u["UserID"], alignment=Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            item_user = table_item(u["Username"])
            self.table.setItem(row, 1, item_user)

            item_name = table_item(u["FullName"])
            self.table.setItem(row, 2, item_name)

            # Role pill (rendered via delegate)
            role_code = u["Role"]
            role_label = STATUS_LABELS_VN.get(role_code, role_code)
            item_role = table_item(role_label, alignment=Qt.AlignCenter)
            self.table.setItem(row, 3, item_role)

            # Status pill (rendered via delegate)
            is_active = u["IsActive"]
            status_text = "ACTIVE" if is_active else "INACTIVE"
            status_label = STATUS_LABELS_VN[status_text]
            item_status = table_item(
                status_text,
                alignment=Qt.AlignCenter,
                tooltip=status_label,
                accessible_text=status_label,
            )
            self.table.setItem(row, 4, item_status)

            # Action buttons
            edit_btn = QPushButton("Sửa")
            edit_btn.setObjectName("actionEditBtn")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setFixedSize(56, 34)
            edit_btn.setAccessibleName(f"Sửa tài khoản {u['Username']}")
            edit_btn.setToolTip(edit_btn.accessibleName())
            edit_btn.clicked.connect(
                lambda _, uid=u["UserID"], un=u["Username"], fn=u["FullName"]: self.open_edit_dialog(
                    uid, un, fn
                )
            )

            del_btn = QPushButton("Khóa" if is_active else "Mở khóa")
            del_btn.setObjectName("actionDeleteBtn")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedSize(76, 34)
            del_btn.setAccessibleName(
                f"{'Khóa' if is_active else 'Mở khóa'} tài khoản {u['Username']}"
            )
            del_btn.setToolTip(del_btn.accessibleName())
            del_btn.clicked.connect(
                lambda _, uid=u["UserID"], button=del_btn: self.delete_user(uid, button)
            )

            actions_widget = action_cell(
                edit_btn,
                del_btn,
                accessible_name=f"Thao tác cho tài khoản {u['Username']}",
            )

            self.table.setCellWidget(row, 5, actions_widget)
            self.table.setRowHeight(row, 48)

    def add_user(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên đăng nhập và mật khẩu.")
            return

        payload = {
            "Username": username,
            "FullName": self.fullname_input.text().strip(),
            "Password": password,
            "Role": self.role_input.currentData() or self.role_input.currentText(),
        }
        self.run_admin_task(
            "create-user",
            lambda: require_success(
                api_client.post("/users/", json=payload),
                "Không thể tạo tài khoản.",
            ),
            self._user_created,
            controls=(self.add_btn,),
            loading_text="Đang tạo tài khoản…",
        )

    def _user_created(self, _response):
        self.feedback.show_message(
            "Đã tạo tài khoản",
            "Tài khoản mới đã được lưu thành công.",
            severity="success",
        )
        self.load_data(clear_feedback=False)
        self.username_input.clear()
        self.fullname_input.clear()
        self.password_input.clear()

    def open_edit_dialog(self, user_id, username, fullname):
        dialog = QDialog(self)
        dialog.setWindowTitle("Chỉnh sửa thông tin tài khoản")
        dialog.setFixedWidth(360)

        form = QFormLayout(dialog)
        form.setContentsMargins(24, 24, 24, 24)
        form.setSpacing(14)

        dlg_title = QLabel("Cập nhật tài khoản")
        dlg_title.setObjectName("sectionTitle")
        form.addRow(dlg_title)
        dialog_feedback = FeedbackBanner(dialog)
        form.addRow(dialog_feedback)

        username_edit = QLineEdit(username)
        username_edit.setAccessibleName("Tên đăng nhập")
        fullname_edit = QLineEdit(fullname)
        fullname_edit.setAccessibleName("Họ và tên")
        form.addRow("Tên đăng nhập:", username_edit)
        form.addRow("Họ và tên:", fullname_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_button = buttons.button(QDialogButtonBox.Save)
        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        save_button.setText("Lưu")
        cancel_button.setText("Hủy")
        form.addRow(buttons)

        def save():
            dialog_feedback.clear()
            payload = {
                "Username": username_edit.text().strip(),
                "FullName": fullname_edit.text().strip(),
            }
            self.run_admin_task(
                f"update-user:{user_id}",
                lambda: require_success(
                    api_client.put(f"/users/{user_id}", json=payload),
                    "Không thể cập nhật tài khoản.",
                ),
                lambda _response: self._user_updated(dialog),
                controls=(save_button, cancel_button, username_edit, fullname_edit),
                loading_text="Đang cập nhật tài khoản…",
                on_error=lambda error: dialog_feedback.show_message(
                    "Không thể cập nhật tài khoản",
                    self.error_message(error),
                    severity="error",
                ),
            )

        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def _user_updated(self, dialog: QDialog) -> None:
        dialog.accept()
        self.feedback.show_message(
            "Đã cập nhật",
            "Thông tin tài khoản đã được lưu.",
            severity="success",
        )
        self.load_data(clear_feedback=False)

    def delete_user(self, user_id, button: QPushButton | None = None):
        if QMessageBox.question(self, "Xác nhận", "Bạn có chắc chắn muốn thay đổi trạng thái tài khoản này?") == QMessageBox.Yes:
            controls = (button,) if button is not None else ()
            self.run_admin_task(
                f"toggle-user:{user_id}",
                lambda: require_success(
                    api_client.delete(f"/users/{user_id}"),
                    "Không thể thay đổi trạng thái tài khoản.",
                ),
                self._user_toggled,
                controls=controls,
                loading_text="Đang cập nhật trạng thái tài khoản…",
            )

    def _user_toggled(self, _response) -> None:
        self.feedback.show_message(
            "Đã cập nhật",
            "Trạng thái tài khoản đã được thay đổi.",
            severity="success",
        )
        self.load_data(clear_feedback=False)
