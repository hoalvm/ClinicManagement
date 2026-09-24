"""Modern, clean login window for ClinicManagement."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from frontend.api_client import api_client


class LoginWindow(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.setWindowTitle("Đăng nhập - Clinic Management")
        self.resize(440, 540)
        self.setMinimumSize(400, 500)

        # Center layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setAlignment(Qt.AlignCenter)

        # Card container
        card = QFrame()
        card.setObjectName("authCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(16)

        # Header branding
        tag_label = QLabel("HỆ THỐNG Y TẾ")
        tag_label.setStyleSheet(
            "color: #0f766e; font-size: 11px; font-weight: 700; letter-spacing: 1px;"
        )
        tag_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(tag_label)

        title_label = QLabel("Clinic Management")
        title_label.setStyleSheet("color: #0f172a; font-size: 22px; font-weight: 700;")
        title_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title_label)

        subtitle_label = QLabel("Đăng nhập để tiếp tục")
        subtitle_label.setStyleSheet("color: #64748b; font-size: 13px;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setWordWrap(True)
        card_layout.addWidget(subtitle_label)

        card_layout.addSpacing(8)

        # Inline error banner
        self.error_label = QLabel()
        self.error_label.setStyleSheet(
            "background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; "
            "border-radius: 6px; padding: 8px 12px; font-size: 12px; font-weight: 500;"
        )
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        card_layout.addWidget(self.error_label)

        # Username input
        user_box = QVBoxLayout()
        user_box.setSpacing(6)
        user_label = QLabel("Tên đăng nhập")
        user_label.setObjectName("fieldLabel")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nhập tên đăng nhập...")
        self.username_input.returnPressed.connect(self.handle_login)
        user_box.addWidget(user_label)
        user_box.addWidget(self.username_input)
        card_layout.addLayout(user_box)

        # Password input
        pwd_box = QVBoxLayout()
        pwd_box.setSpacing(6)
        pwd_label = QLabel("Mật khẩu")
        pwd_label.setObjectName("fieldLabel")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Nhập mật khẩu...")
        self.password_input.returnPressed.connect(self.handle_login)
        pwd_box.addWidget(pwd_label)
        pwd_box.addWidget(self.password_input)
        card_layout.addLayout(pwd_box)

        card_layout.addSpacing(6)

        # Login button
        self.login_btn = QPushButton("Đăng nhập")
        self.login_btn.setObjectName("primaryButton")
        self.login_btn.setMinimumHeight(40)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.handle_login)
        card_layout.addWidget(self.login_btn)

        # Helper note
        hint_label = QLabel("Tài khoản mẫu: admin / doctor01 / patient01")
        hint_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        hint_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(hint_label)

        main_layout.addWidget(card)

    def handle_login(self):
        self.error_label.setVisible(False)
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.error_label.setText("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")
            self.error_label.setVisible(True)
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Đang đăng nhập...")

        try:
            ok, err = api_client.login(username, password)
            if ok:
                self.on_success()
            else:
                self.error_label.setText(err or "Sai tài khoản hoặc mật khẩu.")
                self.error_label.setVisible(True)
                self.password_input.clear()
                self.password_input.setFocus()
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Đăng nhập")