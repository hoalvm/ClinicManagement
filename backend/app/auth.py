"""JWT and password helpers – uses PyJWT (jwt) and pwdlib, same as core/security.py."""

from datetime import datetime, timedelta, UTC

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from backend.app.core.config import get_settings

_settings = get_settings()

SECRET_KEY = _settings.jwt_secret_value
ALGORITHM = _settings.jwt_algorithm
EXPIRE_MINUTES = _settings.access_token_expire_minutes

_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(plain, hashed)
    except (TypeError, UnknownHashError, ValueError):
        return False


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])