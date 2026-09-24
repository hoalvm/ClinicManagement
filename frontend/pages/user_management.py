"""Modern, clean User Management page for Admin."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from frontend.api_client import api_client


class UserManagementPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # ------------------- Page Header -------------------
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title_label = QLabel("Quản lý tài khoản")
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel(
            "Tạo mới, chỉnh sửa thông tin và quản lý trạng thái tài khoản người dùng"
        )
        subtitle_label.setObjectName("pageSubtitle")
        header_box.addWidget(title_label)
        header_box.addWidget(subtitle_label)
        layout.addLayout(header_box)

        # ------------------- Create Form Card -------------------
        form_card = QFrame()
        form_card.setObjectName("contentCard")
        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(20, 16, 20, 18)
        form_card_layout.setSpacing(12)

        form_title = QLabel("Thêm tài khoản mới")
        form_title.setObjectName("sectionTitle")
        form_card_layout.addWidget(form_title)

        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(12)

        # Username
        col_u = QVBoxLayout()
        col_u.setSpacing(4)
        lbl_u = QLabel("Tên đăng nhập")
        lbl_u.setObjectName("fieldLabel")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("VD: nguyenvana")
        col_u.addWidget(lbl_u)
        col_u.addWidget(self.username_input)
        inputs_layout.addLayout(col_u, 2)

        # Fullname
        col_fn = QVBoxLayout()
        col_fn.setSpacing(4)
        lbl_fn = QLabel("Họ và tên")
        lbl_fn.setObjectName("fieldLabel")
        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("VD: Nguyễn Văn A")
        col_fn.addWidget(lbl_fn)
        col_fn.addWidget(self.fullname_input)
        inputs_layout.addLayout(col_fn, 3)

        # Password
        col_p = QVBoxLayout()
        col_p.setSpacing(4)
        lbl_p = QLabel("Mật khẩu")
        lbl_p.setObjectName("fieldLabel")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("••••••••")
        col_p.addWidget(lbl_p)
        col_p.addWidget(self.password_input)
        inputs_layout.addLayout(col_p, 2)

        # Role
        col_r = QVBoxLayout()
        col_r.setSpacing(4)
        lbl_r = QLabel("Vai trò")
        lbl_r.setObjectName("fieldLabel")
        self.role_input = QComboBox()
        self.role_input.addItems(["PATIENT", "DOCTOR", "STAFF", "ADMIN"])
        col_r.addWidget(lbl_r)
        col_r.addWidget(self.role_input)
        inputs_layout.addLayout(col_r, 2)

        # Add button
        col_btn = QVBoxLayout()
        col_btn.setSpacing(4)
        lbl_space = QLabel(" ")
        lbl_space.setObjectName("fieldLabel")
        add_btn = QPushButton("Thêm tài khoản")
        add_btn.setObjectName("primaryButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.add_user)
        col_btn.addWidget(lbl_space)
        col_btn.addWidget(add_btn)
        inputs_layout.addLayout(col_btn, 2)

        form_card_layout.addLayout(inputs_layout)
        layout.addWidget(form_card)

        # ------------------- Data Table Card -------------------
        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(16, 16, 16, 16)
        table_card_layout.setSpacing(10)

        table_title = QLabel("Danh sách tài khoản")
        table_title.setObjectName("sectionTitle")
        table_card_layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Tên đăng nhập", "Họ và tên", "Vai trò", "Trạng thái", "Thao tác"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        header = self.table.horizontalHeader()
        header.setFixedHeight(38)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        table_card_layout.addWidget(self.table)
        layout.addWidget(table_card, 1)

        self.load_data()

    def load_data(self):
        r = api_client.get("/users/")
        if r.status_code != 200:
            return
        users = r.json()
        self.table.clearContents()
        self.table.setRowCount(len(users))
        for row, u in enumerate(users):
            item_id = QTableWidgetItem(str(u["UserID"]))
            item_id.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            item_user = QTableWidgetItem(u["Username"])
            self.table.setItem(row, 1, item_user)

            item_name = QTableWidgetItem(u["FullName"])
            self.table.setItem(row, 2, item_name)

            # Role pill
            role_widget = QLabel(u["Role"])
            role_widget.setAlignment(Qt.AlignCenter)
            role_widget.setStyleSheet(
                "background-color: #f1f5f9; color: #334155; border-radius: 4px; "
                "font-size: 11px; font-weight: 600; padding: 2px 6px;"
            )
            self.table.setCellWidget(row, 3, role_widget)

            # Status pill
            is_active = u["IsActive"]
            status_lbl = QLabel("Hoạt động" if is_active else "Đã khóa")
            status_lbl.setAlignment(Qt.AlignCenter)
            if is_active:
                status_lbl.setStyleSheet(
                    "background-color: #dcfce7; color: #15803d; border-radius: 4px; "
                    "font-size: 11px; font-weight: 600; padding: 2px 6px;"
                )
            else:
                status_lbl.setStyleSheet(
                    "background-color: #fee2e2; color: #b91c1c; border-radius: 4px; "
                    "font-size: 11px; font-weight: 600; padding: 2px 6px;"
                )
            self.table.setCellWidget(row, 4, status_lbl)

            # Action buttons
            edit_btn = QPushButton("Sửa")
            edit_btn.setObjectName("actionEditBtn")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setFixedSize(54, 28)
            edit_btn.clicked.connect(
                lambda _, uid=u["UserID"], un=u["Username"], fn=u["FullName"]: self.open_edit_dialog(
                    uid, un, fn
                )
            )

            del_btn = QPushButton("Khóa" if is_active else "Mở khóa")
            del_btn.setObjectName("actionDeleteBtn")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedSize(68, 28)
            del_btn.clicked.connect(lambda _, uid=u["UserID"]: self.delete_user(uid))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(6, 0, 6, 0)
            actions_layout.setSpacing(6)
            actions_layout.setAlignment(Qt.AlignCenter)
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 5, actions_widget)
            self.table.setRowHeight(row, 44)

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
            "Role": self.role_input.currentText(),
        }
        r = api_client.post("/users/", json=payload)
        if r.status_code == 200:
            self.load_data()
            self.username_input.clear()
            self.fullname_input.clear()
            self.password_input.clear()
        else:
            QMessageBox.warning(self, "Lỗi", r.json().get("detail", "Không thể tạo tài khoản."))

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

        username_edit = QLineEdit(username)
        fullname_edit = QLineEdit(fullname)
        form.addRow("Tên đăng nhập:", username_edit)
        form.addRow("Họ và tên:", fullname_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Lưu")
        buttons.button(QDialogButtonBox.Cancel).setText("Hủy")
        form.addRow(buttons)

        def save():
            payload = {
                "Username": username_edit.text().strip(),
                "FullName": fullname_edit.text().strip(),
            }
            r = api_client.put(f"/users/{user_id}", json=payload)
            if r.status_code == 200:
                dialog.accept()
                self.load_data()
            else:
                QMessageBox.warning(self, "Lỗi", r.json().get("detail", "Có lỗi xảy ra"))

        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def delete_user(self, user_id):
        if QMessageBox.question(self, "Xác nhận", "Bạn có chắc chắn muốn thay đổi trạng thái tài khoản này?") == QMessageBox.Yes:
            api_client.delete(f"/users/{user_id}")
            self.load_data()