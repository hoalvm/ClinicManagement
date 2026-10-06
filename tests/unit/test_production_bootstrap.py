"""A production administrator can be bootstrapped only into an empty DB."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.app.db import bootstrap_admin

_VALID = {
    "username": "admin.nguyen",
    "full_name": "Nguyễn Văn Quản Trị",
    "email": "quantri@example.org",
    "password": "A private long password 2026!",
    "identity_verified": True,
}


def test_bootstrap_rejects_existing_users(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bootstrap_admin, "get_settings", lambda: SimpleNamespace(app_mode="production")
    )
    session = MagicMock()
    session.get_bind.return_value.dialect.name = "mssql"
    session.scalar.return_value = 1
    with pytest.raises(ValueError, match="empty database"):
        bootstrap_admin.bootstrap_first_admin(session, **_VALID)
    session.add.assert_not_called()
    session.rollback.assert_called_once()


def test_bootstrap_requires_in_person_identity_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bootstrap_admin, "get_settings", lambda: SimpleNamespace(app_mode="production")
    )
    session = MagicMock()
    with pytest.raises(ValueError, match="verify the administrator's identity"):
        bootstrap_admin.bootstrap_first_admin(
            session, **{**_VALID, "identity_verified": False}
        )
    session.scalar.assert_not_called()


def test_bootstrap_inserts_admin_and_audit_in_one_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bootstrap_admin, "get_settings", lambda: SimpleNamespace(app_mode="production")
    )
    monkeypatch.setattr(bootstrap_admin, "hash_password", lambda _value: "hashed")
    audit = MagicMock()
    monkeypatch.setattr(bootstrap_admin, "record_audit_event", audit)
    session = MagicMock()
    session.get_bind.return_value.dialect.name = "mssql"
    session.scalar.return_value = 0
    session.flush.side_effect = lambda: setattr(session.add.call_args.args[0], "user_id", 7)

    assert bootstrap_admin.bootstrap_first_admin(session, **_VALID) == 7
    admin = session.add.call_args.args[0]
    assert admin.role == "ADMIN" and admin.password_hash == "hashed"
    audit.assert_called_once()
    session.commit.assert_called_once()
