"""Shared FastAPI test fixtures that never open a database connection."""

from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.api.deps import get_current_patient, get_current_user
from backend.app.db.session import get_db
from backend.app.main import app


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Generator[None, None, None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def fake_session() -> MagicMock:
    return MagicMock(name="mock_sql_server_session")


@pytest.fixture
def current_identity() -> tuple[SimpleNamespace, SimpleNamespace]:
    user = SimpleNamespace(
        user_id=1,
        username="patient01",
        full_name="Nguyen Van A",
        phone="0900000000",
        email="patient01@example.com",
        role="PATIENT",
        is_active=True,
        patient=None,
    )
    patient = SimpleNamespace(
        patient_id=10,
        user_id=1,
        user=user,
        date_of_birth=None,
        gender="MALE",
        address="Ho Chi Minh City",
    )
    user.patient = patient
    return user, patient


@pytest.fixture
def client(fake_session: MagicMock) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[MagicMock, None, None]:
        yield fake_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(
    client: TestClient,
    current_identity: tuple[SimpleNamespace, SimpleNamespace],
) -> TestClient:
    user, patient = current_identity
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_patient] = lambda: patient
    return client
