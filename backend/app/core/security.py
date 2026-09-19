"""Password hashing and JWT helpers."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from backend.app.core.config import get_settings
from backend.app.core.exceptions import AuthenticationError

password_hasher = PasswordHash.recommended()


@dataclass(frozen=True, slots=True)
class TokenPayload:
    user_id: int
    role: str


def hash_password(password: str) -> str:
    """Hash a password using pwdlib's recommended Argon2 configuration."""

    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Safely verify a password without allowing malformed hashes to escape."""

    try:
        return password_hasher.verify(password, password_hash)
    except (TypeError, UnknownHashError, ValueError):
        return False


def create_access_token(*, user_id: int, role: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed bearer token containing only identity and role claims."""

    settings = get_settings()
    now = datetime.now(UTC)
    expires_at = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenPayload:
    """Validate a bearer token and normalize its required claims."""

    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "role", "exp"]},
        )
        user_id = int(payload["sub"])
        role = str(payload["role"])
        if user_id <= 0 or not role:
            raise ValueError
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError() from exc
    return TokenPayload(user_id=user_id, role=role)
