"""Modern, clean Specialty Management page for Admin."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
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


class SpecialtyManagementPage(QWidget):
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

        # ------------------- Create Form Card -------------------
        form_card = QFrame()
        form_card.setObjectName("contentCard")
        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(20, 16, 20, 18)
        form_card_layout.setSpacing(12)

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
        add_btn = QPushButton("Thêm mới")
        add_btn.setObjectName("primaryButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setMinimumHeight(36)
        add_btn.setMinimumWidth(120)
        add_btn.clicked.connect(self.add_specialty)
        btn_layout.addWidget(add_btn)

        form_card_layout.addLayout(grid)
        form_card_layout.addLayout(btn_layout)
        layout.addWidget(form_card)

        # ------------------- Table Card -------------------
        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(16, 16, 16, 16)
        table_card_layout.setSpacing(10)

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
        self.table.setItemDelegateForColumn(3, StatusBadgeDelegate(self.table))

        table_card_layout.addWidget(self.table)
        layout.addWidget(table_card, 1)

        self.load_data()

    def load_data(self):
        r = api_client.get("/specialties/")
        if r.status_code != 200:
            return
        items = r.json()
        self.table.clearContents()
        self.table.setRowCount(len(items))
        for row, s in enumerate(items):
            item_id = QTableWidgetItem(str(s["SpecialtyID"]))
            item_id.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            self.table.setItem(row, 1, QTableWidgetItem(s["SpecialtyName"]))
            self.table.setItem(row, 2, QTableWidgetItem(s.get("Description") or "—"))

            # Status pill (rendered via delegate)
            is_active = s["IsActive"]
            status_text = "Hoạt động" if is_active else "Đã khóa"
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, item_status)

            # Action button
            del_btn = QPushButton("Khóa" if is_active else "Mở khóa")
            del_btn.setObjectName("actionDeleteBtn")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedSize(68, 28)
            del_btn.clicked.connect(lambda _, sid=s["SpecialtyID"]: self.delete_item(sid))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(6, 0, 6, 0)
            actions_layout.setAlignment(Qt.AlignCenter)
            actions_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 4, actions_widget)
            self.table.setRowHeight(row, 44)

    def add_specialty(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên chuyên khoa.")
            return

        payload = {"SpecialtyName": name, "Description": self.desc_input.text().strip()}
        r = api_client.post("/specialties/", json=payload)
        if r.status_code == 200:
            self.load_data()
            self.name_input.clear()
            self.desc_input.clear()
        else:
            QMessageBox.warning(self, "Lỗi", r.json().get("detail", "Không thể thêm chuyên khoa."))

    def delete_item(self, specialty_id):
        if QMessageBox.question(self, "Xác nhận", "Bạn có chắc chắn muốn thay đổi trạng thái chuyên khoa này?") == QMessageBox.Yes:
            r = api_client.delete(f"/specialties/{specialty_id}")
            if r.status_code != 200:
                QMessageBox.warning(self, "Lỗi", r.json().get("detail", "Không thể xóa."))
            self.load_data()