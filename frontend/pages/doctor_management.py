"""List-first doctor administration."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLineEdit, QMessageBox, QVBoxLayout

from frontend.api_client import api_client
from frontend.pages.admin_ui import (
    AdminApiPage,
    AdminFormDialog,
    AdminRowActions,
    AdminSearchBar,
    matches_search,
    require_success,
    set_row_actions,
)
from frontend.ui.design_system import (
    CellValue,
    ColumnDisplayMode,
    ColumnPriority,
    ColumnSpec,
)
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.combo_box import ChevronComboBox
from frontend.widgets.page_header import PageHeader


class DoctorManagementPage(AdminApiPage):
    def __init__(self) -> None:
        super().__init__()
        self._all_doctors: list[dict] = []
        self._specialties: list[dict] = []
        self._clinics: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self.header = PageHeader(
            "Bác sĩ",
            "Quản lý hồ sơ chuyên môn và nơi làm việc",
            action_label="Thêm bác sĩ",
        )
        self.header.action_clicked.connect(self.open_create_dialog)
        layout.addWidget(self.header)
        self.add_request_feedback(layout)

        self.search = AdminSearchBar(
            "Tìm theo tên, chuyên khoa, phòng khám hoặc số giấy phép…"
        )
        self.search.search_changed.connect(self._apply_filter)
        layout.addWidget(self.search)

        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card.setAccessibleName("Danh sách bác sĩ")
        card_layout = QVBoxLayout(table_card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        self.table = AdaptiveDataTable(
            (
                ColumnSpec(
                    "ID",
                    "id",
                    minimum_width=56,
                    preferred_width=64,
                    maximum_width=72,
                    priority=int(ColumnPriority.CRITICAL),
                    preserve_full=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Bác sĩ",
                    "doctor",
                    minimum_width=190,
                    preferred_width=260,
                    maximum_width=390,
                    grow_weight=2,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Chuyên khoa",
                    "specialty",
                    minimum_width=130,
                    preferred_width=170,
                    maximum_width=240,
                    grow_weight=1,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Phòng khám",
                    "clinic",
                    minimum_width=150,
                    preferred_width=210,
                    maximum_width=310,
                    grow_weight=1,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Trạng thái",
                    "status",
                    minimum_width=124,
                    preferred_width=132,
                    maximum_width=148,
                    priority=int(ColumnPriority.CRITICAL),
                    preserve_full=True,
                    status=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Thao tác",
                    "actions",
                    minimum_width=132,
                    preferred_width=140,
                    maximum_width=152,
                    priority=int(ColumnPriority.CRITICAL),
                    preserve_full=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
            ),
            accessible_name="Danh sách bác sĩ",
        )
        card_layout.addWidget(self.table)
        self.table_state = self.bind_state_host(
            table_card,
            self.load_data,
            empty_title="Chưa có bác sĩ",
            empty_description="Thêm hồ sơ bác sĩ đầu tiên để phân chuyên khoa và lịch trực.",
            empty_action_text="Thêm bác sĩ",
            on_empty_action=self.open_create_dialog,
        )
        layout.addWidget(self.table_state, 1)
        self.load_lookups()
        self.load_data()

    def load_lookups(self):
        return self.run_admin_task(
            "load-doctor-lookups",
            self._fetch_lookups,
            self._lookups_loaded,
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

    def _lookups_loaded(self, result) -> None:
        specialties, clinics = result
        self._specialties = [item for item in specialties if item.get("IsActive")]
        self._clinics = [item for item in clinics if item.get("IsActive")]

    def load_data(self, *, clear_feedback: bool = True):
        return self.run_admin_task(
            "load-doctors",
            lambda: require_success(
                api_client.get("/doctors/"),
                "Không thể tải danh sách bác sĩ.",
            ).json(),
            self._doctors_loaded,
            loading_text="Đang tải danh sách bác sĩ…",
            clear_feedback=clear_feedback,
            stateful=True,
            empty_when=lambda doctors: not doctors,
        )

    def _doctors_loaded(self, doctors: list[dict]) -> None:
        self._all_doctors = list(doctors)
        self._apply_filter(self.search.text)

    def _apply_filter(self, query: str) -> None:
        doctors = [
            doctor
            for doctor in self._all_doctors
            if matches_search(
                doctor,
                query,
                "FullName",
                "SpecialtyName",
                "ClinicName",
                "LicenseNumber",
            )
        ]
        rows = []
        for doctor in doctors:
            name = str(doctor.get("FullName") or "Chưa cập nhật họ tên")
            license_number = str(doctor.get("LicenseNumber") or "Chưa có giấy phép")
            rows.append(
                {
                    "id": doctor.get("DoctorID"),
                    "doctor": CellValue(
                        name,
                        f"Giấy phép: {license_number}",
                        accessible_text=f"{name}, số giấy phép hành nghề {license_number}",
                    ),
                    "specialty": doctor.get("SpecialtyName") or "Chưa phân chuyên khoa",
                    "clinic": doctor.get("ClinicName") or "Chưa phân phòng khám",
                    "status": "ACTIVE" if doctor.get("IsActive") else "INACTIVE",
                    "actions": "",
                }
            )
        self.table.set_rows(rows)
        for row, doctor in enumerate(doctors):
            name = str(doctor.get("FullName") or "bác sĩ")
            active = bool(doctor.get("IsActive"))
            actions = AdminRowActions(
                f"bác sĩ {name}",
                self.table,
                on_edit=lambda doctor=doctor: self.open_edit_dialog(doctor),
                overflow_actions=(
                    (
                        "Ngừng hoạt động" if active else "Kích hoạt lại",
                        lambda doctor=doctor: self._confirm_toggle(doctor),
                    ),
                ),
            )
            set_row_actions(self.table, row, 5, actions)

    def _build_dialog(
        self,
        doctor: dict | None = None,
    ) -> tuple[AdminFormDialog, dict[str, object]]:
        editing = doctor is not None
        dialog = AdminFormDialog(
            "Chỉnh sửa bác sĩ" if editing else "Thêm bác sĩ",
            "Cập nhật chuyên khoa, phòng khám và giấy phép hành nghề."
            if editing
            else "Tạo tài khoản và hồ sơ chuyên môn cho bác sĩ.",
            self,
            save_text="Lưu thay đổi" if editing else "Thêm bác sĩ",
        )
        username = QLineEdit()
        password = QLineEdit()
        password.setEchoMode(QLineEdit.EchoMode.Password)
        fullname = QLineEdit(str((doctor or {}).get("FullName") or ""))
        specialty = ChevronComboBox()
        for item in self._specialties:
            specialty.addItem(item["SpecialtyName"], item["SpecialtyID"])
        clinic = ChevronComboBox()
        clinic.addItem("Chưa phân phòng khám", None)
        for item in self._clinics:
            clinic.addItem(item["ClinicName"], item["ClinicID"])
        license_input = QLineEdit(str((doctor or {}).get("LicenseNumber") or ""))

        if editing:
            fullname.setReadOnly(True)
            fullname.setToolTip("Tên bác sĩ thuộc tài khoản và không chỉnh sửa tại màn này.")
            special_index = specialty.findData(doctor.get("SpecialtyID"))
            specialty.setCurrentIndex(max(0, special_index))
            clinic_index = clinic.findData(doctor.get("ClinicID"))
            clinic.setCurrentIndex(max(0, clinic_index))
            dialog.add_field("Họ và tên bác sĩ", fullname, 0, 0, column_span=2)
            dialog.add_field("Chuyên khoa", specialty, 1, 0, required=True)
            dialog.add_field("Phòng khám", clinic, 1, 1)
            dialog.add_field(
                "Số giấy phép hành nghề", license_input, 2, 0, column_span=2
            )
        else:
            dialog.add_field("Tên đăng nhập", username, 0, 0, required=True)
            dialog.add_field("Mật khẩu", password, 0, 1, required=True)
            dialog.add_field(
                "Họ và tên bác sĩ", fullname, 1, 0, required=True, column_span=2
            )
            dialog.add_field("Chuyên khoa", specialty, 2, 0, required=True)
            dialog.add_field("Phòng khám", clinic, 2, 1)
            dialog.add_field(
                "Số giấy phép hành nghề", license_input, 3, 0, column_span=2
            )
        return dialog, {
            "username": username,
            "password": password,
            "fullname": fullname,
            "specialty": specialty,
            "clinic": clinic,
            "license": license_input,
        }

    def open_create_dialog(self) -> None:
        if not self._specialties:
            QMessageBox.information(
                self,
                "Chưa có chuyên khoa",
                "Hãy tạo ít nhất một chuyên khoa đang hoạt động trước khi thêm bác sĩ.",
            )
            return
        dialog, controls = self._build_dialog()

        def submit() -> None:
            username = controls["username"].text().strip()
            password = controls["password"].text()
            fullname = controls["fullname"].text().strip()
            if not username or not password or not fullname:
                dialog.show_request_error(
                    "Thiếu thông tin",
                    "Vui lòng nhập tên đăng nhập, mật khẩu và họ tên bác sĩ.",
                )
                return
            payload = {
                "Username": username,
                "Password": password,
                "FullName": fullname,
                "SpecialtyID": controls["specialty"].currentData(),
                "ClinicID": controls["clinic"].currentData(),
                "LicenseNumber": controls["license"].text().strip() or None,
            }
            self._submit_dialog(
                dialog,
                "create-doctor",
                lambda: require_success(
                    api_client.post("/doctors/", json=payload),
                    "Không thể thêm bác sĩ.",
                ),
                "Đã thêm bác sĩ",
            )

        dialog.buttons.accepted.connect(submit)
        dialog.exec()

    def open_edit_dialog(self, doctor: dict) -> None:
        dialog, controls = self._build_dialog(doctor)
        doctor_id = doctor["DoctorID"]

        def submit() -> None:
            payload = {
                "SpecialtyID": controls["specialty"].currentData(),
                "ClinicID": controls["clinic"].currentData(),
                "LicenseNumber": controls["license"].text().strip() or None,
            }
            self._submit_dialog(
                dialog,
                f"update-doctor:{doctor_id}",
                lambda: require_success(
                    api_client.put(f"/doctors/{doctor_id}", json=payload),
                    "Không thể cập nhật bác sĩ.",
                ),
                "Đã cập nhật bác sĩ",
            )

        dialog.buttons.accepted.connect(submit)
        dialog.exec()

    def _submit_dialog(self, dialog, key, operation, success_title) -> None:
        dialog.set_busy(True)
        self.run_admin_task(
            key,
            operation,
            lambda _response: self._saved(dialog, success_title),
            on_finished=lambda: dialog.set_busy(False),
            on_error=lambda error: dialog.show_request_error(
                "Không thể lưu hồ sơ bác sĩ", self.error_message(error)
            ),
            loading_text="Đang lưu hồ sơ bác sĩ…",
        )

    def _saved(self, dialog: AdminFormDialog, title: str) -> None:
        dialog.accept()
        self.feedback.show_message(
            title,
            "Hồ sơ bác sĩ đã được lưu.",
            severity="success",
        )
        self.load_data(clear_feedback=False)

    def _confirm_toggle(self, doctor: dict) -> None:
        active = bool(doctor.get("IsActive"))
        verb = "ngừng hoạt động" if active else "kích hoạt lại"
        name = str(doctor.get("FullName") or "bác sĩ này")
        answer = QMessageBox.question(
            self,
            "Xác nhận trạng thái bác sĩ",
            f"Bạn có chắc muốn {verb} hồ sơ “{name}”?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        doctor_id = doctor["DoctorID"]

        def operation():
            if active:
                return require_success(
                    api_client.delete(f"/doctors/{doctor_id}"),
                    "Không thể ngừng hoạt động bác sĩ.",
                )
            response = require_success(
                api_client.put(f"/doctors/{doctor_id}", json={"IsActive": True}),
                "Không thể kích hoạt lại bác sĩ.",
            )
            user_id = doctor.get("UserID")
            if user_id is not None:
                require_success(
                    api_client.put(f"/users/{user_id}", json={"IsActive": True}),
                    "Hồ sơ bác sĩ đã mở nhưng tài khoản chưa thể kích hoạt.",
                )
            return response

        self.run_admin_task(
            f"toggle-doctor:{doctor_id}",
            operation,
            lambda _response: self._toggle_finished(verb),
            loading_text=f"Đang {verb} bác sĩ…",
        )

    def _toggle_finished(self, verb: str) -> None:
        self.feedback.show_message(
            "Đã cập nhật trạng thái",
            f"Bác sĩ đã được {verb}.",
            severity="success",
        )
        self.load_data(clear_feedback=False)
