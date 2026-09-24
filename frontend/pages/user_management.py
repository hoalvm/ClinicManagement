from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                                 QPushButton, QLineEdit, QComboBox, QMessageBox, QLabel, QHeaderView,
                                 QDialog, QFormLayout, QDialogButtonBox)
from PySide6.QtCore import Qt
from frontend.api_client import api_client

class UserManagementPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title_label = QLabel("QUẢN LÝ TÀI KHOẢN")
        title_label.setStyleSheet("font-size: 20px; font-weight: 700; color: #1e293b;")
        layout.addWidget(title_label)

        form_layout = QHBoxLayout()
        self.username_input = QLineEdit(); self.username_input.setPlaceholderText("Username")
        self.fullname_input = QLineEdit(); self.fullname_input.setPlaceholderText("Họ tên")
        self.password_input = QLineEdit(); self.password_input.setPlaceholderText("Mật khẩu")
        self.role_input = QComboBox(); self.role_input.addItems(["PATIENT", "DOCTOR", "STAFF", "ADMIN"])
        add_btn = QPushButton("Thêm"); add_btn.clicked.connect(self.add_user)

        for w in [self.username_input, self.fullname_input, self.password_input, self.role_input, add_btn]:
            form_layout.addWidget(w)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Họ tên", "Role", "Trạng thái", "Xóa"])
        header = self.table.horizontalHeader()
        header.setFixedHeight(30)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        layout.addLayout(form_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.load_data()

    def load_data(self):
        r = api_client.get("/users/")
        if r.status_code != 200:
            return
        users = r.json()
        self.table.setRowCount(len(users))
        for row, u in enumerate(users):
            self.table.setItem(row, 0, QTableWidgetItem(str(u["UserID"])))
            self.table.setItem(row, 1, QTableWidgetItem(u["Username"]))
            self.table.setItem(row, 2, QTableWidgetItem(u["FullName"]))
            self.table.setItem(row, 3, QTableWidgetItem(u["Role"]))
            self.table.setItem(row, 4, QTableWidgetItem("Hoạt động" if u["IsActive"] else "Đã khóa"))
            del_btn = QPushButton("Xóa")
            del_btn.setFixedSize(56, 26)
            del_btn.setFocusPolicy(Qt.NoFocus)
            del_btn.clicked.connect(lambda _, uid=u["UserID"]: self.delete_user(uid))

            edit_btn = QPushButton("Sửa")
            edit_btn.setFixedSize(56, 26)
            edit_btn.setFocusPolicy(Qt.NoFocus)
            edit_btn.setStyleSheet("background-color:#dbeafe; color:#2563eb;")
            edit_btn.clicked.connect(lambda _, uid=u["UserID"], un=u["Username"], fn=u["FullName"]: self.open_edit_dialog(uid, un, fn))

            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.addWidget(edit_btn)
            cell_layout.addWidget(del_btn)
            cell_layout.setAlignment(Qt.AlignCenter)
            cell_layout.setContentsMargins(4, 0, 4, 0)
            cell_layout.setSpacing(6)

            self.table.setCellWidget(row, 5, cell_widget)
            self.table.setRowHeight(row, 42)
    def add_user(self):
        if not self.username_input.text().strip() or not self.password_input.text():
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập Username và mật khẩu")
            return
        payload = {
            "Username": self.username_input.text().strip(),
            "FullName": self.fullname_input.text(),
            "Password": self.password_input.text(),
            "Role": self.role_input.currentText(),
        }
        r = api_client.post("/users/", json=payload)
        if r.status_code == 200:
            self.load_data()
            self.username_input.clear(); self.fullname_input.clear(); self.password_input.clear()
        else:
            QMessageBox.warning(self, "Lỗi", r.json().get("detail", "Có lỗi xảy ra"))

    def open_edit_dialog(self, user_id, username, fullname):
        dialog = QDialog(self)
        dialog.setWindowTitle("Sửa thông tin tài khoản")
        dialog.setFixedWidth(320)

        form = QFormLayout(dialog)
        username_edit = QLineEdit(username)
        fullname_edit = QLineEdit(fullname)
        form.addRow("Username:", username_edit)
        form.addRow("Họ tên:", fullname_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
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
        if QMessageBox.question(self, "Xác nhận", "Khóa tài khoản này?") == QMessageBox.Yes:
            api_client.delete(f"/users/{user_id}")
            self.load_data()