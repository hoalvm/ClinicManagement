from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                                 QPushButton, QLineEdit, QMessageBox, QLabel, QHeaderView)
from frontend.api_client import api_client

class SpecialtyManagementPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title_label = QLabel("QUẢN LÝ CHUYÊN KHOA")
        title_label.setStyleSheet("font-size: 20px; font-weight: 700; color: #1e293b;")
        layout.addWidget(title_label)

        form_layout = QHBoxLayout()
        self.name_input = QLineEdit(); self.name_input.setPlaceholderText("Tên chuyên khoa")
        self.desc_input = QLineEdit(); self.desc_input.setPlaceholderText("Mô tả")
        add_btn = QPushButton("Thêm"); add_btn.clicked.connect(self.add_specialty)
        for w in [self.name_input, self.desc_input, add_btn]:
            form_layout.addWidget(w)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Tên chuyên khoa", "Trạng thái", "Xóa"])
        header = self.table.horizontalHeader()
        header.setFixedHeight(30)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        layout.addLayout(form_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.load_data()

    def load_data(self):
        r = api_client.get("/specialties/")
        if r.status_code != 200:
            return
        items = r.json()
        self.table.setRowCount(len(items))
        for row, s in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(str(s["SpecialtyID"])))
            self.table.setItem(row, 1, QTableWidgetItem(s["SpecialtyName"]))
            self.table.setItem(row, 2, QTableWidgetItem("Hoạt động" if s["IsActive"] else "Đã khóa"))
            del_btn = QPushButton("Xóa")
            del_btn.clicked.connect(lambda _, sid=s["SpecialtyID"]: self.delete_item(sid))
            self.table.setCellWidget(row, 3, del_btn)

    def add_specialty(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên chuyên khoa")
            return
        payload = {"SpecialtyName": name, "Description": self.desc_input.text()}
        r = api_client.post("/specialties/", json=payload)
        if r.status_code == 200:
            self.load_data()
            self.name_input.clear(); self.desc_input.clear()
        else:
            QMessageBox.warning(self, "Lỗi", r.json().get("detail", "Có lỗi xảy ra"))

    def delete_item(self, specialty_id):
        if QMessageBox.question(self, "Xác nhận", "Vô hiệu hóa chuyên khoa này?") == QMessageBox.Yes:
            r = api_client.delete(f"/specialties/{specialty_id}")
            if r.status_code != 200:
                QMessageBox.warning(self, "Lỗi", r.json().get("detail", "Không thể xóa"))
            self.load_data()