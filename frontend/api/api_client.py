from __future__ import annotations

import base64
import json
from threading import RLock
from typing import Any

import httpx

from frontend.core.i18n import t


def decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode JWT payload without verifying signature."""
    try:
        payload_part = token.split(".")[1]
        padding = 4 - len(payload_part) % 4
        payload_part += "=" * (padding % 4)
        return json.loads(base64.urlsafe_b64decode(payload_part))
    except Exception:
        return {}


class ApiError(Exception):
    """Normalized API or network failure safe to display to a user."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class ApiClient:
    """Small synchronous client; calls are executed only inside Qt workers."""

    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout),
            headers={"Accept": "application/json"},
        )
        self._access_token: str | None = None
        self._token_lock = RLock()
        self._role: str | None = None
        self._username: str | None = None

    @property
    def token(self) -> str | None:
        with self._token_lock:
            return self._access_token

    @property
    def role(self) -> str | None:
        return self._role

    @property
    def username(self) -> str | None:
        return self._username

    def set_access_token(self, token: str | None) -> None:
        with self._token_lock:
            self._access_token = token
            if token:
                payload = decode_jwt_payload(token)
                self._role = payload.get("role", "").upper()
                self._username = payload.get("username") or str(payload.get("sub", ""))
            else:
                self._role = None
                self._username = None

    def clear_access_token(self) -> None:
        self.set_access_token(None)

    def set_user_identity(self, *, username: str, role: str) -> None:
        """Use the server's /auth/me result for display and route labels."""
        self._username = username
        self._role = role.upper()

    def login(self, username: str, password: str) -> tuple[bool, str | None, dict[str, Any]]:
        """Log in via OAuth2 form and save token in client."""
        try:
            res = self.request("POST", "/auth/login", data={"username": username, "password": password})
            token = res.get("access_token", "")
            self.set_access_token(token)
            current_user = self.get("/auth/me")
            if not isinstance(current_user, dict) or not current_user.get("is_active"):
                raise ApiError(t("api_invalid_response"))
            self._role = str(current_user.get("role") or "").upper()
            self._username = str(current_user.get("username") or username)
            return True, None, current_user
        except ApiError as exc:
            self.clear_access_token()
            return False, exc.message, {}

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return self.request("POST", path, json=json, data=data, params=params)

    def put(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return self.request("PUT", path, json=json, data=data, params=params)

    def patch(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return self.request("PATCH", path, json=json, data=data, params=params)

    def delete(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self.request("DELETE", path, params=params)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        with self._token_lock:
            token = self._access_token
        headers = {"Authorization": f"Bearer {token}"} if token else None

        try:
            response = self._client.request(
                method,
                path,
                params=params,
                json=json,
                data=data,
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise ApiError(t("api_timeout")) from exc
        except httpx.RequestError as exc:
            raise ApiError(t("api_connection")) from exc

        if response.status_code == 204:
            return None

        payload: Any = None
        if response.content:
            try:
                payload = response.json()
            except ValueError as exc:
                if response.is_success:
                    raise ApiError(
                        t("api_invalid_response"),
                        status_code=response.status_code,
                    ) from exc

        if not response.is_success:
            raise self._error_from_response(response.status_code, payload)
        return payload

    @staticmethod
    def _error_from_response(status_code: int, payload: Any) -> ApiError:
        details = payload.get("detail") if isinstance(payload, dict) else None
        message = ApiClient._detail_message(details)
        if not message:
            message = {
                400: t("api_http_400"),
                401: t("api_http_401"),
                403: t("api_http_403"),
                404: t("api_http_404"),
                409: t("api_http_409"),
                422: t("api_http_422"),
                500: t("api_http_500"),
            }.get(status_code, t("api_http_fallback", status_code=status_code))
        return ApiError(message, status_code=status_code, details=details)

    @staticmethod
    def _detail_message(details: Any) -> str | None:
        if isinstance(details, str):
            return details
        if isinstance(details, list):
            messages: list[str] = []
            for item in details:
                if not isinstance(item, dict):
                    continue
                location = item.get("loc", [])
                field = str(location[-1]).replace("_", " ") if location else t("api_field")
                text = item.get("msg")
                if text:
                    messages.append(f"{field.title()}: {text}")
            return "\n".join(messages) or None
        if isinstance(details, dict):
            message = details.get("message") or details.get("msg")
            return str(message) if message else None
        return None

    def close(self) -> None:
        self._client.close()
