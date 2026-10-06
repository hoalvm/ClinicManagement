"""One-time, identity-attested first administrator provisioning."""

from __future__ import annotations

import argparse
import getpass
import re
from collections.abc import Sequence

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.app.core.audit import record_audit_event
from backend.app.core.config import get_settings
from backend.app.core.security import hash_password
from backend.app.models import User


def bootstrap_first_admin(
    session: Session,
    *,
    username: str,
    full_name: str,
    email: str,
    password: str,
    identity_verified: bool,
) -> int:
    """Create a real named administrator only while the Users table is empty."""

    if get_settings().app_mode != "production":
        raise ValueError("First-admin bootstrap requires APP_MODE=production")
    username = username.strip().lower()
    full_name = full_name.strip()
    email = email.strip().lower()
    if not identity_verified:
        raise ValueError("The operator must verify the administrator's identity in person")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{3,49}", username):
        raise ValueError("Username must be a named account with 4-50 safe characters")
    if username.lower() in {"admin", "root", "sa"} or username.lower().startswith("demo"):
        raise ValueError("Generic or demo administrator usernames are forbidden")
    if len(full_name) < 3 or len(full_name) > 100:
        raise ValueError("Full name must be 3-100 characters")
    if len(email) > 100 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("A real administrator email is required")
    if len(password) < 16 or len(password) > 128 or password.strip() != password:
        raise ValueError("Password must be 16-128 characters without surrounding spaces")
    if password.lower() in {"password12345678", "1234567890123456"}:
        raise ValueError("A sample password is forbidden")

    try:
        bind = session.get_bind()
        if bind is not None and bind.dialect.name == "mssql":
            # This also locks an empty Users table until the transaction commits.
            existing = session.scalar(text("SELECT COUNT_BIG(*) FROM dbo.Users WITH (TABLOCKX, HOLDLOCK)"))
        else:
            existing = session.scalar(select(func.count(User.user_id)))
        if existing:
            raise ValueError("Bootstrap is allowed only on a newly provisioned empty database")

        admin = User(
            username=username,
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role="ADMIN",
            is_active=True,
        )
        session.add(admin)
        session.flush()
        record_audit_event(
            session,
            actor_user_id=None,
            actor_role="DBA",
            action="ADMIN_BOOTSTRAP",
            entity_type="User",
            entity_id=admin.user_id,
        )
        session.commit()
        return admin.user_id
    except Exception:
        session.rollback()
        raise


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Provision one named administrator in a new production DB")
    parser.add_argument("--username", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--identity-verified", action="store_true")
    args = parser.parse_args(argv)
    password = getpass.getpass("New administrator password: ")
    confirm = getpass.getpass("Repeat password: ")
    if password != confirm:
        parser.error("Passwords do not match")

    from backend.app.db.session import SessionLocal

    with SessionLocal() as session:
        user_id = bootstrap_first_admin(
            session,
            username=args.username,
            full_name=args.full_name,
            email=args.email,
            password=password,
            identity_verified=args.identity_verified,
        )
    print(f"Created administrator UserID={user_id}. Configure MFA before go-live.")


if __name__ == "__main__":
    main()
