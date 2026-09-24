"""Modern, clean Clinic Management page for Admin."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
from frontend.widgets.page_header import PageHeader
from frontend.widgets.status_badge import StatusBadgeDelegate


class ClinicManagementPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # ------------------- Header -------------------
        self.header = PageHeader(
            "Quản lý phòng khám",
            "Danh mục các cơ sở phòng khám",
        )
        layout.addWidget(self.header)

        # ------------------- Create Form Card -------------------
        form_card = QFrame()
        form_card.setObjectName("contentCard")
        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(20, 16, 20, 18)
        form_card_layout.setSpacing(12)

        form_title = QLabel("Thêm phòng khám mới")
        form_title.setObjectName("sectionTitle")
        form_card_layout.addWidget(form_title)

        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(12)

        # Clinic Name
        col_n = QVBoxLayout()
        col_n.setSpacing(4)
        lbl_n = QLabel("Tên phòng khám")
        lbl_n.setObjectName("fieldLabel")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("VD: Phòng khám Nội 1")
        col_n.addWidget(lbl_n)
        col_n.addWidget(self.name_input)
        inputs_layout.addLayout(col_n, 3)

        # Address
        col_a = QVBoxLayout()
        col_a.setSpacing(4)
        lbl_a = QLabel("Địa chỉ")
        lbl_a.setObjectName("fieldLabel")
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("VD: Tầng 2, Tòa nhà A")
        col_a.addWidget(lbl_a)
        col_a.addWidget(self.address_input)
        inputs_layout.addLayout(col_a, 4)

        # Phone
        col_p = QVBoxLayout()
        col_p.setSpacing(4)
        lbl_p = QLabel("Số điện thoại")
        lbl_p.setObjectName("fieldLabel")
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("VD: 028 1234 5678")
        col_p.addWidget(lbl_p)
        col_p.addWidget(self.phone_input)
        inputs_layout.addLayout(col_p, 2)

        # Button
        col_btn = QVBoxLayout()
        col_btn.setSpacing(4)
        lbl_space = QLabel(" ")
        lbl_space.setObjectName("fieldLabel")
        add_btn = QPushButton("Thêm phòng khám")
        add_btn.setObjectName("primaryButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.add_clinic)
        col_btn.addWidget(lbl_space)
        col_btn.addWidget(add_btn)
        inputs_layout.addLayout(col_btn, 2)

        form_card_layout.addLayout(inputs_layout)
        layout.addWidget(form_card)

        # ------------------- Table Card -------------------
        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(16, 16, 16, 16)
        table_card_layout.setSpacing(10)

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
        self.table.setItemDelegateForColumn(4, StatusBadgeDelegate(self.table))

        table_card_layout.addWidget(self.table)
        layout.addWidget(table_card, 1)

        self.load_data()

    def load_data(self):
        r = api_client.get("/clinics/")
        if r.status_code != 200:
            return
        items = r.json()
        self.table.clearContents()
        self.table.setRowCount(len(items))
        for row, c in enumerate(items):
            item_id = QTableWidgetItem(str(c["ClinicID"]))
            item_id.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            self.table.setItem(row, 1, QTableWidgetItem(c["ClinicName"]))
            self.table.setItem(row, 2, QTableWidgetItem(c.get("Address") or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(c.get("Phone") or "—"))

            # Status pill (rendered via delegate)
            is_active = c["IsActive"]
            status_text = "Hoạt động" if is_active else "Đã khóa"
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, item_status)

            # Action button
            del_btn = QPushButton("Khóa" if is_active else "Mở khóa")
            del_btn.setObjectName("actionDeleteBtn")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedSize(68, 28)
            del_btn.clicked.connect(lambda _, cid=c["ClinicID"]: self.delete_item(cid))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(6, 0, 6, 0)
            actions_layout.setAlignment(Qt.AlignCenter)
            actions_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 5, actions_widget)
            self.table.setRowHeight(row, 44)

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
        r = api_client.post("/clinics/", json=payload)
        if r.status_code == 200:
            self.load_data()
            self.name_input.clear()
            self.address_input.clear()
            self.phone_input.clear()
        else:
            QMessageBox.warning(self, "Lỗi", r.json().get("detail", "Không thể thêm phòng khám."))

    def delete_item(self, clinic_id):
        if QMessageBox.question(self, "Xác nhận", "Bạn có chắc chắn muốn thay đổi trạng thái phòng khám này?") == QMessageBox.Yes:
            api_client.delete(f"/clinics/{clinic_id}")
            self.load_data()