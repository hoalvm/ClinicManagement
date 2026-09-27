"""Modern, clean Doctor Management page for Admin."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)

from frontend.api_client import api_client
from frontend.pages.admin_ui import (
    AdminApiPage,
    action_cell,
    configure_admin_table,
    require_success,
    table_item,
)
from frontend.widgets.page_header import PageHeader
from frontend.widgets.status_badge import STATUS_LABELS_VN, StatusBadgeDelegate


class DoctorManagementPage(AdminApiPage):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # ------------------- Header -------------------
        self.header = PageHeader(
            "Bác sĩ",
            "Danh sách và hồ sơ bác sĩ",
        )
        layout.addWidget(self.header)
        self.add_request_feedback(layout)

        # ------------------- Create Form Card -------------------
        form_card = QFrame()
        form_card.setObjectName("contentCard")
        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(20, 18, 20, 18)
        form_card_layout.setSpacing(14)

        form_title = QLabel("Thêm bác sĩ")
        form_title.setObjectName("sectionTitle")
        form_card_layout.addWidget(form_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)

        # Row 0: Username, Password, Họ tên
        col_u = QVBoxLayout()
        col_u.setSpacing(5)
        lbl_u = QLabel("Tên đăng nhập")
        lbl_u.setObjectName("fieldLabel")
        self.username_input = QLineEdit()
        col_u.addWidget(lbl_u)
        col_u.addWidget(self.username_input)
        grid.addLayout(col_u, 0, 0)

        col_p = QVBoxLayout()
        col_p.setSpacing(5)
        lbl_p = QLabel("Mật khẩu")
        lbl_p.setObjectName("fieldLabel")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        col_p.addWidget(lbl_p)
        col_p.addWidget(self.password_input)
        grid.addLayout(col_p, 0, 1)

        col_fn = QVBoxLayout()
        col_fn.setSpacing(5)
        lbl_fn = QLabel("Họ và tên bác sĩ")
        lbl_fn.setObjectName("fieldLabel")
        self.fullname_input = QLineEdit()
        col_fn.addWidget(lbl_fn)
        col_fn.addWidget(self.fullname_input)
        grid.addLayout(col_fn, 0, 2)

        # Row 1: Chuyên khoa, Phòng khám, CCHN, Button
        col_sp = QVBoxLayout()
        col_sp.setSpacing(5)
        lbl_sp = QLabel("Chuyên khoa")
        lbl_sp.setObjectName("fieldLabel")
        self.specialty_combo = QComboBox()
        col_sp.addWidget(lbl_sp)
        col_sp.addWidget(self.specialty_combo)
        grid.addLayout(col_sp, 1, 0)

        col_cl = QVBoxLayout()
        col_cl.setSpacing(5)
        lbl_cl = QLabel("Phòng khám")
        lbl_cl.setObjectName("fieldLabel")
        self.clinic_combo = QComboBox()
        col_cl.addWidget(lbl_cl)
        col_cl.addWidget(self.clinic_combo)
        grid.addLayout(col_cl, 1, 1)

        col_lic = QVBoxLayout()
        col_lic.setSpacing(5)
        lbl_lic = QLabel("Số CCHN / Giấy phép")
        lbl_lic.setObjectName("fieldLabel")
        self.license_input = QLineEdit()
        col_lic.addWidget(lbl_lic)
        col_lic.addWidget(self.license_input)
        grid.addLayout(col_lic, 1, 2)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.add_btn = QPushButton("Thêm mới")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setMinimumHeight(36)
        self.add_btn.setMinimumWidth(120)
        self.add_btn.setAccessibleName("Thêm bác sĩ mới")
        self.add_btn.clicked.connect(self.add_doctor)
        btn_layout.addWidget(self.add_btn)

        form_card_layout.addLayout(grid)
        form_card_layout.addLayout(btn_layout)
        layout.addWidget(form_card)

        # ------------------- Table Card -------------------
        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card.setAccessibleName("Nội dung danh sách bác sĩ")
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(20, 18, 20, 18)
        table_card_layout.setSpacing(12)

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
        configure_admin_table(
            self.table,
            accessible_name="Danh sách bác sĩ",
            stretch_column=1,
            fixed_widths={0: 52, 2: 132, 3: 170, 4: 126, 5: 116, 6: 98},
        )
        self.table.setItemDelegateForColumn(5, StatusBadgeDelegate(self.table))

        table_card_layout.addWidget(self.table)
        self.table_state = self.bind_state_host(
            table_card,
            self.load_data,
            empty_title="Chưa có bác sĩ",
            empty_description="Thêm hồ sơ bác sĩ đầu tiên để phân chuyên khoa và lịch trực.",
            empty_action_text="Thêm bác sĩ",
            on_empty_action=self.username_input.setFocus,
        )
        layout.addWidget(self.table_state, 1)

        self.load_lookups()
        self.load_data()

    def load_lookups(self):
        return self.run_admin_task(
            "load-doctor-lookups",
            self._fetch_lookups,
            self._populate_lookups,
            controls=(self.specialty_combo, self.clinic_combo, self.add_btn),
            loading_text="Đang tải chuyên khoa và phòng khám…",
        )

    @staticmethod
    def _fetch_lookups():
        specialties = require_success(
            api_client.get("/specialties/"),
            "Không thể tải danh sách chuyên khoa.",
        ).json()
        clinics = require_success(
            api_client.get("/clinics/"),
            "Không thể tải danh sách phòng khám.",
        ).json()
        return specialties, clinics

    def _populate_lookups(self, result):
        specialties, clinics = result
        self.specialty_combo.clear()
        self.specialty_map = {}
        for specialty in specialties:
            if specialty["IsActive"]:
                name = specialty["SpecialtyName"]
                self.specialty_combo.addItem(name)
                self.specialty_map[name] = specialty["SpecialtyID"]

        self.clinic_combo.clear()
        self.clinic_map = {}
        for clinic in clinics:
            if clinic["IsActive"]:
                name = clinic["ClinicName"]
                self.clinic_combo.addItem(name)
                self.clinic_map[name] = clinic["ClinicID"]

    def load_data(self, *, clear_feedback: bool = True):
        return self.run_admin_task(
            "load-doctors",
            lambda: require_success(
                api_client.get("/doctors/"),
                "Không thể tải danh sách bác sĩ.",
            ).json(),
            self._populate_doctors,
            loading_text="Đang tải danh sách bác sĩ…",
            clear_feedback=clear_feedback,
            stateful=True,
            empty_when=lambda doctors: not doctors,
        )

    def _populate_doctors(self, items):
        self.table.clearContents()
        self.table.setRowCount(len(items))
        for row, d in enumerate(items):
            item_id = table_item(d["DoctorID"], alignment=Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            self.table.setItem(row, 1, table_item(d["FullName"]))
            self.table.setItem(row, 2, table_item(d.get("SpecialtyName")))
            self.table.setItem(row, 3, table_item(d.get("ClinicName")))
            self.table.setItem(row, 4, table_item(d.get("LicenseNumber")))

            # Status pill (rendered via delegate)
            is_active = d["IsActive"]
            status_text = "ACTIVE" if is_active else "INACTIVE"
            status_label = STATUS_LABELS_VN[status_text]
            item_status = table_item(
                status_text,
                alignment=Qt.AlignCenter,
                tooltip=status_label,
                accessible_text=status_label,
            )
            self.table.setItem(row, 5, item_status)

            # Action button
            del_btn = QPushButton("Khóa" if is_active else "Mở khóa")
            del_btn.setObjectName("actionDeleteBtn")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedSize(76, 34)
            del_btn.setAccessibleName(
                f"{'Khóa' if is_active else 'Mở khóa'} bác sĩ {d['FullName']}"
            )
            del_btn.setToolTip(del_btn.accessibleName())
            del_btn.clicked.connect(
                lambda _, did=d["DoctorID"], button=del_btn: self.delete_item(did, button)
            )

            actions_widget = action_cell(
                del_btn,
                accessible_name=f"Thao tác cho bác sĩ {d['FullName']}",
            )

            self.table.setCellWidget(row, 6, actions_widget)
            self.table.setRowHeight(row, 48)

    def add_doctor(self):
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
        self.run_admin_task(
            "create-doctor",
            lambda: require_success(
                api_client.post("/doctors/", json=payload),
                "Không thể thêm bác sĩ.",
            ),
            self._doctor_created,
            controls=(self.add_btn,),
            loading_text="Đang thêm bác sĩ…",
        )

    def _doctor_created(self, _response) -> None:
        self.username_input.clear()
        self.password_input.clear()
        self.fullname_input.clear()
        self.license_input.clear()
        self.feedback.show_message(
            "Đã thêm bác sĩ",
            "Hồ sơ bác sĩ đã được lưu.",
            severity="success",
        )
        self.load_data(clear_feedback=False)

    def delete_item(self, doctor_id, button: QPushButton | None = None):
        if QMessageBox.question(self, "Xác nhận", "Bạn có chắc chắn muốn thay đổi trạng thái bác sĩ này?") == QMessageBox.Yes:
            controls = (button,) if button is not None else ()
            self.run_admin_task(
                f"toggle-doctor:{doctor_id}",
                lambda: require_success(
                    api_client.delete(f"/doctors/{doctor_id}"),
                    "Không thể thay đổi trạng thái bác sĩ.",
                ),
                self._doctor_toggled,
                controls=controls,
                loading_text="Đang cập nhật trạng thái bác sĩ…",
            )

    def _doctor_toggled(self, _response) -> None:
        self.feedback.show_message(
            "Đã cập nhật",
            "Trạng thái bác sĩ đã được thay đổi.",
            severity="success",
        )
        self.load_data(clear_feedback=False)
