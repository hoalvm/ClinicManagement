from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
                                 QPushButton, QLineEdit, QMessageBox, QLabel, QHeaderView)
from api_client import api_client

class ClinicManagementPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title_label = QLabel("QUẢN LÝ PHÒNG KHÁM")
        title_label.setStyleSheet("font-size: 20px; font-weight: 700; color: #1e293b;")
        layout.addWidget(title_label)

        form_layout = QHBoxLayout()
        self.name_input = QLineEdit(); self.name_input.setPlaceholderText("Tên phòng khám")
        self.address_input = QLineEdit(); self.address_input.setPlaceholderText("Địa chỉ")
        self.phone_input = QLineEdit(); self.phone_input.setPlaceholderText("SĐT")
        add_btn = QPushButton("Thêm"); add_btn.clicked.connect(self.add_clinic)
        for w in [self.name_input, self.address_input, self.phone_input, add_btn]:
            form_layout.addWidget(w)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Tên phòng khám", "Địa chỉ", "Trạng thái", "Xóa"])
        header = self.table.horizontalHeader()
        header.setFixedHeight(30)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        layout.addLayout(form_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.load_data()

    def load_data(self):
        r = api_client.get("/clinics/")
        if r.status_code != 200:
            return
        items = r.json()
        self.table.setRowCount(len(items))
        for row, c in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(str(c["ClinicID"])))
            self.table.setItem(row, 1, QTableWidgetItem(c["ClinicName"]))
            self.table.setItem(row, 2, QTableWidgetItem(c.get("Address") or ""))
            self.table.setItem(row, 3, QTableWidgetItem("Hoạt động" if c["IsActive"] else "Đã khóa"))
            del_btn = QPushButton("Xóa")
            del_btn.clicked.connect(lambda _, cid=c["ClinicID"]: self.delete_item(cid))
            self.table.setCellWidget(row, 4, del_btn)

    def add_clinic(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên phòng khám")
            return
        payload = {
            "ClinicName": name,
            "Address": self.address_input.text(),
            "Phone": self.phone_input.text(),
        }
        r = api_client.post("/clinics/", json=payload)
        if r.status_code == 200:
            self.load_data()
            self.name_input.clear(); self.address_input.clear(); self.phone_input.clear()
        else:
            QMessageBox.warning(self, "Lỗi", r.json().get("detail", "Có lỗi xảy ra"))

    def delete_item(self, clinic_id):
        if QMessageBox.question(self, "Xác nhận", "Vô hiệu hóa phòng khám này?") == QMessageBox.Yes:
            api_client.delete(f"/clinics/{clinic_id}")
            self.load_data()