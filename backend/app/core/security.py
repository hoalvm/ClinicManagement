"""Password hashing and JWT helpers."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.audit import record_audit_event
from backend.app.core.config import get_settings
from backend.app.core.exceptions import AuthenticationError

password_hasher = PasswordHash.recommended()


@dataclass(frozen=True, slots=True)
class TokenPayload:
    user_id: int
    role: str
    jti_hash: str | None = None


def hash_password(password: str) -> str:
    """Hash a password using pwdlib's recommended Argon2 configuration."""

    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Safely verify a password without allowing malformed hashes to escape."""

    try:
        return password_hasher.verify(password, password_hash)
    except (TypeError, UnknownHashError, ValueError):
        return False


def create_access_token(
    *,
    user_id: int,
    role: str,
    expires_delta: timedelta | None = None,
    session: Session | None = None,
) -> str:
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
    if settings.app_mode == "production":
        if session is None:
            raise RuntimeError("Production tokens require a persistent auth session")
        jti = token_urlsafe(32)
        jti_hash = sha256(jti.encode("ascii")).hexdigest()
        payload["jti"] = jti
        try:
            session.execute(
                text(
                    "INSERT INTO dbo.AuthSessions "
                    "(JtiHash, UserID, IssuedAt, ExpiresAt) "
                    "VALUES (:jti_hash, :user_id, :issued_at, :expires_at)"
                ),
                {
                    "jti_hash": jti_hash,
                    "user_id": user_id,
                    "issued_at": now.replace(tzinfo=None),
                    "expires_at": expires_at.replace(tzinfo=None),
                },
            )
            record_audit_event(
                session,
                actor_user_id=user_id,
                actor_role=role,
                action="LOGIN_SUCCESS",
                entity_type="User",
                entity_id=user_id,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
    return jwt.encode(
        payload,
        settings.jwt_secret_value,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> TokenPayload:
    """Validate a bearer token and normalize its required claims."""

    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_value,
            algorithms=[settings.jwt_algorithm],
            options={
                "require": ["sub", "role", "exp", "jti"]
                if settings.app_mode == "production"
                else ["sub", "role", "exp"]
            },
        )
        user_id = int(payload["sub"])
        role = str(payload["role"])
        if user_id <= 0 or not role:
            raise ValueError
        jti = payload.get("jti")
        if settings.app_mode == "production" and (
            not isinstance(jti, str)
            or not jti.isascii()
            or len(jti) < 32
            or len(jti) > 128
        ):
            raise ValueError
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError() from exc
    return TokenPayload(
        user_id=user_id,
        role=role,
        jti_hash=sha256(jti.encode("ascii")).hexdigest() if isinstance(jti, str) else None,
    )


def validate_access_session(session: Session, payload: TokenPayload) -> None:
    """Verify a production bearer token still has a live server-side session."""

    if get_settings().app_mode != "production":
        return
    if payload.jti_hash is None:
        raise AuthenticationError()
    row = session.execute(
        text(
            "SELECT UserID, ExpiresAt, RevokedAt FROM dbo.AuthSessions "
            "WHERE JtiHash = :jti_hash"
        ),
        {"jti_hash": payload.jti_hash},
    ).first()
    if (
        row is None
        or row[0] != payload.user_id
        or row[2] is not None
        or row[1] <= datetime.now(UTC).replace(tzinfo=None)
    ):
        raise AuthenticationError()


def revoke_access_session(session: Session, payload: TokenPayload) -> None:
    """Invalidate the current production session; caller must commit."""

    if get_settings().app_mode != "production":
        return
    if payload.jti_hash is None:
        raise AuthenticationError()
    session.execute(
        text(
            "UPDATE dbo.AuthSessions SET RevokedAt = SYSUTCDATETIME() "
            "WHERE JtiHash = :jti_hash AND UserID = :user_id AND RevokedAt IS NULL"
        ),
        {"jti_hash": payload.jti_hash, "user_id": payload.user_id},
    )


def revoke_user_sessions(session: Session, user_id: int) -> None:
    """Revoke all production tokens after role/credential/account changes."""

    if get_settings().app_mode != "production":
        return
    session.execute(
        text(
            "UPDATE dbo.AuthSessions SET RevokedAt = SYSUTCDATETIME() "
            "WHERE UserID = :user_id AND RevokedAt IS NULL"
        ),
        {"user_id": user_id},
    )


def logout_access_token(session: Session, token: str, *, actor_role: str) -> None:
    """Revoke the presented production token and commit the logout audit."""

    payload = decode_access_token(token)
    if get_settings().app_mode != "production":
        return
    try:
        revoke_access_session(session, payload)
        record_audit_event(
            session,
            actor_user_id=payload.user_id,
            actor_role=actor_role,
            action="LOGOUT",
            entity_type="User",
            entity_id=payload.user_id,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
