"""Compatibility wrappers around the single password and JWT implementation."""

from backend.app.core.security import (
    create_access_token as _create_access_token,
)
from backend.app.core.security import (
    decode_access_token as _decode_access_token,
)
from backend.app.core.security import (
    hash_password,
    verify_password,
)

__all__ = ["create_access_token", "decode_access_token", "hash_password", "verify_password"]


def create_access_token(data: dict[str, object]) -> str:
    """Issue a token for an immutable user id, never a mutable username."""

    return _create_access_token(user_id=int(data["sub"]), role=str(data["role"]))


def decode_access_token(token: str) -> dict[str, str]:
    payload = _decode_access_token(token)
    return {"sub": str(payload.user_id), "role": payload.role}
