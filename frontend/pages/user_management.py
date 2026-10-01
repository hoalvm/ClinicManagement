"""List-first account administration."""

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

ROLE_LABELS = {
    "PATIENT": "Bệnh nhân",
    "DOCTOR": "Bác sĩ",
    "STAFF": "Nhân viên",
    "ADMIN": "Quản trị viên",
}


class UserManagementPage(AdminApiPage):
    def __init__(self) -> None:
        super().__init__()
        self._all_users: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self.header = PageHeader(
            "Tài khoản",
            "Quản lý tài khoản và quyền truy cập hệ thống",
            action_label="Tạo tài khoản",
        )
        self.header.action_clicked.connect(self.open_create_dialog)
        layout.addWidget(self.header)
        self.add_request_feedback(layout)

        self.search = AdminSearchBar("Tìm theo tên đăng nhập, họ tên hoặc vai trò…")
        self.role_filter = self.search.add_filter(
            "role",
            (
                ("Tất cả vai trò", None),
                ("Bệnh nhân", "PATIENT"),
                ("Bác sĩ", "DOCTOR"),
                ("Nhân viên", "STAFF"),
                ("Quản trị viên", "ADMIN"),
            ),
            accessible_name="Lọc tài khoản theo vai trò",
        )
        self.search.filters_changed.connect(self._apply_filter)
        layout.addWidget(self.search)

        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card.setAccessibleName("Danh sách tài khoản")
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
                    "Tài khoản",
                    "identity",
                    minimum_width=210,
                    preferred_width=300,
                    maximum_width=460,
                    grow_weight=2,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Vai trò",
                    "role",
                    minimum_width=120,
                    preferred_width=136,
                    maximum_width=156,
                    preserve_full=True,
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
            accessible_name="Danh sách tài khoản",
        )
        card_layout.addWidget(self.table)
        self.table_state = self.bind_state_host(
            table_card,
            self.load_data,
            empty_title="Chưa có tài khoản",
            empty_description="Tạo tài khoản đầu tiên để bắt đầu phân quyền người dùng.",
            empty_action_text="Tạo tài khoản",
            on_empty_action=self.open_create_dialog,
        )
        layout.addWidget(self.table_state, 1)

    def load_data(self, *, clear_feedback: bool = True):
        return self.run_admin_task(
            "load-users",
            lambda: require_success(
                api_client.get("/users/"),
                "Không thể tải danh sách tài khoản.",
            ).json(),
            self._users_loaded,
            loading_text="Đang tải danh sách tài khoản…",
            clear_feedback=clear_feedback,
            stateful=True,
            empty_when=lambda users: not users,
        )

    def _users_loaded(self, users: list[dict]) -> None:
        self._all_users = list(users)
        self._apply_filter(self.search.values())

    def _apply_filter(self, values: object | None = None) -> None:
        filters = values if isinstance(values, dict) else self.search.values()
        query = str(filters.get("search") or "")
        selected_role = filters.get("role")
        users = [
            user
            for user in self._all_users
            if matches_search(user, query, "Username", "FullName", "Role")
            and (
                not selected_role
                or str(user.get("Role") or "").strip().upper() == selected_role
            )
        ]
        rows = []
        for user in users:
            username = str(user.get("Username") or "—")
            full_name = str(user.get("FullName") or "Chưa cập nhật họ tên")
            rows.append(
                {
                    "id": user.get("UserID"),
                    "identity": CellValue(
                        username,
                        full_name,
                        accessible_text=f"{username}, {full_name}",
                    ),
                    "role": ROLE_LABELS.get(str(user.get("Role")), user.get("Role")),
                    "status": "ACTIVE" if user.get("IsActive") else "INACTIVE",
                    "actions": "",
                }
            )
        if not users and self._all_users:
            self.table.set_rows([
                {
                    "id": "",
                    "identity": "Không có tài khoản phù hợp với bộ lọc",
                    "role": "",
                    "status": "",
                    "actions": "",
                }
            ])
            return
        self.table.set_rows(rows)
        for row, user in enumerate(users):
            username = str(user.get("Username") or "tài khoản")
            active = bool(user.get("IsActive"))
            is_protected_admin = (
                username.lower() == "admin"
                or (api_client.username and username.lower() == str(api_client.username).lower())
            )
            overflow_actions = []
            if not (is_protected_admin and active):
                overflow_actions.append(
                    (
                        "Khóa tài khoản" if active else "Mở khóa tài khoản",
                        lambda user=user: self._confirm_toggle(user),
                    )
                )
            actions = AdminRowActions(
                f"tài khoản {username}",
                self.table,
                on_edit=lambda user=user: self.open_edit_dialog(user),
                overflow_actions=tuple(overflow_actions),
            )
            set_row_actions(self.table, row, 4, actions)

    def _build_dialog(
        self,
        *,
        user: dict | None = None,
    ) -> tuple[AdminFormDialog, dict[str, object]]:
        editing = user is not None
        dialog = AdminFormDialog(
            "Chỉnh sửa tài khoản" if editing else "Tạo tài khoản",
            "Cập nhật thông tin định danh và quyền truy cập."
            if editing
            else "Tạo tài khoản cho bệnh nhân, nhân viên hoặc quản trị viên.",
            self,
            save_text="Lưu thay đổi" if editing else "Tạo tài khoản",
        )
        username = QLineEdit(str((user or {}).get("Username") or ""))
        fullname = QLineEdit(str((user or {}).get("FullName") or ""))
        phone = QLineEdit(str((user or {}).get("Phone") or ""))
        email = QLineEdit(str((user or {}).get("Email") or ""))
        role = ChevronComboBox()
        for code in ("PATIENT", "STAFF", "ADMIN"):
            role.addItem(ROLE_LABELS[code], code)
        current_role = str((user or {}).get("Role") or "PATIENT")
        if editing and current_role == "DOCTOR":
            role.insertItem(0, ROLE_LABELS["DOCTOR"], "DOCTOR")
            role.setEnabled(False)
            role.setToolTip("Vai trò bác sĩ được quản lý trong mục Bác sĩ.")
        index = role.findData(current_role)
        role.setCurrentIndex(max(0, index))

        dialog.add_field("Tên đăng nhập", username, 0, 0, required=True)
        dialog.add_field("Họ và tên", fullname, 0, 1)
        if not editing:
            password = QLineEdit()
            password.setEchoMode(QLineEdit.EchoMode.Password)
            dialog.add_field("Mật khẩu", password, 1, 0, required=True)
        else:
            password = None
        dialog.add_field("Vai trò", role, 1, 1 if not editing else 0, required=True)
        dialog.add_field("Số điện thoại", phone, 2, 0)
        dialog.add_field("Email", email, 2, 1)
        return dialog, {
            "username": username,
            "fullname": fullname,
            "password": password,
            "role": role,
            "phone": phone,
            "email": email,
        }

    def open_create_dialog(self) -> None:
        dialog, controls = self._build_dialog()

        def submit() -> None:
            username = controls["username"].text().strip()
            password = controls["password"].text()
            if not username or not password:
                dialog.show_request_error(
                    "Thiếu thông tin",
                    "Vui lòng nhập tên đăng nhập và mật khẩu.",
                )
                return
            payload = {
                "Username": username,
                "FullName": controls["fullname"].text().strip(),
                "Password": password,
                "Role": controls["role"].currentData(),
                "Phone": controls["phone"].text().strip() or None,
                "Email": controls["email"].text().strip() or None,
            }
            dialog.set_busy(True)
            self.run_admin_task(
                "create-user",
                lambda: require_success(
                    api_client.post("/users/", json=payload),
                    "Không thể tạo tài khoản.",
                ),
                lambda _response: self._saved(dialog, "Đã tạo tài khoản"),
                on_finished=lambda: dialog.set_busy(False),
                on_error=lambda error: dialog.show_request_error(
                    "Không thể tạo tài khoản", self.error_message(error)
                ),
                loading_text="Đang tạo tài khoản…",
            )

        dialog.buttons.accepted.connect(submit)
        dialog.exec()

    def open_edit_dialog(self, user: dict) -> None:
        dialog, controls = self._build_dialog(user=user)
        user_id = user["UserID"]

        def submit() -> None:
            username = controls["username"].text().strip()
            if not username:
                dialog.show_request_error("Thiếu thông tin", "Vui lòng nhập tên đăng nhập.")
                return
            payload = {
                "Username": username,
                "FullName": controls["fullname"].text().strip(),
                "Role": controls["role"].currentData(),
                "Phone": controls["phone"].text().strip() or None,
                "Email": controls["email"].text().strip() or None,
            }
            dialog.set_busy(True)
            self.run_admin_task(
                f"update-user:{user_id}",
                lambda: require_success(
                    api_client.put(f"/users/{user_id}", json=payload),
                    "Không thể cập nhật tài khoản.",
                ),
                lambda _response: self._saved(dialog, "Đã cập nhật tài khoản"),
                on_finished=lambda: dialog.set_busy(False),
                on_error=lambda error: dialog.show_request_error(
                    "Không thể cập nhật tài khoản", self.error_message(error)
                ),
                loading_text="Đang cập nhật tài khoản…",
            )

        dialog.buttons.accepted.connect(submit)
        dialog.exec()

    def _saved(self, dialog: AdminFormDialog, title: str) -> None:
        dialog.accept()
        self.feedback.show_message(
            title,
            "Thông tin tài khoản đã được lưu.",
            severity="success",
        )
        self.load_data(clear_feedback=False)

    def _confirm_toggle(self, user: dict) -> None:
        active = bool(user.get("IsActive"))
        username = str(user.get("Username") or "tài khoản này")
        is_protected_admin = (
            username.lower() == "admin"
            or (api_client.username and username.lower() == str(api_client.username).lower())
        )
        if active and is_protected_admin:
            self.feedback.show_message(
                "Không thể thực hiện",
                "Không thể khóa tài khoản quản trị viên hiện tại hoặc tài khoản admin hệ thống.",
                severity="warning",
            )
            return
        verb = "khóa" if active else "mở khóa"
        answer = QMessageBox.question(
            self,
            f"Xác nhận {verb} tài khoản",
            f"Bạn có chắc muốn {verb} tài khoản “{username}”?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        user_id = user["UserID"]

        def operation():
            if active:
                return require_success(
                    api_client.delete(f"/users/{user_id}"),
                    "Không thể khóa tài khoản.",
                )
            return require_success(
                api_client.put(f"/users/{user_id}", json={"IsActive": True}),
                "Không thể mở khóa tài khoản.",
            )

        self.run_admin_task(
            f"toggle-user:{user_id}",
            operation,
            lambda _response: self._toggle_finished(verb),
            loading_text=f"Đang {verb} tài khoản…",
        )

    def _toggle_finished(self, verb: str) -> None:
        self.feedback.show_message(
            "Đã cập nhật trạng thái",
            f"Tài khoản đã được {verb}.",
            severity="success",
        )
        self.load_data(clear_feedback=False)
