"""List-first clinic administration."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLineEdit, QMessageBox, QTextEdit, QVBoxLayout

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
from frontend.widgets.page_header import PageHeader


class ClinicManagementPage(AdminApiPage):
    def __init__(self) -> None:
        super().__init__()
        self._all_clinics: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self.header = PageHeader(
            "Phòng khám",
            "Quản lý cơ sở y tế và thông tin liên hệ",
            action_label="Thêm phòng khám",
        )
        self.header.action_clicked.connect(self.open_create_dialog)
        layout.addWidget(self.header)
        self.add_request_feedback(layout)

        self.search = AdminSearchBar("Tìm theo tên phòng khám, địa chỉ hoặc số điện thoại…")
        self.search.search_changed.connect(self._apply_filter)
        layout.addWidget(self.search)

        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card.setAccessibleName("Danh sách phòng khám")
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
                    "Phòng khám",
                    "clinic",
                    minimum_width=220,
                    preferred_width=300,
                    maximum_width=430,
                    grow_weight=2,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Địa chỉ",
                    "address",
                    minimum_width=260,
                    preferred_width=430,
                    maximum_width=680,
                    grow_weight=3,
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
            accessible_name="Danh sách phòng khám",
        )
        card_layout.addWidget(self.table)
        self.table_state = self.bind_state_host(
            table_card,
            self.load_data,
            empty_title="Chưa có phòng khám",
            empty_description="Thêm cơ sở khám đầu tiên để gán bác sĩ và lịch làm việc.",
            empty_action_text="Thêm phòng khám",
            on_empty_action=self.open_create_dialog,
        )
        layout.addWidget(self.table_state, 1)

    def load_data(self, *, clear_feedback: bool = True):
        return self.run_admin_task(
            "load-clinics",
            lambda: require_success(
                api_client.get("/clinics/"),
                "Không thể tải danh sách phòng khám.",
            ).json(),
            self._clinics_loaded,
            loading_text="Đang tải danh sách phòng khám…",
            clear_feedback=clear_feedback,
            stateful=True,
            empty_when=lambda clinics: not clinics,
        )

    def _clinics_loaded(self, clinics: list[dict]) -> None:
        self._all_clinics = list(clinics)
        self._apply_filter(self.search.text)

    def _apply_filter(self, query: str) -> None:
        clinics = [
            clinic
            for clinic in self._all_clinics
            if matches_search(clinic, query, "ClinicName", "Address", "Phone")
        ]
        rows = []
        for clinic in clinics:
            name = str(clinic.get("ClinicName") or "Chưa đặt tên")
            phone = str(clinic.get("Phone") or "Chưa có số điện thoại")
            address = str(clinic.get("Address") or "Chưa cập nhật địa chỉ")
            rows.append(
                {
                    "id": clinic.get("ClinicID"),
                    "clinic": CellValue(
                        name,
                        phone,
                        accessible_text=f"{name}, số điện thoại {phone}",
                    ),
                    "address": CellValue(address, accessible_text=address),
                    "status": "ACTIVE" if clinic.get("IsActive") else "INACTIVE",
                    "actions": "",
                }
            )
        self.table.set_rows(rows)
        for row, clinic in enumerate(clinics):
            name = str(clinic.get("ClinicName") or "phòng khám")
            active = bool(clinic.get("IsActive"))
            actions = AdminRowActions(
                f"phòng khám {name}",
                self.table,
                on_edit=lambda clinic=clinic: self.open_edit_dialog(clinic),
                overflow_actions=(
                    (
                        "Ngừng hoạt động" if active else "Kích hoạt lại",
                        lambda clinic=clinic: self._confirm_toggle(clinic),
                    ),
                ),
            )
            set_row_actions(self.table, row, 4, actions)

    def _build_dialog(
        self,
        clinic: dict | None = None,
    ) -> tuple[AdminFormDialog, QLineEdit, QTextEdit, QLineEdit]:
        editing = clinic is not None
        dialog = AdminFormDialog(
            "Chỉnh sửa phòng khám" if editing else "Thêm phòng khám",
            "Cung cấp tên cơ sở, địa chỉ đầy đủ và số điện thoại liên hệ.",
            self,
            save_text="Lưu thay đổi" if editing else "Thêm phòng khám",
        )
        name = QLineEdit(str((clinic or {}).get("ClinicName") or ""))
        phone = QLineEdit(str((clinic or {}).get("Phone") or ""))
        address = QTextEdit()
        address.setPlainText(str((clinic or {}).get("Address") or ""))
        address.setMinimumHeight(88)
        dialog.add_field("Tên phòng khám", name, 0, 0, required=True)
        dialog.add_field("Số điện thoại", phone, 0, 1)
        dialog.add_field("Địa chỉ", address, 1, 0, column_span=2)
        return dialog, name, address, phone

    def open_create_dialog(self) -> None:
        dialog, name, address, phone = self._build_dialog()

        def submit() -> None:
            clinic_name = name.text().strip()
            if not clinic_name:
                dialog.show_request_error("Thiếu thông tin", "Vui lòng nhập tên phòng khám.")
                return
            payload = {
                "ClinicName": clinic_name,
                "Address": address.toPlainText().strip() or None,
                "Phone": phone.text().strip() or None,
            }
            self._submit_dialog(
                dialog,
                "create-clinic",
                lambda: require_success(
                    api_client.post("/clinics/", json=payload),
                    "Không thể thêm phòng khám.",
                ),
                "Đã thêm phòng khám",
            )

        dialog.buttons.accepted.connect(submit)
        dialog.exec()

    def open_edit_dialog(self, clinic: dict) -> None:
        dialog, name, address, phone = self._build_dialog(clinic)
        clinic_id = clinic["ClinicID"]

        def submit() -> None:
            clinic_name = name.text().strip()
            if not clinic_name:
                dialog.show_request_error("Thiếu thông tin", "Vui lòng nhập tên phòng khám.")
                return
            payload = {
                "ClinicName": clinic_name,
                "Address": address.toPlainText().strip() or None,
                "Phone": phone.text().strip() or None,
            }
            self._submit_dialog(
                dialog,
                f"update-clinic:{clinic_id}",
                lambda: require_success(
                    api_client.put(f"/clinics/{clinic_id}", json=payload),
                    "Không thể cập nhật phòng khám.",
                ),
                "Đã cập nhật phòng khám",
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
                "Không thể lưu phòng khám", self.error_message(error)
            ),
            loading_text="Đang lưu phòng khám…",
        )

    def _saved(self, dialog: AdminFormDialog, title: str) -> None:
        dialog.accept()
        self.feedback.show_message(
            title,
            "Thông tin phòng khám đã được lưu.",
            severity="success",
        )
        self.load_data(clear_feedback=False)

    def _confirm_toggle(self, clinic: dict) -> None:
        active = bool(clinic.get("IsActive"))
        verb = "ngừng hoạt động" if active else "kích hoạt lại"
        name = str(clinic.get("ClinicName") or "phòng khám này")
        answer = QMessageBox.question(
            self,
            "Xác nhận trạng thái phòng khám",
            f"Bạn có chắc muốn {verb} phòng khám “{name}”?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        clinic_id = clinic["ClinicID"]

        def operation():
            if active:
                return require_success(
                    api_client.delete(f"/clinics/{clinic_id}"),
                    "Không thể ngừng hoạt động phòng khám.",
                )
            return require_success(
                api_client.put(f"/clinics/{clinic_id}", json={"IsActive": True}),
                "Không thể kích hoạt lại phòng khám.",
            )

        self.run_admin_task(
            f"toggle-clinic:{clinic_id}",
            operation,
            lambda _response: self._toggle_finished(verb),
            loading_text=f"Đang {verb} phòng khám…",
        )

    def _toggle_finished(self, verb: str) -> None:
        self.feedback.show_message(
            "Đã cập nhật trạng thái",
            f"Phòng khám đã được {verb}.",
            severity="success",
        )
        self.load_data(clear_feedback=False)
