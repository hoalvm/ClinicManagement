"""Unit tests for the request-scoped SQLAlchemy session dependency."""

from unittest.mock import MagicMock

import pytest

from backend.app.db import session as session_module


def test_get_db_closes_session_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = MagicMock()
    monkeypatch.setattr(session_module, "SessionLocal", lambda: fake_session)

    dependency = session_module.get_db()

    assert next(dependency) is fake_session
    with pytest.raises(StopIteration):
        next(dependency)

    fake_session.rollback.assert_not_called()
    fake_session.close.assert_called_once_with()


def test_get_db_rolls_back_and_closes_after_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = MagicMock()
    monkeypatch.setattr(session_module, "SessionLocal", lambda: fake_session)
    dependency = session_module.get_db()
    next(dependency)

    with pytest.raises(RuntimeError, match="query failed"):
        dependency.throw(RuntimeError("query failed"))

    fake_session.rollback.assert_called_once_with()
    fake_session.close.assert_called_once_with()
