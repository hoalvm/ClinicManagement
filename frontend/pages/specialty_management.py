"""List-first medical-specialty administration."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLineEdit, QMessageBox, QTextEdit, QVBoxLayout

from frontend.api_client import api_client
from frontend.pages.admin_ui import (
    AdminApiPage,
    AdminFormDialog,
    AdminRowActions,
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


class SpecialtyManagementPage(AdminApiPage):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self.header = PageHeader(
            "Chuyên khoa",
            "Quản lý danh mục chuyên khoa y tế",
            action_label="Thêm chuyên khoa",
        )
        self.header.action_clicked.connect(self.open_create_dialog)
        layout.addWidget(self.header)
        self.add_request_feedback(layout)

        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card.setAccessibleName("Danh sách chuyên khoa")
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
                    "Chuyên khoa",
                    "specialty",
                    minimum_width=260,
                    preferred_width=460,
                    maximum_width=760,
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
            accessible_name="Danh sách chuyên khoa",
        )
        card_layout.addWidget(self.table)
        self.table_state = self.bind_state_host(
            table_card,
            self.load_data,
            empty_title="Chưa có chuyên khoa",
            empty_description="Thêm chuyên khoa đầu tiên để phân loại dịch vụ và bác sĩ.",
            empty_action_text="Thêm chuyên khoa",
            on_empty_action=self.open_create_dialog,
        )
        layout.addWidget(self.table_state, 1)
        self.load_data()

    def load_data(self, *, clear_feedback: bool = True):
        return self.run_admin_task(
            "load-specialties",
            lambda: require_success(
                api_client.get("/specialties/"),
                "Không thể tải danh sách chuyên khoa.",
            ).json(),
            self._populate_specialties,
            loading_text="Đang tải danh sách chuyên khoa…",
            clear_feedback=clear_feedback,
            stateful=True,
            empty_when=lambda specialties: not specialties,
        )

    def _populate_specialties(self, specialties: list[dict]) -> None:
        rows = []
        for specialty in specialties:
            name = str(specialty.get("SpecialtyName") or "Chưa đặt tên")
            description = str(specialty.get("Description") or "Chưa có mô tả")
            rows.append(
                {
                    "id": specialty.get("SpecialtyID"),
                    "specialty": CellValue(
                        name,
                        description,
                        accessible_text=f"{name}. {description}",
                    ),
                    "status": "ACTIVE" if specialty.get("IsActive") else "INACTIVE",
                    "actions": "",
                }
            )
        self.table.set_rows(rows)
        for row, specialty in enumerate(specialties):
            name = str(specialty.get("SpecialtyName") or "chuyên khoa")
            active = bool(specialty.get("IsActive"))
            actions = AdminRowActions(
                f"chuyên khoa {name}",
                self.table,
                on_edit=lambda specialty=specialty: self.open_edit_dialog(specialty),
                overflow_actions=(
                    (
                        "Ngừng hoạt động" if active else "Kích hoạt lại",
                        lambda specialty=specialty: self._confirm_toggle(specialty),
                    ),
                ),
            )
            set_row_actions(self.table, row, 3, actions)

    def _build_dialog(
        self,
        specialty: dict | None = None,
    ) -> tuple[AdminFormDialog, QLineEdit, QTextEdit]:
        editing = specialty is not None
        dialog = AdminFormDialog(
            "Chỉnh sửa chuyên khoa" if editing else "Thêm chuyên khoa",
            "Tên chuyên khoa cần ngắn gọn; mô tả giúp phân biệt phạm vi chuyên môn.",
            self,
            save_text="Lưu thay đổi" if editing else "Thêm chuyên khoa",
        )
        name = QLineEdit(str((specialty or {}).get("SpecialtyName") or ""))
        description = QTextEdit()
        description.setPlainText(str((specialty or {}).get("Description") or ""))
        description.setMinimumHeight(96)
        dialog.add_field("Tên chuyên khoa", name, 0, 0, required=True, column_span=2)
        dialog.add_field("Mô tả", description, 1, 0, column_span=2)
        return dialog, name, description

    def open_create_dialog(self) -> None:
        dialog, name, description = self._build_dialog()

        def submit() -> None:
            specialty_name = name.text().strip()
            if not specialty_name:
                dialog.show_request_error(
                    "Thiếu thông tin", "Vui lòng nhập tên chuyên khoa."
                )
                return
            payload = {
                "SpecialtyName": specialty_name,
                "Description": description.toPlainText().strip() or None,
            }
            self._submit_dialog(
                dialog,
                "create-specialty",
                lambda: require_success(
                    api_client.post("/specialties/", json=payload),
                    "Không thể thêm chuyên khoa.",
                ),
                "Đã thêm chuyên khoa",
            )

        dialog.buttons.accepted.connect(submit)
        dialog.exec()

    def open_edit_dialog(self, specialty: dict) -> None:
        dialog, name, description = self._build_dialog(specialty)
        specialty_id = specialty["SpecialtyID"]

        def submit() -> None:
            specialty_name = name.text().strip()
            if not specialty_name:
                dialog.show_request_error(
                    "Thiếu thông tin", "Vui lòng nhập tên chuyên khoa."
                )
                return
            payload = {
                "SpecialtyName": specialty_name,
                "Description": description.toPlainText().strip() or None,
            }
            self._submit_dialog(
                dialog,
                f"update-specialty:{specialty_id}",
                lambda: require_success(
                    api_client.put(f"/specialties/{specialty_id}", json=payload),
                    "Không thể cập nhật chuyên khoa.",
                ),
                "Đã cập nhật chuyên khoa",
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
                "Không thể lưu chuyên khoa", self.error_message(error)
            ),
            loading_text="Đang lưu chuyên khoa…",
        )

    def _saved(self, dialog: AdminFormDialog, title: str) -> None:
        dialog.accept()
        self.feedback.show_message(
            title,
            "Thông tin chuyên khoa đã được lưu.",
            severity="success",
        )
        self.load_data(clear_feedback=False)

    def _confirm_toggle(self, specialty: dict) -> None:
        active = bool(specialty.get("IsActive"))
        verb = "ngừng hoạt động" if active else "kích hoạt lại"
        name = str(specialty.get("SpecialtyName") or "chuyên khoa này")
        answer = QMessageBox.question(
            self,
            "Xác nhận trạng thái chuyên khoa",
            f"Bạn có chắc muốn {verb} chuyên khoa “{name}”?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        specialty_id = specialty["SpecialtyID"]

        def operation():
            if active:
                return require_success(
                    api_client.delete(f"/specialties/{specialty_id}"),
                    "Không thể ngừng hoạt động chuyên khoa.",
                )
            return require_success(
                api_client.put(
                    f"/specialties/{specialty_id}", json={"IsActive": True}
                ),
                "Không thể kích hoạt lại chuyên khoa.",
            )

        self.run_admin_task(
            f"toggle-specialty:{specialty_id}",
            operation,
            lambda _response: self._toggle_finished(verb),
            loading_text=f"Đang {verb} chuyên khoa…",
        )

    def _toggle_finished(self, verb: str) -> None:
        self.feedback.show_message(
            "Đã cập nhật trạng thái",
            f"Chuyên khoa đã được {verb}.",
            severity="success",
        )
        self.load_data(clear_feedback=False)
