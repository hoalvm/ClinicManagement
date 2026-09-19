"""Unit tests for the frontend's single HTTP boundary."""

from collections.abc import Callable

import httpx
import pytest

from frontend.api.api_client import ApiClient, ApiError


def make_client(handler: Callable[[httpx.Request], httpx.Response]) -> ApiClient:
    client = ApiClient("https://clinic.example.test")
    client._client.close()
    client._client = httpx.Client(
        base_url="https://clinic.example.test",
        transport=httpx.MockTransport(handler),
    )
    return client


def test_bearer_token_is_added_to_requests() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer signed-token"
        assert request.url.path == "/api/v1/patients/me"
        return httpx.Response(200, json={"patient_id": 1})

    client = make_client(handler)
    client.set_access_token("signed-token")

    try:
        assert client.get("/api/v1/patients/me") == {"patient_id": 1}
    finally:
        client.close()


def test_clear_token_removes_authorization_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Authorization" not in request.headers
        return httpx.Response(200, json={"status": "ok"})

    client = make_client(handler)
    client.set_access_token("old-token")
    client.clear_access_token()

    try:
        assert client.get("/health") == {"status": "ok"}
    finally:
        client.close()


@pytest.mark.parametrize(
    ("status_code", "expected_message"),
    [
        (401, "expired"),
        (403, "permission"),
        (404, "not found"),
        (409, "already exists"),
        (500, "unexpected error"),
    ],
)
def test_http_errors_are_normalized(status_code: int, expected_message: str) -> None:
    client = make_client(lambda _request: httpx.Response(status_code, json={}))

    try:
        with pytest.raises(ApiError) as caught:
            client.get("/api/v1/private")
    finally:
        client.close()

    assert caught.value.status_code == status_code
    assert expected_message in caught.value.message.lower()


def test_validation_details_are_rendered_for_users() -> None:
    payload = {
        "detail": [
            {"loc": ["body", "full_name"], "msg": "Field required", "type": "missing"},
            {
                "loc": ["body", "email"],
                "msg": "value is not a valid email address",
                "type": "value_error",
            },
        ]
    }
    client = make_client(lambda _request: httpx.Response(422, json=payload))

    try:
        with pytest.raises(ApiError) as caught:
            client.post("/api/v1/auth/register", json={})
    finally:
        client.close()

    assert caught.value.status_code == 422
    assert "Full Name: Field required" in caught.value.message
    assert "Email: value is not a valid email address" in caught.value.message
    assert caught.value.details == payload["detail"]


def test_timeout_is_reported_without_leaking_transport_details() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("internal timeout detail", request=request)

    client = make_client(handler)

    try:
        with pytest.raises(ApiError, match="too long") as caught:
            client.get("/health")
    finally:
        client.close()

    assert "internal timeout detail" not in caught.value.message


def test_connection_failure_is_normalized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("internal socket detail", request=request)

    client = make_client(handler)

    try:
        with pytest.raises(ApiError, match="Cannot connect") as caught:
            client.get("/health")
    finally:
        client.close()

    assert "internal socket detail" not in caught.value.message


def test_successful_invalid_json_is_rejected() -> None:
    client = make_client(
        lambda _request: httpx.Response(
            200,
            content=b"not-json",
            headers={"content-type": "application/json"},
        )
    )

    try:
        with pytest.raises(ApiError, match="invalid response") as caught:
            client.get("/health")
    finally:
        client.close()

    assert caught.value.status_code == 200


def test_no_content_response_returns_none() -> None:
    client = make_client(lambda _request: httpx.Response(204))

    try:
        assert client.post("/logout") is None
    finally:
        client.close()
