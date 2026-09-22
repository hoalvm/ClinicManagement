from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
from api_client import api_client

class LoginWindow(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.setWindowTitle("Đăng nhập - Clinic Management")
        self.resize(320, 220)

        layout = QVBoxLayout()

        title = QLabel("HỆ THỐNG QUẢN LÝ PHÒNG KHÁM")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        layout.addWidget(QLabel("Tên đăng nhập:"))
        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("Mật khẩu:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.handle_login)
        layout.addWidget(self.password_input)

        login_btn = QPushButton("Đăng nhập")
        login_btn.clicked.connect(self.handle_login)
        layout.addWidget(login_btn)

        self.setLayout(layout)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập đủ tên đăng nhập và mật khẩu")
            return

        ok, err = api_client.login(username, password)
        if ok:
            self.on_success()
        else:
            QMessageBox.warning(self, "Lỗi đăng nhập", err)