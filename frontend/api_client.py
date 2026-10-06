"""Compatibility adapter providing requests-like API on top of httpx."""

from __future__ import annotations

from typing import Any

import httpx

from frontend.core.clinic_clock import clinic_clock
from frontend.core.config import get_frontend_settings
from frontend.core.session import session_state


class LegacyResponse:
    """Mock response providing .status_code and .json() for backward compatibility."""

    def __init__(self, status_code: int, data: Any = None, text: str = ""):
        self.status_code = status_code
        self._data = data
        self.text = text

    def json(self) -> Any:
        return self._data if self._data is not None else {}

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class ApiClient:
    def __init__(self) -> None:
        self._settings = get_frontend_settings()
        self.base_url = self._settings.api_base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self._settings.api_timeout_seconds),
        )
        self.token: str | None = None
        self.role: str | None = None
        self.username: str | None = None

    def login(self, username: str, password: str) -> tuple[bool, str | None]:
        try:
            r = self._client.post(
                "/auth/login",
                data={"username": username, "password": password},
            )
        except (httpx.ConnectError, httpx.RequestError):
            return False, "Không kết nối được server. Hãy chắc chắn backend đang chạy."

        if r.status_code == 200:
            payload = r.json()
            self.token = payload["access_token"]
            try:
                me_response = self._client.get("/auth/me", headers=self._headers())
                if not me_response.is_success:
                    raise ValueError("Không thể tải tài khoản hiện tại.")
                user = me_response.json()
                if not isinstance(user, dict) or not user.get("is_active"):
                    raise ValueError("Tài khoản không còn hoạt động.")
                clock_response = self._client.get(
                    "/api/v1/system/time", headers=self._headers()
                )
                if not clock_response.is_success:
                    raise ValueError("Không thể đồng bộ thời gian phòng khám.")
                clinic_clock.set_from_payload(clock_response.json())
            except (httpx.RequestError, ValueError, KeyError, TypeError):
                self.clear_session()
                return False, "Không thể đồng bộ thời gian phòng khám. Vui lòng thử lại."
            self.role = str(user.get("role") or "").upper()
            self.username = str(user.get("username") or username)
            session_state.set_authenticated(
                self.token,
                {"username": self.username, "role": self.role},
            )
            return True, None

        try:
            return False, r.json().get("detail", "Lỗi đăng nhập")
        except Exception:
            return False, "Lỗi đăng nhập không xác định"

    def clear_session(self) -> None:
        """Drop central-login credentials before another role signs in."""

        self.token = None
        self.role = None
        self.username = None
        session_state.clear()
        clinic_clock.clear()

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _wrap(self, response: httpx.Response) -> LegacyResponse:
        data: Any = None
        try:
            data = response.json()
        except Exception:
            data = None
        return LegacyResponse(response.status_code, data, response.text)

    def get(self, path: str, params: dict[str, Any] | None = None) -> LegacyResponse:
        try:
            r = self._client.get(path, headers=self._headers(), params=params)
            return self._wrap(r)
        except httpx.RequestError:
            return LegacyResponse(503, {"detail": "Không thể kết nối server."})

    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> LegacyResponse:
        try:
            r = self._client.post(path, headers=self._headers(), json=json, data=data)
            return self._wrap(r)
        except httpx.RequestError:
            return LegacyResponse(503, {"detail": "Không thể kết nối server."})

    def put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> LegacyResponse:
        try:
            r = self._client.put(path, headers=self._headers(), json=json, data=data)
            return self._wrap(r)
        except httpx.RequestError:
            return LegacyResponse(503, {"detail": "Không thể kết nối server."})

    def delete(self, path: str) -> LegacyResponse:
        try:
            r = self._client.delete(path, headers=self._headers())
            return self._wrap(r)
        except httpx.RequestError:
            return LegacyResponse(503, {"detail": "Không thể kết nối server."})


api_client = ApiClient()

