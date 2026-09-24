"""Modern, clean Doctor Management page for Admin."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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


class DoctorManagementPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # ------------------- Header -------------------
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title_label = QLabel("Quản lý bác sĩ")
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel(
            "Danh sách đội ngũ y bác sĩ, phân bổ chuyên khoa, cơ sở phòng khám và giấy phép hành nghề"
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

        form_title = QLabel("Thêm thông tin bác sĩ mới")
        form_title.setObjectName("sectionTitle")
        form_card_layout.addWidget(form_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        # Row 0: Username, Password, Họ tên
        col_u = QVBoxLayout()
        col_u.setSpacing(4)
        lbl_u = QLabel("Tên đăng nhập")
        lbl_u.setObjectName("fieldLabel")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("VD: bstranvanb")
        col_u.addWidget(lbl_u)
        col_u.addWidget(self.username_input)
        grid.addLayout(col_u, 0, 0)

        col_p = QVBoxLayout()
        col_p.setSpacing(4)
        lbl_p = QLabel("Mật khẩu")
        lbl_p.setObjectName("fieldLabel")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("••••••••")
        col_p.addWidget(lbl_p)
        col_p.addWidget(self.password_input)
        grid.addLayout(col_p, 0, 1)

        col_fn = QVBoxLayout()
        col_fn.setSpacing(4)
        lbl_fn = QLabel("Họ và tên bác sĩ")
        lbl_fn.setObjectName("fieldLabel")
        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("VD: BS. Trần Văn B")
        col_fn.addWidget(lbl_fn)
        col_fn.addWidget(self.fullname_input)
        grid.addLayout(col_fn, 0, 2)

        # Row 1: Chuyên khoa, Phòng khám, CCHN, Button
        col_sp = QVBoxLayout()
        col_sp.setSpacing(4)
        lbl_sp = QLabel("Chuyên khoa")
        lbl_sp.setObjectName("fieldLabel")
        self.specialty_combo = QComboBox()
        col_sp.addWidget(lbl_sp)
        col_sp.addWidget(self.specialty_combo)
        grid.addLayout(col_sp, 1, 0)

        col_cl = QVBoxLayout()
        col_cl.setSpacing(4)
        lbl_cl = QLabel("Phòng khám")
        lbl_cl.setObjectName("fieldLabel")
        self.clinic_combo = QComboBox()
        col_cl.addWidget(lbl_cl)
        col_cl.addWidget(self.clinic_combo)
        grid.addLayout(col_cl, 1, 1)

        col_lic = QVBoxLayout()
        col_lic.setSpacing(4)
        lbl_lic = QLabel("Số CCHN / Giấy phép")
        lbl_lic.setObjectName("fieldLabel")
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("VD: CCHN-123456")
        col_lic.addWidget(lbl_lic)
        col_lic.addWidget(self.license_input)
        grid.addLayout(col_lic, 1, 2)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        add_btn = QPushButton("Thêm bác sĩ")
        add_btn.setObjectName("primaryButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setMinimumHeight(36)
        add_btn.clicked.connect(self.add_doctor)
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

        table_title = QLabel("Danh sách bác sĩ")
        table_title.setObjectName("sectionTitle")
        table_card_layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Họ và tên",
            "Chuyên khoa",
            "Phòng khám",
            "Số giấy phép",
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
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        table_card_layout.addWidget(self.table)
        layout.addWidget(table_card, 1)

        self.load_lookups()
        self.load_data()

    def load_lookups(self):
        self.specialty_combo.clear()
        self.specialty_map = {}
        r = api_client.get("/specialties/")
        if r.status_code == 200:
            for s in r.json():
                if s["IsActive"]:
                    self.specialty_combo.addItem(s["SpecialtyName"])
                    self.specialty_map[s["SpecialtyName"]] = s["SpecialtyID"]

        self.clinic_combo.clear()
        self.clinic_map = {}
        r = api_client.get("/clinics/")
        if r.status_code == 200:
            for c in r.json():
                if c["IsActive"]:
                    self.clinic_combo.addItem(c["ClinicName"])
                    self.clinic_map[c["ClinicName"]] = c["ClinicID"]

    def load_data(self):
        r = api_client.get("/doctors/")
        if r.status_code != 200:
            return
        items = r.json()
        self.table.clearContents()
        self.table.setRowCount(len(items))
        for row, d in enumerate(items):
            item_id = QTableWidgetItem(str(d["DoctorID"]))
            item_id.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            self.table.setItem(row, 1, QTableWidgetItem(d["FullName"]))
            self.table.setItem(row, 2, QTableWidgetItem(d.get("SpecialtyName") or "—"))
            self.table.setItem(row, 3, QTableWidgetItem(d.get("ClinicName") or "—"))
            self.table.setItem(row, 4, QTableWidgetItem(d.get("LicenseNumber") or "—"))

            # Status pill
            is_active = d["IsActive"]
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
            self.table.setCellWidget(row, 5, status_lbl)

            # Action button
            del_btn = QPushButton("Khóa" if is_active else "Mở khóa")
            del_btn.setObjectName("actionDeleteBtn")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedSize(68, 28)
            del_btn.clicked.connect(lambda _, did=d["DoctorID"]: self.delete_item(did))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(6, 0, 6, 0)
            actions_layout.setAlignment(Qt.AlignCenter)
            actions_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 6, actions_widget)
            self.table.setRowHeight(row, 44)

    def add_doctor(self):
        self.load_lookups()
        specialty_name = self.specialty_combo.currentText()
        clinic_name = self.clinic_combo.currentText()

        if not specialty_name:
            QMessageBox.warning(self, "Lỗi", "Chưa có chuyên khoa nào — hãy tạo chuyên khoa trước.")
            return
        if not self.username_input.text().strip() or not self.password_input.text():
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập tên đăng nhập và mật khẩu.")
            return

        payload = {
            "Username": self.username_input.text().strip(),
            "Password": self.password_input.text(),
            "FullName": self.fullname_input.text().strip(),
            "SpecialtyID": self.specialty_map.get(specialty_name),
            "ClinicID": self.clinic_map.get(clinic_name) if clinic_name else None,
            "LicenseNumber": self.license_input.text().strip(),
        }
        r = api_client.post("/doctors/", json=payload)
        if r.status_code == 200:
            self.load_data()
            self.username_input.clear()
            self.password_input.clear()
            self.fullname_input.clear()
            self.license_input.clear()
        else:
            QMessageBox.warning(self, "Lỗi", r.json().get("detail", "Có lỗi xảy ra"))

    def delete_item(self, doctor_id):
        if QMessageBox.question(self, "Xác nhận", "Bạn có chắc chắn muốn thay đổi trạng thái bác sĩ này?") == QMessageBox.Yes:
            api_client.delete(f"/doctors/{doctor_id}")
            self.load_data()