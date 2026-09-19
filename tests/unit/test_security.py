"""Security helper tests independent of SQL Server."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from pydantic import SecretStr

from backend.app.core import security
from backend.app.core.exceptions import AuthenticationError


@pytest.fixture
def jwt_settings(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    settings = SimpleNamespace(
        jwt_secret=SecretStr("unit-test-secret-that-is-not-used-outside-tests"),
        jwt_secret_value="unit-test-secret-that-is-not-used-outside-tests",
        jwt_algorithm="HS256",
        access_token_expire_minutes=60,
    )
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    return settings


def test_password_is_argon2_hashed_and_verifiable() -> None:
    password = "Password123!"

    password_hash = security.hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2")
    assert security.verify_password(password, password_hash) is True
    assert security.verify_password("WrongPassword!", password_hash) is False


def test_malformed_password_hash_fails_closed() -> None:
    assert security.verify_password("Password123!", "not-a-password-hash") is False


def test_access_token_contains_only_expected_identity_claims(jwt_settings: SimpleNamespace) -> None:
    token = security.create_access_token(user_id=42, role="PATIENT")

    raw_payload = jwt.decode(
        token,
        jwt_settings.jwt_secret.get_secret_value(),
        algorithms=[jwt_settings.jwt_algorithm],
    )
    decoded = security.decode_access_token(token)

    assert decoded.user_id == 42
    assert decoded.role == "PATIENT"
    assert set(raw_payload) == {"sub", "role", "iat", "exp"}
    assert raw_payload["sub"] == "42"


def test_expired_access_token_is_rejected(jwt_settings: SimpleNamespace) -> None:
    token = jwt.encode(
        {
            "sub": "42",
            "role": "PATIENT",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        },
        jwt_settings.jwt_secret.get_secret_value(),
        algorithm=jwt_settings.jwt_algorithm,
    )

    with pytest.raises(AuthenticationError):
        security.decode_access_token(token)


@pytest.mark.parametrize(
    "payload",
    [
        {"role": "PATIENT"},
        {"sub": "not-an-integer", "role": "PATIENT"},
        {"sub": "0", "role": "PATIENT"},
        {"sub": "42", "role": ""},
    ],
)
def test_invalid_required_claims_are_rejected(
    payload: dict[str, str], jwt_settings: SimpleNamespace
) -> None:
    payload_with_expiry = {
        **payload,
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }
    token = jwt.encode(
        payload_with_expiry,
        jwt_settings.jwt_secret.get_secret_value(),
        algorithm=jwt_settings.jwt_algorithm,
    )

    with pytest.raises(AuthenticationError):
        security.decode_access_token(token)
