"""Primary authenticated navigation."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget


class Sidebar(QFrame):
    navigation_requested = Signal(str)
    logout_requested = Signal()

    _ITEMS = (
        ("dashboard", "Dashboard"),
        ("profile", "My Profile"),
        ("appointments", "Appointments"),
        ("medical_history", "Medical History"),
        ("invoice_history", "Invoice History"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 20)
        layout.setSpacing(8)

        brand = QLabel("ClinicCare")
        brand.setObjectName("brandLabel")
        subtitle = QLabel("Patient Portal")
        subtitle.setObjectName("sidebarSubtitle")
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addSpacing(28)

        self._buttons: dict[str, QPushButton] = {}
        for route, label in self._ITEMS:
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.clicked.connect(
                lambda _checked=False, key=route: self.navigation_requested.emit(key)
            )
            layout.addWidget(button)
            self._buttons[route] = button

        layout.addStretch()
        logout = QPushButton("Logout")
        logout.setObjectName("logoutButton")
        logout.clicked.connect(self.logout_requested)
        layout.addWidget(logout)

    def set_active(self, route: str) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == route)
