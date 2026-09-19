"""The single HTTP boundary used by all frontend views."""

from __future__ import annotations

from threading import RLock
from typing import Any

import httpx


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

    def set_access_token(self, token: str | None) -> None:
        with self._token_lock:
            self._access_token = token

    def clear_access_token(self) -> None:
        self.set_access_token(None)

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, *, json: dict[str, Any] | None = None) -> Any:
        return self.request("POST", path, json=json)

    def patch(self, path: str, *, json: dict[str, Any] | None = None) -> Any:
        return self.request("PATCH", path, json=json)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
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
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise ApiError("The server took too long to respond. Please try again.") from exc
        except httpx.RequestError as exc:
            raise ApiError(
                "Cannot connect to the clinic server. Check that the backend is running."
            ) from exc

        if response.status_code == 204:
            return None

        payload: Any = None
        if response.content:
            try:
                payload = response.json()
            except ValueError as exc:
                if response.is_success:
                    raise ApiError(
                        "The server returned an invalid response.",
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
                400: "The request could not be completed.",
                401: "Your session is invalid or has expired.",
                403: "You do not have permission to perform this action.",
                404: "The requested information was not found.",
                409: "This information already exists.",
                422: "Please check the information you entered.",
                500: "The server encountered an unexpected error.",
            }.get(status_code, f"Request failed (HTTP {status_code}).")
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
                field = str(location[-1]).replace("_", " ") if location else "Field"
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
